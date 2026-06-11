# Quality Baseline — Technical Design Deep-Dive

> 日期: 2026-06-10
> OpenSpec change: `quality-baseline`
> 设计基于: `openspec/changes/quality-baseline/proposal.md`, `design.md`, `specs/`, `docs/current-capabilities.md`

---

## 1. 测试架构

```
tests/
  conftest.py                  # engine / session / TestClient fixtures, seed helpers, mock 工厂
  test_query_creation.py       # 直接调用 notify_and_create_query()
  test_mentor_assignment.py    # TestClient → accept_query / resolve_query
```

### 1.1 调用方式选择

| 测试目标 | 调用方式 | 理由 |
|---|---|---|
| `notify_and_create_query` | 直接调函数 | 纯 Python 函数，不依赖 FastAPI 基础设施；创建独立 Session 传入即可 |
| `accept_query` | `httpx.TestClient` | 路由函数有 HTTP 状态码语义 (200/400/404) 需要验证；走 `Depends(get_db)` 路径 |
| `resolve_query` | `httpx.TestClient` | 同上 |

### 1.2 Mock 策略

- `dependency_overrides[get_db]` → 测试 `:memory:` session（TestClient 路径必须）
- `pytest monkeypatch` → `send_slack_alert` / `send_email_alert`（两个通知函数不走 FastAPI DI，只能 monkeypatch）
- 不使用 side_effect 做 DB 查询验证时序 — 时序含义由 "commit 结果 + mock 已被调用" 组合验证
- `Mock.assert_called_once()` 验证通知被触发，不验证内部参数细节

### 1.3 数据库隔离

每个测试函数独立创建 `:memory:` engine + 建表 + session。测试间零泄漏。

---

## 2. conftest.py Fixtures

### 2.1 Engine（autouse）

```
scope: function
→ create_engine("sqlite:///:memory:")
→ Base.metadata.create_all(engine)
→ yield engine
→ Base.metadata.drop_all(engine)
→ engine.dispose()
```

### 2.2 Session

```
scope: function
→ Session(bind=engine)
→ yield session
→ session.rollback()
→ session.close()
```

### 2.3 TestClient

```
scope: function
→ from overclocked_helpdesk.main import app
→ app.dependency_overrides[get_db] = lambda: db
→ yield TestClient(app)
→ app.dependency_overrides.clear()
```

### 2.4 Notification mocks

```python
@pytest.fixture
def mock_slack(monkeypatch):
    mock = Mock(return_value=True)
    monkeypatch.setattr("overclocked_helpdesk.services.notifier.send_slack_alert", mock)
    return mock

@pytest.fixture
def mock_email(monkeypatch):
    mock = Mock(return_value=True)
    monkeypatch.setattr("overclocked_helpdesk.api.queries.send_email_alert", mock)
    return mock
```

### 2.5 Seed helpers（普通函数，非 fixture）

- `create_mentor(db, **kwargs)` → Mentor — 默认: name="M1", email="m1@test.com", max_load=3, current_load=0, is_active=True
- `create_team(db, **kwargs)` → Team — 默认: name="T1", location="Room 1", mentor_id=seed_mentor.id
- `create_query(db, **kwargs)` → Query — 默认: team_id=seed_team.id, issue="Test issue", location="Test loc", status="PENDING", mentor_id=None

每个函数内 `db.add()` → `db.commit()` → `db.refresh()`。

---

## 3. 测试用例矩阵

### 3.1 test_query_creation.py

| ID | Spec 来源 | Scenario | Mock slack | 断言 |
|---|---|---|---|---|
| QC1 | TP1-TP2 / Successful query creation | `notify_and_create_query(db, team_id=5, issue="...", location="...")` | → True | status=PENDING, mentor_id=None, 字段精确匹配, created_at 非空, Slack 被调用 1 次 |
| QC2 | TP2 / Slack unavailable | 同 QC1 | → False | Query 仍持久化, status=PENDING, Slack 被调用过 |
| QC3 | TP1 / Fields match exactly | `notify_and_create_query(db, team_id=5, issue="Network down", location="Room 301")` | → True | team_id=5, issue="Network down", location="Room 301" |

### 3.2 test_mentor_assignment.py — accept_query

| ID | Spec 来源 | Scenario | 前置状态 | HTTP | 断言 |
|---|---|---|---|---|---|
| MA1 | MP1 / Successful acceptance | 正常接受 | query PENDING, mentor active, load < max | PATCH 200 | status=ASSIGNED, mentor_id 正确, load +1 |
| MA2 | MP2 / Full-load deactivation | 满载去激活 | query PENDING, mentor load = max_load - 1 | PATCH 200 | is_active=False |
| MA3 | MP2 / Stay active below max | 未满载保持活跃 | query PENDING, mentor load < max_load - 1 | PATCH 200 | is_active=True |
| MA4 | MP3 / Reject assigned | 拒绝已分配 | query 已有 mentor_id 或 status != PENDING | PATCH 400 | "Query already taken", 状态未变 |
| MA5 | MP4 / Reject inactive | 拒绝非活跃 | mentor.is_active=False | PATCH 400 | "Mentor not available", query 未变 |
| MA6 | MP5 / Query 404 | Query 不存在 | query_id=9999 | PATCH 404 | "Query not found" |
| MA7 | MP5 / Mentor 404 | Mentor 不存在 | mentor_id=9999 | PATCH 404 | "Mentor not found" |
| MA8 | MP10 / Email called | 邮件已调用 | 正常 accept, email mock → True | PATCH 200 | `send_email_alert` 被调用 1 次 |
| MA9 | MP10 / Email failure no rollback | 邮件失败不回滚 | 正常 accept, email mock → False | PATCH 200 | query 已 ASSIGNED, load +1 |

### 3.3 test_mentor_assignment.py — resolve_query

| ID | Spec 来源 | Scenario | 前置状态 | HTTP | 断言 |
|---|---|---|---|---|---|
| MR1 | MP6 / Successful resolve | 正常 resolve | query ASSIGNED 有 mentor, load > 0 | PATCH 200 | status=RESOLVED, load -1 |
| MR2 | MP7 / Load recovery | 负载恢复 | mentor 满载 is_active=False, resolve 后 load < max | PATCH 200 | is_active=True |
| MR3 | MP9 / No-mentor resolve | 无 mentor resolve | query PENDING, mentor_id=None | PATCH 200 | status=RESOLVED, 无 mentor 操作 |
| MR4 | MP8 / Idempotent resolve | 重复 resolve 幂等 | query 已 RESOLVED | PATCH 200 | {ok:true}, load 不变 |
| MR5 | MP6 / Load never negative | Load 不下穿 0 | query 有 mentor, load=1 | PATCH 200 | load=0 |
| MR6 | (delta added) / Query 404 | Query 不存在 | query_id=9999 | PATCH 404 | "Query not found" |

---

## 4. 边界条件覆盖

| 边界 | 用例 | 验证点 |
|---|---|---|
| `current_load >= max_load` 去激活 | MA2 | is_active=False |
| `current_load < max_load` 保持活跃 | MA3 | is_active=True |
| `current_load` 从满载下降后恢复 | MR2 | is_active=True |
| `current_load = 1` 时 resolve | MR5 | load=0（不下穿 0） |
| `mentor_id=None` 时 resolve | MR3 | 跳过 mentor 操作 |
| 已 RESOLVED 重复 resolve | MR4 | 幂等，状态不变 |
| status != PENDING 接受 | MA4 | 400 拒绝 |
| is_active=False 接受 | MA5 | 400 拒绝 |

---

## 5. 不测试的项

| 项 | 原因 |
|---|---|
| 并发两个 mentor 同时 accept 同一 query | SQLite 测试环境无法真实模拟竞态；`docs/current-capabilities.md` MV4 已记录 |
| toggle-availability 与 accept 交互 | MV5，非 assignment 核心路径，属于 mentor 管理 |
| 邮件 HTML 模板内容验证 | 属于 `email_service.py` 单元测试范围，不在本 change |
| `background_notify()` 的 BackgroundTasks 调度 | FastAPI 内置行为 |
| `POST /submit` 端到端（表单 → BackgroundTasks → notify） | TP1 已通过 `notify_and_create_query` 直接调用覆盖 |
| `api/mentors.py` 路径 | 死代码，未注册 router |
| `services/assigner.py` 算法 | 未接入，如果未来启用需单独 change |
| admin CRUD（add/edit/delete mentor, generate QR） | 非本 change 的 core write path |

---

## 6. 缺失验收场景回写

以下场景在原 OpenSpec spec 中未覆盖，已回写 delta spec：

| 场景 | 代码依据 | 操作 |
|---|---|---|
| `resolve_query` 对不存在的 query_id 返回 404 | `api/queries.py:257-258` | ADDED Requirement → `specs/mentor-assignment-tests/spec.md` |

---

## 7. 运行命令

```bash
# Query creation
pytest tests/test_query_creation.py -v

# Mentor assignment (accept + resolve)
pytest tests/test_mentor_assignment.py -v

# Full
pytest tests/ -v
```

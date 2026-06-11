## Context

OverClocked Helpdesk 是一个 FastAPI + SQLAlchemy + SQLite 的工单系统，当前无任何自动化测试。核心写路径集中在两个位置：

- **Query Creation**: `services/notifier.py:6-33`（`notify_and_create_query`），由 `main.py:40-50`（`background_notify`）在后台任务中调用
- **Mentor Assignment**: `api/queries.py:80-244`（`accept_query`）和 `api/queries.py:250-276`（`resolve_query`），直接处理 mentor 的负载状态机

当前行为边界记录在 `docs/current-capabilities.md`，本 change 的覆盖目标定义在该文档第 1.2 节（TP1-TP2）和第 2.2 节（MP1-MP10）。

本 change 是纯测试添加，不涉及业务代码修改。项目目前没有测试框架配置。

## Goals / Non-Goals

**Goals:**
- 建立可运行的 pytest 测试套件，覆盖 `accept_query`、`resolve_query`、`notify_and_create_query` 的当前行为
- 测试数据使用 SQLite 内存数据库，不依赖外部服务（Slack/SMTP 全部 mock）
- 每个测试场景精确对应 `docs/current-capabilities.md` 中标记为 "Planned `quality-baseline` 应保护的行为" 的条目
- 提供两个聚焦测试命令：一个验证 mentor assignment，一个验证 query creation

**Non-Goals:**
- 不修改 `overclocked_helpdesk/`、`templates/`、`scripts/` 下的任何业务代码
- 不引入登录、认证、权限校验
- 不引入 WebSocket、Docker、Analytics
- 不重写或重构现有服务层/路由层
- 不测试 `api/mentors.py`（死代码）或 `services/assigner.py`（未接入）
- 若 `qrcode` 或 `requirements.txt` 缺失依赖阻碍测试运行，仅记录为已知问题，不在本 change 修复

## Decisions

### D1: 测试框架 — pytest

选择 `pytest` 作为测试运行器（FastAPI/SQLAlchemy 生态标准搭配）。`requirements.txt` 已包含 FastAPI 和 SQLAlchemy，需额外添加 `pytest` 和 `httpx`（用于 FastAPI TestClient）。如果 `requirements.txt` 未锁定测试依赖，则在本 change 中添加。

备选方案: `unittest` — 内置但缺乏 pytest fixture 系统和参数化能力，不适合需要大量边界条件覆盖的测试。

### D2: 数据库策略 — SQLite 内存 + 独立 session factory

使用独立的 SQLite `:memory:` 数据库为每个测试函数创建全新 engine 和 session。这避免了测试间数据泄漏，且不需要安装额外数据库。

备选方案: 使用项目的 `helpdesk.db` 文件 — 会污染开发数据，且无法并行测试。

### D3: 外部依赖 mock — monkeypatch + unittest.mock

Slack webhook（`services/slack_service.send_slack_alert`）和 SMTP 邮件（`services/email_service.send_email_alert`）在测试中全部 mock。Slack mock 返回 `True`（模拟成功），SMTP mock 返回 `True`（模拟成功），另提供返回 `False` 的 mock 用于测试通知失败场景。

备选方案: 使用依赖注入替换服务 — 需要修改业务代码，违反 non-goal。

### D4: 测试文件组织

```
tests/
  conftest.py              # 共享 fixtures: engine, session, test client, seed helpers
  test_mentor_assignment.py  # accept_query + resolve_query 全分支
  test_query_creation.py     # notify_and_create_query 最小成功路径
```

两个文件各自独立可运行：
- `pytest tests/test_mentor_assignment.py -v`
- `pytest tests/test_query_creation.py -v`

### D5: 不测试需网络的服务函数

`email_service.py` 和 `slack_service.py` 仅在 mock 层被调用，不单独编写单元测试。它们的当前行为如有缺陷，在 `docs/current-capabilities.md` 中记录，不在本 change 验证。

## Risks / Trade-offs

- **[R1] 测试与实现耦合**: accept_query 的测试直接调用路由函数或使用 TestClient，如果路由签名变更测试会失败。→ 这是期望行为 — 测试就是回归保护。
- **[R2] SQLite 与 PostgreSQL 行为差异**: 生产环境如果迁移到 PostgreSQL，某些行为可能不同（如 FK 约束、并发隔离）。→ `docs/current-capabilities.md` 已知风险已记录 FK 不强制的问题。如生产数据库变更，测试需要同步调整。
- **[R3] 邮件/通知 mock 可能掩盖配置问题**: mock 返回固定值，无法发现 SMTP 凭据缺失等配置问题。→ 在 `docs/current-capabilities.md` 已知缺陷中已记录，属于运维配置范畴，不在单元测试范围。
- **[R4] `pytest` 和 `httpx` 可能不在 `requirements.txt` 中**: 如果缺失，在本 change 中添加为测试依赖，不修改已有业务依赖。

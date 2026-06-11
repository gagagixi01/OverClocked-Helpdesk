# Quality Baseline — TDD Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 OverClocked Helpdesk 的 mentor assignment 和 query creation 两条核心写路径建立自动化测试基线，锁定当前行为，不做任何业务代码修改。

**Architecture:** pytest + SQLite `:memory:` + FastAPI TestClient（混合方案）。`notify_and_create_query()` 直接调函数测试；`accept_query`/`resolve_query` 走 TestClient HTTP。Slack/SMTP 外部依赖全部 monkeypatch mock。每个测试函数独立创建 engine + 建表，测试间零泄漏。

**Tech Stack:** Python 3.13, pytest, httpx, FastAPI, SQLAlchemy 2.0, SQLite `:memory:`

**Base Ref:** `bbe9654` (HEAD of main)

**Design Doc:** `docs/superpowers/specs/2026-06-10-quality-baseline-design.md`

**OpenSpec Change:** `openspec/changes/quality-baseline/`

---

## File Structure

```
tests/
  conftest.py                  # [NEW] engine/session/TestClient fixtures, mock 工厂, seed helpers
  test_query_creation.py       # [NEW] QC1-QC3: 直接调 notify_and_create_query()
  test_mentor_assignment.py    # [NEW] MA1-MA9 + MR1-MR6: TestClient → accept_query/resolve_query

requirements.txt               # [MODIFY] 添加 pytest（如缺失）
```

**Monkeypatch Targets (关键):**

| Mock 目标 | monkeypatch.setattr 路径 |
|---|---|
| `send_slack_alert` | `overclocked_helpdesk.services.notifier.send_slack_alert` |
| `send_email_alert` | `overclocked_helpdesk.api.queries.send_email_alert` |

> 注意：monkeypatch 必须替换 **import 位置**（notifier.py 中 import 了 `send_slack_alert`，queries.py 中 import 了 `send_email_alert`），不是定义位置。

---

## Task 1: 安装 pytest 并确认环境

- [ ] **Step 1.1: 安装 pytest**

```bash
cd overclocked-helpdesk-lab && source .venv/bin/activate
python -m pip install pytest
```

Expected: `Successfully installed pytest-<version>`

- [ ] **Step 1.2: 确认 pytest 可用**

```bash
python -m pytest --version
```

Expected: prints pytest version (e.g., `pytest 8.4.0`)

- [ ] **Step 1.3: 将 pytest 加入 requirements.txt（如果尚未在其中）**

```bash
grep -q "^pytest" requirements.txt || echo "pytest" >> requirements.txt
```

Expected: `pytest` 现在出现在 `requirements.txt` 中

- [ ] **Step 1.4: 创建 tests 目录**

```bash
mkdir -p tests
touch tests/__init__.py
```

Expected: `tests/` 目录存在，含空的 `__init__.py`

- [ ] **Step 1.5: 确认 conftest.py 和 test 文件不存在**

```bash
ls tests/conftest.py 2>/dev/null && echo "EXISTS" || echo "NOT FOUND"
ls tests/test_query_creation.py 2>/dev/null && echo "EXISTS" || echo "NOT FOUND"
ls tests/test_mentor_assignment.py 2>/dev/null && echo "EXISTS" || echo "NOT FOUND"
```

Expected: 全部输出 `NOT FOUND`

- [ ] **Step 1.6: Commit**

```bash
git add requirements.txt tests/__init__.py
git commit -m "chore: add pytest dependency and tests directory"
```

---

## Task 2: 创建 conftest.py — Engine + Session fixtures

**Files:**
- Create: `tests/conftest.py`
- Modify: none

**TDD 顺序**: 先写测试（期望因 fixture 不存在而 FAIL），再实现 fixture（期望 PASS）。

- [ ] **Step 2.1: 先写一个冒烟测试验证 import 链能工作（纯 import，不需要 fixture，应直接 PASS）**

Create `tests/test_query_creation.py`:

```python
def test_imports_work():
    from overclocked_helpdesk.services.notifier import notify_and_create_query
    from overclocked_helpdesk.models.query import Query
    assert notify_and_create_query is not None
    assert Query is not None
```

- [ ] **Step 2.2: 运行冒烟测试，确认环境正常**

```bash
cd overclocked-helpdesk-lab && source .venv/bin/activate
python -m pytest tests/test_query_creation.py::test_imports_work -v
```

Expected: PASS — 纯 import 测试不需要任何 fixture

- [ ] **Step 2.3: 写一个依赖 engine fixture 的测试（engine fixture 尚不存在，预期 FAIL）**

Append to `tests/test_query_creation.py`:

```python
def test_engine_creates_tables(engine):
    """验证 engine fixture 建表成功 — 可以查询 mentors/queries/teams 表。"""
    from sqlalchemy import text
    from sqlalchemy.orm import Session

    session = Session(bind=engine)
    session.execute(text("INSERT INTO mentors (name) VALUES ('test')"))
    session.commit()
    result = session.execute(text("SELECT COUNT(*) FROM mentors")).scalar()
    assert result == 1
    session.close()
```

- [ ] **Step 2.4: 运行测试，确认因 fixture 不存在而 FAIL**

```bash
cd overclocked-helpdesk-lab && source .venv/bin/activate
python -m pytest tests/test_query_creation.py::test_engine_creates_tables -v
```

Expected: FAIL — `fixture 'engine' not found`

- [ ] **Step 2.5: 实现 engine fixture（最小实现使测试通过）**

Write `tests/conftest.py`:

```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from overclocked_helpdesk.db.session import Base


@pytest.fixture(autouse=True)
def engine():
    """每个测试函数独立创建 :memory: engine，建表，测试后销毁。"""
    _engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=_engine)
    yield _engine
    Base.metadata.drop_all(bind=_engine)
    _engine.dispose()
```

- [ ] **Step 2.6: 运行测试验证 engine fixture 使测试通过**

```bash
cd overclocked-helpdesk-lab && source .venv/bin/activate
python -m pytest tests/test_query_creation.py::test_engine_creates_tables -v
```

Expected: PASS

- [ ] **Step 2.7: 写一个依赖 db fixture 的测试（db fixture 尚不存在，预期 FAIL）**

Append to `tests/test_query_creation.py`:

```python
from overclocked_helpdesk.models.mentor import Mentor

def test_db_fixture_persists_and_isolates(db):
    """验证 db fixture 可以持久化数据，且测试间隔离。"""
    mentor = Mentor(name="fixture_test", email="f@t.com", max_load=3)
    db.add(mentor)
    db.commit()
    db.refresh(mentor)

    assert mentor.id is not None
    assert mentor.name == "fixture_test"
```

- [ ] **Step 2.8: 运行测试，确认因 fixture 不存在而 FAIL**

```bash
cd overclocked-helpdesk-lab && source .venv/bin/activate
python -m pytest tests/test_query_creation.py::test_db_fixture_persists_and_isolates -v
```

Expected: FAIL — `fixture 'db' not found`

- [ ] **Step 2.9: 实现 db fixture**

Append to `tests/conftest.py`:

```python
@pytest.fixture
def db(engine):
    """每个测试函数独立 session。测试后 rollback + close。"""
    session = Session(bind=engine)
    yield session
    session.rollback()
    session.close()
```

- [ ] **Step 2.10: 运行测试确认 db fixture 使测试通过**

```bash
cd overclocked-helpdesk-lab && source .venv/bin/activate
python -m pytest tests/test_query_creation.py::test_db_fixture_persists_and_isolates tests/test_query_creation.py::test_engine_creates_tables -v
```

Expected: 2 PASS

- [ ] **Step 2.11: Commit**

```bash
git add tests/conftest.py tests/test_query_creation.py
git commit -m "feat: add engine and db fixtures to conftest"
```

---

## Task 3: 创建 conftest.py — Seed Helpers

**Files:**
- Modify: `tests/conftest.py`

**TDD 顺序**: 先写测试（期望因 seed helpers 不存在而 FAIL），再实现 helpers（期望 PASS）。

- [ ] **Step 3.1: 确认 seed helpers 尚不存在**

```bash
cd overclocked-helpdesk-lab && source .venv/bin/activate
python -c "from tests.conftest import create_mentor" 2>&1
```

Expected: ImportError (create_mentor not in conftest yet)

- [ ] **Step 3.2: 写测试验证 seed helpers（helpers 尚不存在，预期 FAIL）**

Append to `tests/test_query_creation.py`:

```python
from tests.conftest import create_mentor, create_team, create_query


def test_create_mentor_defaults(db):
    m = create_mentor(db)
    assert m.name == "Mentor_Default"
    assert m.is_active is True
    assert m.current_load == 0
    assert m.max_load == 3


def test_create_mentor_overrides(db):
    m = create_mentor(db, name="Alice", max_load=5, current_load=2, is_active=False)
    assert m.name == "Alice"
    assert m.max_load == 5
    assert m.current_load == 2
    assert m.is_active is False


def test_create_query_defaults(db):
    create_team(db, id=1)  # FK needs a team
    q = create_query(db)
    assert q.status == "PENDING"
    assert q.mentor_id is None
    assert q.issue == "Test issue"
    assert q.created_at is not None


def test_create_query_overrides(db):
    create_team(db, id=5)
    create_mentor(db, id=2)
    q = create_query(db, team_id=5, issue="Broken", location="Room 301", status="ASSIGNED", mentor_id=2)
    assert q.team_id == 5
    assert q.issue == "Broken"
    assert q.location == "Room 301"
    assert q.status == "ASSIGNED"
    assert q.mentor_id == 2
```

- [ ] **Step 3.3: 运行测试，确认因 seed helpers 不存在而 FAIL**

```bash
cd overclocked-helpdesk-lab && source .venv/bin/activate
python -m pytest tests/test_query_creation.py -k "test_create" -v
```

Expected: FAIL — `ImportError: cannot import name 'create_mentor'`

- [ ] **Step 3.4: 实现 seed helpers（最小实现使所有测试通过）**

Append to `tests/conftest.py`:

```python
from overclocked_helpdesk.models.mentor import Mentor
from overclocked_helpdesk.models.team import Team
from overclocked_helpdesk.models.query import Query


def create_mentor(db, **kwargs):
    defaults = {
        "name": "Mentor_Default",
        "email": "mentor@test.com",
        "max_load": 3,
        "current_load": 0,
        "is_active": True,
    }
    defaults.update(kwargs)
    obj = Mentor(**defaults)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def create_team(db, **kwargs):
    defaults = {"name": "Team_Default", "location": "Room 1", "mentor_id": 1}
    defaults.update(kwargs)
    obj = Team(**defaults)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def create_query(db, **kwargs):
    defaults = {
        "team_id": 1,
        "mentor_id": None,
        "issue": "Test issue",
        "location": "Test location",
        "status": "PENDING",
    }
    defaults.update(kwargs)
    obj = Query(**defaults)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj
```

- [ ] **Step 3.5: 运行测试确认 seed helpers 使测试通过**

```bash
cd overclocked-helpdesk-lab && source .venv/bin/activate
python -m pytest tests/test_query_creation.py -k "test_create" -v
```

Expected: 4 PASS

- [ ] **Step 3.6: Commit**

```bash
git add tests/conftest.py tests/test_query_creation.py
git commit -m "feat: add seed helpers to conftest"
```

---

## Task 4: Query Creation 测试 — QC1 & QC2（成功路径 + Slack 不可用）

**本任务记录已有行为，不修改生产代码。** `notify_and_create_query()` 是已存在的函数，测试应直接 PASS。

**Files:**
- Modify: `tests/test_query_creation.py`

**此文件仅直接调用 `notify_and_create_query()`，不走 TestClient。**

- [ ] **Step 4.1: 清理 test_query_creation.py，重新写入第一个正式测试 QC1**

**关键**: monkeypatch 必须在调用 `notify_and_create_query` **之前**完成，因为该函数 import 时就绑定了 `send_slack_alert`。patch 目标路径是 `overclocked_helpdesk.services.notifier.send_slack_alert`（使用位置）。

Replace `tests/test_query_creation.py` 全部内容:

```python
import pytest
from unittest.mock import Mock
from sqlalchemy.orm import Session

from overclocked_helpdesk.models.query import Query
from overclocked_helpdesk.services.notifier import notify_and_create_query
from tests.conftest import create_team


class TestQueryCreation:
    """notify_and_create_query() 的最小成功路径和 Slack 分离行为。"""

    @pytest.fixture(autouse=True)
    def setup(self, db, monkeypatch):
        self.db = db
        # Mock Slack — 默认返回 True（成功）
        self.mock_slack = Mock(return_value=True)
        monkeypatch.setattr(
            "overclocked_helpdesk.services.notifier.send_slack_alert",
            self.mock_slack,
        )

    def test_creates_query_with_pending_status_and_no_mentor(self):
        """QC1: 成功路径 — status=PENDING, mentor_id=None, Slack 被调用。"""
        create_team(self.db, id=5, name="Team5", location="Room 5")

        query = notify_and_create_query(
            db=self.db,
            team_id=5,
            issue="WiFi down",
            location="Room 5",
        )

        assert query.id is not None
        assert query.status == "PENDING"
        assert query.mentor_id is None
        assert query.team_id == 5
        assert query.issue == "WiFi down"
        assert query.location == "Room 5"
        assert query.created_at is not None
        self.mock_slack.assert_called_once()

    def test_query_created_even_when_slack_unavailable(self):
        """QC2: Slack 不可用时 Query 仍成功创建。"""
        self.mock_slack.return_value = False
        create_team(self.db, id=5, name="Team5", location="Room 5")

        query = notify_and_create_query(
            db=self.db,
            team_id=5,
            issue="WiFi down",
            location="Room 5",
        )

        assert query.id is not None
        assert query.status == "PENDING"
        self.mock_slack.assert_called_once()
        # Slack 失败不影响持久化
        db_query = self.db.query(Query).filter(Query.id == query.id).first()
        assert db_query is not None
        assert db_query.status == "PENDING"
```

- [ ] **Step 4.2: 运行 QC1 和 QC2**

```bash
cd overclocked-helpdesk-lab && source .venv/bin/activate
python -m pytest tests/test_query_creation.py -v
```

Expected: 2 PASS

- [ ] **Step 4.3: Commit**

```bash
git add tests/test_query_creation.py
git commit -m "test: add QC1 and QC2 — query creation success and Slack-unavailable paths"
```

---

## Task 5: Query Creation 测试 — QC3（字段精确传递）

**本任务记录已有行为，不修改生产代码。**

- [ ] **Step 5.1: 添加 QC3 到 test_query_creation.py**

Append inside `class TestQueryCreation`:

```python
    def test_query_fields_match_input_exactly(self):
        """QC3: 字段精确传递 — team_id, issue, location 与输入完全一致。"""
        create_team(self.db, id=42, name="Team42", location="Room 42")

        query = notify_and_create_query(
            db=self.db,
            team_id=42,
            issue="Network down",
            location="Room 301",
        )

        assert query.team_id == 42
        assert query.issue == "Network down"
        assert query.location == "Room 301"
```

- [ ] **Step 5.2: 运行 QC3**

```bash
cd overclocked-helpdesk-lab && source .venv/bin/activate
python -m pytest tests/test_query_creation.py::TestQueryCreation::test_query_fields_match_input_exactly -v
```

Expected: PASS

- [ ] **Step 5.3: Commit**

```bash
git add tests/test_query_creation.py
git commit -m "test: add QC3 — query creation field-pass-through"
```

---

## Task 6: TestClient fixture + conftest 收尾

**TDD 顺序**: 先写测试（期望因 client fixture 不存在而 FAIL），再实现 fixture（期望 PASS）。

- [ ] **Step 6.1: 确认 TestClient fixture 尚不存在**

```bash
cd overclocked-helpdesk-lab && source .venv/bin/activate
python -c "from tests.conftest import client" 2>&1
```

Expected: ImportError

- [ ] **Step 6.2: 写一个依赖 client fixture 的 sanity 测试（client fixture 尚不存在，预期 FAIL）**

Create `tests/test_mentor_assignment.py`:

```python
class TestClientSanity:
    def test_app_starts_and_serves_root(self, client):
        """验证 TestClient 能启动并返回 helpdesk 表单。"""
        response = client.get("/")
        assert response.status_code == 200
        assert "helpdesk" in response.text.lower()
```

- [ ] **Step 6.3: 运行测试，确认因 client fixture 不存在而 FAIL**

```bash
cd overclocked-helpdesk-lab && source .venv/bin/activate
python -m pytest tests/test_mentor_assignment.py -v
```

Expected: FAIL — `fixture 'client' not found`

- [ ] **Step 6.4: 实现 client fixture**

Append to `tests/conftest.py`:

```python
from fastapi.testclient import TestClient
from overclocked_helpdesk.main import app
from overclocked_helpdesk.db.session import get_db


@pytest.fixture
def client(db):
    """TestClient with get_db overridden to use test :memory: session."""
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as _client:
        yield _client
    app.dependency_overrides.clear()
```

- [ ] **Step 6.5: 运行测试确认 client fixture 使测试通过**

```bash
cd overclocked-helpdesk-lab && source .venv/bin/activate
python -m pytest tests/test_mentor_assignment.py -v
```

Expected: PASS

- [ ] **Step 6.6: Commit**

```bash
git add tests/conftest.py tests/test_mentor_assignment.py
git commit -m "feat: add TestClient fixture and sanity test"
```

---

## Task 7: accept_query 测试 — MA1-MA3（正常接受 + 满载边界）

**本任务记录已有行为，不修改生产代码。** `accept_query` 端点已存在，测试应直接 PASS。

- [ ] **Step 7.1: 创建 accept_query 测试类的基础结构和 MA1**

Replace `tests/test_mentor_assignment.py`:

```python
import pytest
from unittest.mock import Mock

from tests.conftest import create_mentor, create_team, create_query
from overclocked_helpdesk.models.query import Query
from overclocked_helpdesk.models.mentor import Mentor


class TestAcceptQuery:
    """accept_query 状态机全分支 — MA1 到 MA9。"""

    @pytest.fixture(autouse=True)
    def setup(self, db, client, monkeypatch):
        self.db = db
        self.client = client
        # Mock email — 默认返回 True（成功）
        self.mock_email = Mock(return_value=True)
        monkeypatch.setattr(
            "overclocked_helpdesk.api.queries.send_email_alert",
            self.mock_email,
        )

    def test_successful_acceptance(self):
        """MA1: 正常接受 — PENDING → ASSIGNED, load +1。"""
        mentor = create_mentor(self.db, name="M1", email="m1@t.com", max_load=3, current_load=0)
        create_team(self.db, id=5, name="T5", mentor_id=mentor.id)
        query = create_query(self.db, team_id=5, status="PENDING", mentor_id=None)

        resp = self.client.patch(f"/queries/{query.id}/accept/{mentor.id}")

        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["query_id"] == query.id
        assert data["mentor_id"] == mentor.id
        assert data["current_load"] == 1

        # Verify DB state
        self.db.refresh(query)
        assert query.status == "ASSIGNED"
        assert query.mentor_id == mentor.id
        self.db.refresh(mentor)
        assert mentor.current_load == 1
        assert mentor.is_active is True

    def test_mentor_deactivates_when_reaching_max_load(self):
        """MA2: 满载去激活 — load 达到 max_load 后 is_active=False。"""
        mentor = create_mentor(self.db, name="M1", max_load=2, current_load=1)
        create_team(self.db, id=5, name="T5", mentor_id=mentor.id)
        query = create_query(self.db, team_id=5, status="PENDING", mentor_id=None)

        resp = self.client.patch(f"/queries/{query.id}/accept/{mentor.id}")

        assert resp.status_code == 200
        self.db.refresh(mentor)
        assert mentor.current_load == 2
        assert mentor.is_active is False

    def test_mentor_stays_active_below_max_load(self):
        """MA3: 未满载保持活跃 — load < max_load 时 is_active 不变。"""
        mentor = create_mentor(self.db, name="M1", max_load=5, current_load=2)
        create_team(self.db, id=5, name="T5", mentor_id=mentor.id)
        query = create_query(self.db, team_id=5, status="PENDING", mentor_id=None)

        resp = self.client.patch(f"/queries/{query.id}/accept/{mentor.id}")

        assert resp.status_code == 200
        self.db.refresh(mentor)
        assert mentor.current_load == 3
        assert mentor.is_active is True
```

- [ ] **Step 7.2: 运行 MA1-MA3**

```bash
cd overclocked-helpdesk-lab && source .venv/bin/activate
python -m pytest tests/test_mentor_assignment.py -v
```

Expected: 3 PASS

- [ ] **Step 7.3: Commit**

```bash
git add tests/test_mentor_assignment.py
git commit -m "test: add MA1-MA3 — accept_query success, full-load deactivation, stay-active"
```

---

## Task 8: accept_query 测试 — MA4-MA7（拒绝守卫 + 404）

**本任务记录已有行为，不修改生产代码。**

- [ ] **Step 8.1: 添加 MA4-MA7 到 TestAcceptQuery**

Append inside `class TestAcceptQuery`:

```python
    def test_reject_already_assigned_query(self):
        """MA4: 拒绝已分配工单 — status != PENDING → 400。"""
        mentor = create_mentor(self.db, name="M1")
        other = create_mentor(self.db, name="M2", email="m2@t.com")
        create_team(self.db, id=5, name="T5", mentor_id=mentor.id)
        query = create_query(self.db, team_id=5, status="ASSIGNED", mentor_id=other.id)

        resp = self.client.patch(f"/queries/{query.id}/accept/{mentor.id}")

        assert resp.status_code == 400
        assert "already taken" in resp.json()["detail"].lower()
        # 状态未变
        self.db.refresh(query)
        assert query.status == "ASSIGNED"
        assert query.mentor_id == other.id
        # Load 未变
        self.db.refresh(mentor)
        assert mentor.current_load == 0

    def test_reject_inactive_mentor(self):
        """MA5: 拒绝非活跃导师 — !mentor.is_active → 400。"""
        mentor = create_mentor(self.db, name="M1", is_active=False)
        create_team(self.db, id=5, name="T5", mentor_id=mentor.id)
        query = create_query(self.db, team_id=5, status="PENDING", mentor_id=None)

        resp = self.client.patch(f"/queries/{query.id}/accept/{mentor.id}")

        assert resp.status_code == 400
        assert "not available" in resp.json()["detail"].lower()
        self.db.refresh(query)
        assert query.status == "PENDING"
        assert query.mentor_id is None

    def test_query_not_found_during_accept(self):
        """MA6: Query 不存在 → 404。"""
        mentor = create_mentor(self.db, name="M1")

        resp = self.client.patch(f"/queries/9999/accept/{mentor.id}")

        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_mentor_not_found_during_accept(self):
        """MA7: Mentor 不存在 → 404。"""
        create_team(self.db, id=5, name="T5", mentor_id=1)
        query = create_query(self.db, team_id=5, status="PENDING", mentor_id=None)

        resp = self.client.patch(f"/queries/{query.id}/accept/9999")

        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()
```

- [ ] **Step 8.2: 运行 MA4-MA7**

```bash
cd overclocked-helpdesk-lab && source .venv/bin/activate
python -m pytest tests/test_mentor_assignment.py -v
```

Expected: 7 PASS (3 from before + 4 new)

- [ ] **Step 8.3: Commit**

```bash
git add tests/test_mentor_assignment.py
git commit -m "test: add MA4-MA7 — accept reject-already-assigned, reject-inactive, 404s"
```

---

## Task 9: accept_query 测试 — MA8-MA9（邮件行为）

**本任务记录已有行为，不修改生产代码。**

- [ ] **Step 9.1: 添加 MA8-MA9 到 TestAcceptQuery**

Append inside `class TestAcceptQuery`:

```python
    def test_email_sent_on_accept(self):
        """MA8: 接受后邮件被调用。"""
        mentor = create_mentor(self.db, name="M1", email="m1@test.com")
        create_team(self.db, id=5, name="T5", mentor_id=mentor.id)
        query = create_query(self.db, team_id=5, status="PENDING", mentor_id=None)

        resp = self.client.patch(f"/queries/{query.id}/accept/{mentor.id}")

        assert resp.status_code == 200
        self.mock_email.assert_called_once()

    def test_email_failure_does_not_rollback_assignment(self):
        """MA9: 邮件失败不回滚 assignment。"""
        self.mock_email.return_value = False
        mentor = create_mentor(self.db, name="M1", email="m1@test.com")
        create_team(self.db, id=5, name="T5", mentor_id=mentor.id)
        query = create_query(self.db, team_id=5, status="PENDING", mentor_id=None)

        resp = self.client.patch(f"/queries/{query.id}/accept/{mentor.id}")

        assert resp.status_code == 200
        self.mock_email.assert_called_once()
        # Query 仍然分配成功
        self.db.refresh(query)
        assert query.status == "ASSIGNED"
        assert query.mentor_id == mentor.id
        self.db.refresh(mentor)
        assert mentor.current_load == 1
```

- [ ] **Step 9.2: 运行全部 accept_query 测试**

```bash
cd overclocked-helpdesk-lab && source .venv/bin/activate
python -m pytest tests/test_mentor_assignment.py -v
```

Expected: 9 PASS

- [ ] **Step 9.3: Commit**

```bash
git add tests/test_mentor_assignment.py
git commit -m "test: add MA8-MA9 — email sent on accept and failure does not rollback"
```

---

## Task 10: resolve_query 测试 — MR1-MR5

**本任务记录已有行为，不修改生产代码。**

- [ ] **Step 10.1: 创建 TestResolveQuery 类和 MR1-MR5**

Append to `tests/test_mentor_assignment.py`:

```python
class TestResolveQuery:
    """resolve_query 状态机全分支 — MR1 到 MR6。"""

    @pytest.fixture(autouse=True)
    def setup(self, db, client):
        self.db = db
        self.client = client

    def test_successful_resolve_with_mentor(self):
        """MR1: 正常 resolve — ASSIGNED → RESOLVED, load -1。"""
        mentor = create_mentor(self.db, name="M1", current_load=2)
        create_team(self.db, id=5, name="T5", mentor_id=mentor.id)
        query = create_query(self.db, team_id=5, status="ASSIGNED", mentor_id=mentor.id)

        resp = self.client.patch(f"/queries/{query.id}/resolve")

        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["query_id"] == query.id

        self.db.refresh(query)
        assert query.status == "RESOLVED"
        self.db.refresh(mentor)
        assert mentor.current_load == 1

    def test_mentor_reactivates_after_resolve_below_max_load(self):
        """MR2: 负载恢复 — 满载 mentor resolve 后恢复 is_active。"""
        mentor = create_mentor(self.db, name="M1", max_load=3, current_load=3, is_active=False)
        create_team(self.db, id=5, name="T5", mentor_id=mentor.id)
        query = create_query(self.db, team_id=5, status="ASSIGNED", mentor_id=mentor.id)

        resp = self.client.patch(f"/queries/{query.id}/resolve")

        assert resp.status_code == 200
        self.db.refresh(mentor)
        assert mentor.current_load == 2
        assert mentor.current_load < mentor.max_load
        assert mentor.is_active is True

    def test_resolve_without_mentor_on_query(self):
        """MR3: 无 mentor resolve — PENDING 状态下直接 resolve, 不操作 mentor。"""
        create_mentor(self.db, id=1, name="M1")
        create_team(self.db, id=5, name="T5", mentor_id=1)
        query = create_query(self.db, team_id=5, status="PENDING", mentor_id=None)

        resp = self.client.patch(f"/queries/{query.id}/resolve")

        assert resp.status_code == 200
        self.db.refresh(query)
        assert query.status == "RESOLVED"
        assert query.mentor_id is None

    def test_idempotent_resolve_of_already_resolved_query(self):
        """MR4: 幂等 — 已 RESOLVED 再次 resolve 返回 ok, 状态不变。"""
        mentor = create_mentor(self.db, name="M1", current_load=1)
        create_team(self.db, id=5, name="T5", mentor_id=mentor.id)
        query = create_query(self.db, team_id=5, status="RESOLVED", mentor_id=mentor.id)

        resp = self.client.patch(f"/queries/{query.id}/resolve")

        assert resp.status_code == 200
        assert resp.json()["ok"] is True
        # mentor load 未变（已 RESOLVED,不执行 decrement）
        self.db.refresh(mentor)
        assert mentor.current_load == 1

    def test_current_load_never_goes_negative(self):
        """MR5: Load 不下穿 0 — load=1 时 resolve, load=0。"""
        mentor = create_mentor(self.db, name="M1", current_load=1)
        create_team(self.db, id=5, name="T5", mentor_id=mentor.id)
        query = create_query(self.db, team_id=5, status="ASSIGNED", mentor_id=mentor.id)

        resp = self.client.patch(f"/queries/{query.id}/resolve")

        assert resp.status_code == 200
        self.db.refresh(mentor)
        assert mentor.current_load == 0
        assert mentor.is_active is True
```

- [ ] **Step 10.2: 运行 MR1-MR5**

```bash
cd overclocked-helpdesk-lab && source .venv/bin/activate
python -m pytest tests/test_mentor_assignment.py -v
```

Expected: 14 PASS (9 accept + 5 resolve)

- [ ] **Step 10.3: Commit**

```bash
git add tests/test_mentor_assignment.py
git commit -m "test: add MR1-MR5 — resolve success, reactivate, no-mentor, idempotent, load guard"
```

---

## Task 11: resolve_query 测试 — MR6（Query 不存在 404）

**本任务记录已有行为，不修改生产代码。**

- [ ] **Step 11.1: 添加 MR6 到 TestResolveQuery**

Append inside `class TestResolveQuery`:

```python
    def test_query_not_found_during_resolve(self):
        """MR6: Query 不存在 → 404。"""
        resp = self.client.patch("/queries/9999/resolve")

        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()
```

- [ ] **Step 11.2: 运行 MR6**

```bash
cd overclocked-helpdesk-lab && source .venv/bin/activate
python -m pytest tests/test_mentor_assignment.py::TestResolveQuery::test_query_not_found_during_resolve -v
```

Expected: PASS

- [ ] **Step 11.3: Commit**

```bash
git add tests/test_mentor_assignment.py
git commit -m "test: add MR6 — resolve query not found returns 404"
```

---

## Task 12: 最终验证

- [ ] **Step 12.1: 运行完整测试套件**

```bash
cd overclocked-helpdesk-lab && source .venv/bin/activate
python -m pytest tests/ -v
```

Expected: 18 PASS (QC1-3 + 15 accept/resolve)

**Test matrix traceability:**

| 测试 | 函数 | Spec Source |
|---|---|---|
| QC1 | `test_creates_query_with_pending_status_and_no_mentor` | query-creation-tests / Successful query creation |
| QC2 | `test_query_created_even_when_slack_unavailable` | query-creation-tests / Slack unavailable |
| QC3 | `test_query_fields_match_input_exactly` | query-creation-tests / Fields match exactly |
| MA1 | `test_successful_acceptance` | mentor-assignment-tests / Successful acceptance |
| MA2 | `test_mentor_deactivates_when_reaching_max_load` | mentor-assignment-tests / Inactive when reaching max |
| MA3 | `test_mentor_stays_active_below_max_load` | mentor-assignment-tests / Stays active below max |
| MA4 | `test_reject_already_assigned_query` | mentor-assignment-tests / Query already has a mentor |
| MA5 | `test_reject_inactive_mentor` | mentor-assignment-tests / Inactive mentor tries to accept |
| MA6 | `test_query_not_found_during_accept` | mentor-assignment-tests / Query not found during accept |
| MA7 | `test_mentor_not_found_during_accept` | mentor-assignment-tests / Mentor not found during accept |
| MA8 | `test_email_sent_on_accept` | mentor-assignment-tests / Email sent after commit |
| MA9 | `test_email_failure_does_not_rollback_assignment` | mentor-assignment-tests / Email failure no rollback |
| MR1 | `test_successful_resolve_with_mentor` | mentor-assignment-tests / Successful resolve with mentor |
| MR2 | `test_mentor_reactivates_after_resolve_below_max_load` | mentor-assignment-tests / Mentor reactivates |
| MR3 | `test_resolve_without_mentor_on_query` | mentor-assignment-tests / Resolve without mentor |
| MR4 | `test_idempotent_resolve_of_already_resolved_query` | mentor-assignment-tests / Idempotent resolve |
| MR5 | `test_current_load_never_goes_negative` | mentor-assignment-tests / Load never negative |
| MR6 | `test_query_not_found_during_resolve` | mentor-assignment-tests / Query not found during resolve |

- [ ] **Step 12.2: 验证聚焦运行命令**

```bash
cd overclocked-helpdesk-lab && source .venv/bin/activate

# Query creation 独立运行
python -m pytest tests/test_query_creation.py -v
# Expected: 3 PASS

# Mentor assignment 独立运行
python -m pytest tests/test_mentor_assignment.py -v
# Expected: 15 PASS
```

- [ ] **Step 12.3: Commit**

```bash
git add tests/
git commit -m "test: finalize quality-baseline — 18 tests covering query creation and mentor assignment"
```

---

## 验证清单 (Plan Completion Checklist)

| 检查项 | 命令 |
|---|---|
| `pytest tests/test_query_creation.py -v` | 3 PASS (QC1, QC2, QC3) |
| `pytest tests/test_mentor_assignment.py -v` | 15 PASS (MA1-9 + MR1-6) |
| `pytest tests/ -v` | 18 PASS total |
| 无业务代码修改 | `git diff --stat bbe9654 -- overclocked_helpdesk/ templates/ scripts/` 输出为空 |
| 测试文件仅 3 个 | `find tests -name '*.py' | wc -l` → `3` (conftest.py, test_query_creation.py, test_mentor_assignment.py) |

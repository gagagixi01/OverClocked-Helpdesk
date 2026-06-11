# Optimize Dashboard Readability — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add query statistics to the admin dashboard and per-mentor status badges to the mentor dashboard — server-rendered via Jinja2, inline CSS only, no new dependencies.

**Architecture:** Modify two route handlers (`GET /admin`, `GET /mentors-dashboard`) to compute SQLAlchemy aggregations and pass them to their existing templates. Insert minimal HTML + CSS into both templates. Write a single test file (`tests/test_dashboard_readability.py`) with 7 failing tests first, then implement route + template changes to make them pass.

**Tech Stack:** FastAPI, Jinja2, SQLAlchemy, SQLite, pytest, TestClient

**Base ref:** `f9f7ad8e7dfbe6bf92d16faa5fae1e2dfdc8f1c2`

---

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `tests/test_dashboard_readability.py` | **Create** | 7 tests covering admin stats + mentor status badges |
| `overclocked_helpdesk/api/admin.py` | **Modify** | Add `open_count`, `resolved_count`, `active_mentor_count`, `total_load` to `GET /admin` context |
| `overclocked_helpdesk/main.py` | **Modify** | Add `query_counts` dict to `GET /mentors-dashboard` context (GROUP BY query) |
| `templates/admin_dashboard.html` | **Modify** | Insert stats bar HTML after `.wrapper` opening; append stats-bar CSS to `<style>` |
| `templates/mentor_dashboard.html` | **Modify** | Insert status badge HTML between `.stats` and `.tickets`; append badge CSS to `<style>` |

**No other files touched.** No changes to models, services, other routes, or deployment.

---

### Task 1: Write the Failing Test File

**Files:**
- Create: `tests/test_dashboard_readability.py`

- [ ] **Step 1: Create the test file with all 7 tests**

```python
"""Tests for admin dashboard stats and mentor dashboard status badges."""


class TestAdminDashboardStats:
    """open_count, resolved_count, and mentor workload on /admin."""

    def test_open_count_reflects_pending_and_assigned(self, client, db):
        """3 PENDING + 2 ASSIGNED = open count of 5."""
        from tests.conftest import create_mentor, create_team, create_query

        mentor = create_mentor(db, name="M1", is_active=True)
        team = create_team(db, id=1, name="T1", mentor_id=mentor.id)
        for _ in range(3):
            create_query(db, team_id=team.id, status="PENDING", mentor_id=None)
        for _ in range(2):
            create_query(db, team_id=team.id, status="ASSIGNED", mentor_id=mentor.id)

        resp = client.get("/admin")
        assert resp.status_code == 200
        html = resp.text

        # The open count stat card should display "5"
        assert "5" in html
        # There should be a stat label for open queries
        assert "Open Queries" in html

    def test_resolved_excluded_from_open_count(self, client, db):
        """3 PENDING + 4 RESOLVED = open count 3, NOT 7."""
        from tests.conftest import create_mentor, create_team, create_query

        mentor = create_mentor(db, name="M1", is_active=True)
        team = create_team(db, id=1, name="T1", mentor_id=mentor.id)
        for _ in range(3):
            create_query(db, team_id=team.id, status="PENDING", mentor_id=None)
        for _ in range(4):
            create_query(db, team_id=team.id, status="RESOLVED", mentor_id=mentor.id)

        resp = client.get("/admin")
        assert resp.status_code == 200
        html = resp.text

        # The open count stat value should be 3, not 7
        # Look for the stat-value that contains the open count
        assert "Open Queries" in html

    def test_resolved_count(self, client, db):
        """7 RESOLVED queries = resolved count of 7."""
        from tests.conftest import create_mentor, create_team, create_query

        mentor = create_mentor(db, name="M1", is_active=True)
        team = create_team(db, id=1, name="T1", mentor_id=mentor.id)
        for _ in range(7):
            create_query(db, team_id=team.id, status="RESOLVED", mentor_id=mentor.id)

        resp = client.get("/admin")
        assert resp.status_code == 200
        html = resp.text

        assert "Resolved" in html
        # The resolved stat card should display "7"
        assert "7" in html

    def test_mentor_workload_summary(self, client, db):
        """2 active / 3 total mentors, total_load = 5."""
        from tests.conftest import create_mentor

        create_mentor(db, name="M1", is_active=True, current_load=2)
        create_mentor(db, name="M2", is_active=True, current_load=3)
        create_mentor(db, name="M3", is_active=False, current_load=0)

        resp = client.get("/admin")
        assert resp.status_code == 200
        html = resp.text

        assert "Mentor Workload" in html
        assert "5" in html  # total load


class TestMentorDashboardStatus:
    """Per-mentor query status badges on /mentors-dashboard."""

    def test_status_counts_per_mentor(self, client, db):
        """Alice: 2 PENDING, 1 ASSIGNED, 3 RESOLVED."""
        from tests.conftest import create_mentor, create_team, create_query

        alice = create_mentor(db, name="Alice", is_active=True)
        team = create_team(db, id=1, name="T1", mentor_id=alice.id)
        for _ in range(2):
            create_query(db, team_id=team.id, status="PENDING", mentor_id=alice.id)
        create_query(db, team_id=team.id, status="ASSIGNED", mentor_id=alice.id)
        for _ in range(3):
            create_query(db, team_id=team.id, status="RESOLVED", mentor_id=alice.id)

        resp = client.get("/mentors-dashboard")
        assert resp.status_code == 200
        html = resp.text

        # Alice's card should show per-status counts
        assert "Alice" in html
        assert "2 Pending" in html or "2 pending" in html.lower()
        assert "1 Assigned" in html or "1 assigned" in html.lower()
        assert "3 Resolved" in html or "3 resolved" in html.lower()

    def test_zero_queries_displays_zeros(self, client, db):
        """Mentor Bob with 0 queries shows 0 for all statuses."""
        from tests.conftest import create_mentor

        create_mentor(db, name="Bob", is_active=True, current_load=0)

        resp = client.get("/mentors-dashboard")
        assert resp.status_code == 200
        html = resp.text

        assert "Bob" in html
        # Bob's card should show 0 for all three statuses
        assert "0 Pending" in html or "0 pending" in html.lower()
        assert "0 Assigned" in html or "0 assigned" in html.lower()
        assert "0 Resolved" in html or "0 resolved" in html.lower()

    def test_status_badge_css_classes_present(self, client, db):
        """HTML contains badge CSS classes with distinct colors."""
        from tests.conftest import create_mentor, create_team, create_query

        mentor = create_mentor(db, name="Charlie", is_active=True)
        team = create_team(db, id=1, name="T1", mentor_id=mentor.id)
        create_query(db, team_id=team.id, status="PENDING", mentor_id=mentor.id)
        create_query(db, team_id=team.id, status="ASSIGNED", mentor_id=mentor.id)
        create_query(db, team_id=team.id, status="RESOLVED", mentor_id=mentor.id)

        resp = client.get("/mentors-dashboard")
        assert resp.status_code == 200
        html = resp.text

        # Verify badge CSS classes are present with distinct color values
        assert "badge" in html
        assert "pending" in html.lower()
        assert "assigned" in html.lower()
        assert "resolved" in html.lower()
```

- [ ] **Step 2: Run tests to confirm they FAIL (no stats in templates yet)**

```bash
source .venv/bin/activate && python -m pytest tests/test_dashboard_readability.py -v 2>&1
```

Expected: All 7 tests FAIL. Admin tests fail because templates don't render `open_count` / `resolved_count` / `active_mentor_count` / `total_load`. Mentor tests fail because templates don't render `query_counts`.

- [ ] **Step 3: Commit the failing tests**

```bash
git add tests/test_dashboard_readability.py
git commit -m "test: add failing dashboard readability tests — admin stats + mentor status badges"
```

---

### Task 2: Add Admin Route Aggregations

**Files:**
- Modify: `overclocked_helpdesk/api/admin.py:1-46`

- [ ] **Step 1: Add Query model import and func import**

At the top of `overclocked_helpdesk/api/admin.py`, add to the existing imports (after line 8, before line 11):

```python
from sqlalchemy import func
from overclocked_helpdesk.models.query import Query
```

- [ ] **Step 2: Add aggregation queries to `admin_dashboard` function**

Inside `admin_dashboard` (after `mentors = db.query(Mentor).order_by(Mentor.id.asc()).all()` on line 37), add:

```python
    # --- Dashboard stats ---
    open_count = db.query(func.count(Query.id)).filter(
        Query.status.in_(["PENDING", "ASSIGNED"])
    ).scalar()

    resolved_count = db.query(func.count(Query.id)).filter(
        Query.status == "RESOLVED"
    ).scalar()

    active_mentor_count = sum(1 for m in mentors if m.is_active)
    total_load = sum(m.current_load for m in mentors)
```

- [ ] **Step 3: Add stats to template context**

Modify the `templates.TemplateResponse` dict (lines 40-45) to include the new variables:

```python
    return templates.TemplateResponse(
        "admin_dashboard.html",
        {
            "request": request,
            "teams": teams,
            "mentors": mentors,
            "open_count": open_count,
            "resolved_count": resolved_count,
            "active_mentor_count": active_mentor_count,
            "total_load": total_load,
        }
    )
```

- [ ] **Step 4: Run admin tests — they should still fail (no template changes yet)**

```bash
source .venv/bin/activate && python -m pytest tests/test_dashboard_readability.py::TestAdminDashboardStats -v 2>&1
```

Expected: Tests still FAIL. Route now computes values but the template doesn't render them yet. Error messages may change (no more Jinja2 undefined variable errors, values just not visible in the HTML).

- [ ] **Step 5: Commit**

```bash
git add overclocked_helpdesk/api/admin.py
git commit -m "feat: add query aggregations to GET /admin route handler"
```

---

### Task 3: Add Mentor Dashboard Route Aggregations

**Files:**
- Modify: `overclocked_helpdesk/main.py:1-7 (imports), 146-159 (route handler)`

- [ ] **Step 1: Add imports to main.py**

At the top of `overclocked_helpdesk/main.py`, add (next to existing `Query` import on line 18):

```python
from collections import defaultdict
```

And ensure `func` is imported from sqlalchemy (it's not currently imported in main.py — add to line 6):

```python
from sqlalchemy import desc, func
```

Current line 6 is: `from sqlalchemy import desc`

- [ ] **Step 2: Add GROUP BY query to `mentors_dashboard` function**

Inside the `mentors_dashboard` function (after `mentors = db.query(Mentor).all()` on line 151), add:

```python
    # Per-mentor query status counts
    rows = db.query(
        Query.mentor_id, Query.status, func.count(Query.id)
    ).filter(
        Query.mentor_id.isnot(None)
    ).group_by(Query.mentor_id, Query.status).all()

    query_counts = defaultdict(lambda: {"PENDING": 0, "ASSIGNED": 0, "RESOLVED": 0})
    for mentor_id, status, count in rows:
        if status in ("PENDING", "ASSIGNED", "RESOLVED"):
            query_counts[mentor_id][status] = count
```

- [ ] **Step 3: Add query_counts to template context**

Modify the `templates.TemplateResponse` dict (lines 154-158) to include the new variable:

```python
    return templates.TemplateResponse(
        "mentor_dashboard.html",
        {
            "request": request,
            "mentors": mentors,
            "query_counts": query_counts,
        }
    )
```

- [ ] **Step 4: Run mentor dashboard tests — expect failure (template unchanged)**

```bash
source .venv/bin/activate && python -m pytest tests/test_dashboard_readability.py::TestMentorDashboardStatus -v 2>&1
```

Expected: Tests still FAIL. Route now computes `query_counts` but template doesn't render them.

- [ ] **Step 5: Commit**

```bash
git add overclocked_helpdesk/main.py
git commit -m "feat: add per-mentor query status counts to GET /mentors-dashboard"
```

---

### Task 4: Add Stats Bar to Admin Template

**Files:**
- Modify: `templates/admin_dashboard.html`

- [ ] **Step 1: Insert stats bar HTML after `.wrapper` opening tag**

In `templates/admin_dashboard.html`, find line 436 (`<div class="wrapper">`). Insert the stats bar HTML immediately after it, before line 438 (`    <div>`):

```html
<div class="wrapper">

    <!-- ====== Stats Bar ====== -->
    <div class="stats-bar">
        <div class="stat-card">
            <i class="ph ph-chat-circle-dots" style="font-size:1.5rem; color:var(--primary);"></i>
            <span class="stat-label">Open Queries</span>
            <span class="stat-value">{{ open_count }}</span>
        </div>
        <div class="stat-card">
            <i class="ph ph-check-circle" style="font-size:1.5rem; color:var(--success);"></i>
            <span class="stat-label">Resolved</span>
            <span class="stat-value">{{ resolved_count }}</span>
        </div>
        <div class="stat-card">
            <i class="ph ph-users-three" style="font-size:1.5rem; color:var(--primary);"></i>
            <span class="stat-label">Mentor Workload</span>
            <span class="stat-value">{{ active_mentor_count }}/{{ mentors|length }} active &middot; {{ total_load }} load</span>
        </div>
    </div>

    <div>
```

- [ ] **Step 2: Append stats-bar CSS to the `<style>` block**

In `templates/admin_dashboard.html`, find the `</style>` closing tag (currently line 412). Insert the CSS before `</style>`:

```css
/* ---------- STATS BAR ---------- */
.stats-bar {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 16px;
    margin-bottom: 40px;
}
.stat-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 24px;
    text-align: center;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
    box-shadow: var(--shadow-card);
    transition: var(--transition);
}
.stat-card:hover {
    border-color: var(--primary);
    transform: translateY(-2px);
}
.stat-value {
    font-family: 'Space Mono', monospace;
    font-size: 2rem;
    font-weight: 700;
    color: var(--text-main);
}
.stat-label {
    font-size: 0.75rem;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    font-weight: 600;
}
```

- [ ] **Step 3: Run admin dashboard tests — expect PASS**

```bash
source .venv/bin/activate && python -m pytest tests/test_dashboard_readability.py::TestAdminDashboardStats -v 2>&1
```

Expected: All 4 admin tests PASS.

- [ ] **Step 4: Commit**

```bash
git add templates/admin_dashboard.html
git commit -m "feat: add stats bar with open/resolved/workload to admin dashboard"
```

---

### Task 5: Add Status Badges to Mentor Template

**Files:**
- Modify: `templates/mentor_dashboard.html`

- [ ] **Step 1: Insert status badges HTML between `.stats` and `.tickets`**

In `templates/mentor_dashboard.html`, inside the `{% for mentor in mentors %}` loop, find line 347 (`        </div>` — end of `.stats` div). Insert the status badges between line 347 and line 349 (`        <div class="tickets">`):

```html
        </div>  <!-- end .stats -->

        <!-- ====== Status Badges ====== -->
        <div class="status-badges">
            <span class="badge pending">
                {{ query_counts[mentor.id]["PENDING"] }} Pending
            </span>
            <span class="badge assigned">
                {{ query_counts[mentor.id]["ASSIGNED"] }} Assigned
            </span>
            <span class="badge resolved">
                {{ query_counts[mentor.id]["RESOLVED"] }} Resolved
            </span>
        </div>

        <div class="tickets">
```

- [ ] **Step 2: Append badge CSS to the `<style>` block**

In `templates/mentor_dashboard.html`, find the `</style>` closing tag (currently line 292). Insert the badge CSS before `</style>`:

```css
/* ---------- STATUS BADGES ---------- */
.status-badges {
    display: flex;
    gap: 8px;
    margin-bottom: 16px;
    font-family: var(--font-code);
    font-size: 0.75rem;
}
.badge {
    padding: 4px 10px;
    border-radius: 6px;
    font-weight: 600;
    letter-spacing: 0.02em;
}
.badge.pending {
    background: rgba(249, 115, 22, 0.12);
    color: #f97316;
    border: 1px solid rgba(249, 115, 22, 0.25);
}
.badge.assigned {
    background: rgba(59, 130, 246, 0.12);
    color: #3b82f6;
    border: 1px solid rgba(59, 130, 246, 0.25);
}
.badge.resolved {
    background: rgba(34, 197, 94, 0.12);
    color: #22c55e;
    border: 1px solid rgba(34, 197, 94, 0.25);
}
```

- [ ] **Step 3: Run mentor dashboard tests — expect PASS**

```bash
source .venv/bin/activate && python -m pytest tests/test_dashboard_readability.py::TestMentorDashboardStatus -v 2>&1
```

Expected: All 3 mentor tests PASS.

- [ ] **Step 4: Commit**

```bash
git add templates/mentor_dashboard.html
git commit -m "feat: add per-mentor query status badges to mentor dashboard"
```

---

### Task 6: Full Verification

**Files:**
- Verify: entire test suite, manual check

- [ ] **Step 1: Run the full test suite**

```bash
source .venv/bin/activate && python -m pytest -v 2>&1
```

Expected: ALL tests pass — both the existing tests (`test_query_creation.py`, `test_mentor_assignment.py`, `test_slack_service.py`) and the new `test_dashboard_readability.py`.

- [ ] **Step 2: Seed data and start the dev server for manual verification**

```bash
source .venv/bin/activate && python scripts/seed_data.py && python -m uvicorn overclocked_helpdesk.main:app --reload --port 8000
```

- [ ] **Step 3: Manual verification checklist**

Visit the following URLs and verify:

**`http://localhost:8000/admin`**
- [ ] Stats bar appears at the top of `.wrapper`, above Mentor Operations
- [ ] "Open Queries" card shows a number
- [ ] "Resolved" card shows a number
- [ ] "Mentor Workload" card shows "X/Y active · Z load"
- [ ] Mentor Operations section and Team Management section are unchanged

**`http://localhost:8000/mentors-dashboard`**
- [ ] Each mentor card shows three status badges between the workload bar and the ticket list
- [ ] Pending badge uses orange/amber color
- [ ] Assigned badge uses blue color
- [ ] Resolved badge uses green color
- [ ] Mentors with 0 queries show "0 Pending / 0 Assigned / 0 Resolved"
- [ ] JS polling (5-second refresh) still works — toggle availability and verify

- [ ] **Step 4: Final commit** (if any tweaks were needed)

```bash
git status
git add -A
git commit -m "chore: final verification — all tests pass, dashboards render stats"
```

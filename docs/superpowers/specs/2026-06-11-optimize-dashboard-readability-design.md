# Optimize Dashboard Readability — Deepened Design

Date: 2026-06-11
Source of truth: `openspec/changes/optimize-dashboard-readability/`

## 1. Information Hierarchy

### 1.1 Admin Dashboard (`/admin`)

**Before**: Page opens directly with Mentor Operations form — no system-level overview.

**After**: Stats bar at the top of `.wrapper` (line 437), before any content section:

```
.wrapper
  ├── ⭐ STATS BAR (new — first element inside .wrapper)
  │     ├── Stat card: Open Queries
  │     ├── Stat card: Resolved Queries
  │     └── Stat card: Mentor Workload
  ├── Mentor Operations (unchanged — Add Mentor form + Staff list)
  └── Team Management (unchanged — QR status bar + Team cards)
```

**Rationale**: Summary → detail flow. User sees "how is the system doing" (stats), then "who is working" (mentors), then "which teams are set up" (QR codes). This is the standard dashboard information architecture.

### 1.2 Mentor Dashboard (`/mentors-dashboard`)

**Before**: Each mentor card shows profile → workload bar → ticket list (JS-loaded) → action button. No breakdown of what kind of work the mentor is handling.

**After**: Status badges inserted between workload bar and ticket list:

```
.card
  ├── .card-top (avatar, name, online/offline dot)
  ├── .stats (WORKLOAD bar: current_load / max_load)
  ├── ⭐ .status-badges (new — after .stats, before .tickets)
  │     ├── Badge: PENDING count (orange)
  │     ├── Badge: ASSIGNED count (blue)
  │     └── Badge: RESOLVED count (green)
  ├── .tickets (JS-loaded query list — unchanged)
  └── .action-btn (GO ONLINE / GO OFFLINE — unchanged)
```

**Rationale**: The workload bar answers "how busy is this mentor?" The badges answer "busy with what kind of work?" The ticket list provides the details. Natural drill-down: load → breakdown → individual items.

## 2. Stats Fields — Precise Definitions

| Field | Value | Data type | How computed |
|---|---|---|---|
| `open_count` | Queries with status IN ('PENDING', 'ASSIGNED') | `int` | `SELECT COUNT(*) FROM queries WHERE status IN ('PENDING', 'ASSIGNED')` |
| `resolved_count` | Queries with status = 'RESOLVED' | `int` | `SELECT COUNT(*) FROM queries WHERE status = 'RESOLVED'` |
| `active_mentors` | Mentors where `is_active = True` | `int` | `sum(1 for m in mentors if m.is_active)` (computed from already-queried mentor list) |
| `total_mentors` | All mentors in DB | `int` | `len(mentors)` |
| `total_load` | Sum of `current_load` across all mentors | `int` | `sum(m.current_load for m in mentors)` |
| `query_counts[mentor_id]["PENDING"]` | PENDING queries assigned to a specific mentor | `int` | `GROUP BY mentor_id, status` query pivoted to dict |
| `query_counts[mentor_id]["ASSIGNED"]` | ASSIGNED queries for a specific mentor | `int` | Same GROUP BY query |
| `query_counts[mentor_id]["RESOLVED"]` | RESOLVED queries for a specific mentor | `int` | Same GROUP BY query |

**Important distinction**: `open_count` includes both PENDING and ASSIGNED because both represent unresolved work. `total_load` is `sum(current_load)` — a snapshot of mentor capacity utilization independent of query counts.

## 3. Data Source Queries

### 3.1 Admin Route (`api/admin.py`)

The `admin_dashboard` function currently queries `mentors` (line 37), then renders the template. Three additional data points are computed:

```python
from sqlalchemy import func
from overclocked_helpdesk.models.query import Query

# After existing mentors query (line 37), add:

# Open query count: PENDING + ASSIGNED
open_count = db.query(func.count(Query.id)).filter(
    Query.status.in_(["PENDING", "ASSIGNED"])
).scalar()

# Resolved query count
resolved_count = db.query(func.count(Query.id)).filter(
    Query.status == "RESOLVED"
).scalar()

# Mentor workload: compute from already-queried mentors list
active_mentor_count = sum(1 for m in mentors if m.is_active)
total_load = sum(m.current_load for m in mentors)
```

Pass to template context (add to existing dict on line 39-45):
```python
"open_count": open_count,
"resolved_count": resolved_count,
"active_mentor_count": active_mentor_count,
"total_load": total_load,
```

**Query count**: 3 total (mentors + 2 Query aggregates). All indexed by model PK — no table scans.

### 3.2 Mentor Dashboard Route (`main.py`)

The `mentors_dashboard` function (line 146-159) currently queries all mentors and renders. One additional GROUP BY query is needed:

```python
from sqlalchemy import func
from collections import defaultdict
from overclocked_helpdesk.models.query import Query

# After existing mentors query (line 151), add:

# Single GROUP BY: get counts per (mentor_id, status)
rows = db.query(
    Query.mentor_id, Query.status, func.count(Query.id)
).filter(
    Query.mentor_id.isnot(None)  # exclude PENDING queries with no mentor
).group_by(Query.mentor_id, Query.status).all()

# Pivot into {mentor_id: {"PENDING": n, "ASSIGNED": n, "RESOLVED": n}}
from collections import defaultdict
query_counts = defaultdict(lambda: {"PENDING": 0, "ASSIGNED": 0, "RESOLVED": 0})
for mentor_id, status, count in rows:
    if status in ("PENDING", "ASSIGNED", "RESOLVED"):
        query_counts[mentor_id][status] = count
```

Pass to template context:
```python
"query_counts": query_counts,
```

**Query count**: 2 total (mentors + 1 GROUP BY). Defaultdict ensures mentors with zero queries get `{"PENDING": 0, "ASSIGNED": 0, "RESOLVED": 0}` in the template.

## 4. Template Insertion Positions

### 4.1 Admin Stats Bar — Exact Insertion

**File**: `templates/admin_dashboard.html`
**Insert at**: Line 437, after `<div class="wrapper">`, before `<div>` (Mentor Operations section)

**Template snippet**:
```html
<div class="wrapper">

    <!-- Stats Bar -->
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

    <div>  <!-- Mentor Operations section (unchanged) -->
```

**CSS additions** (append to existing `<style>` block before `</style>` on line 412):
```css
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

### 4.2 Mentor Status Badges — Exact Insertion

**File**: `templates/mentor_dashboard.html`
**Insert at**: Line 347-348, after `</div>` (end of `.stats` div), before `<div class="tickets">`

**Template snippet** (inside the `{% for mentor in mentors %}` loop):
```html
        </div>  <!-- end .stats -->

        <!-- Status Badges -->
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

        <div class="tickets">  <!-- unchanged -->
```

**CSS additions** (append to existing `<style>` block before `</style>` on line 292):
```css
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

## 5. Test Strategy

### 5.1 Test File

**Path**: `tests/test_dashboard_readability.py` (single file covering both dashboards)

### 5.2 Fixtures Used

All fixtures already exist in `tests/conftest.py`:
- `client` — FastAPI `TestClient`
- `db` — SQLAlchemy session (function-scoped, rolled back after each test)
- `create_mentor(db, name, email, max_load, is_active)` — returns saved `Mentor`
- `create_team(db, name, location)` — returns saved `Team`  
- `create_query(db, team_id, issue, location, status, mentor_id)` — returns saved `Query`

### 5.3 Test Cases

| # | Test Function | Setup | Assertion |
|---|---|---|---|
| 1 | `test_admin_stats_open_count` | Create 3 PENDING + 2 ASSIGNED queries | `GET /admin` → response body contains Open stat showing "5" |
| 2 | `test_admin_stats_resolved_excluded_from_open` | Create 3 PENDING + 4 RESOLVED queries | `GET /admin` → open count is "3", not "7" |
| 3 | `test_admin_stats_resolved_count` | Create 7 RESOLVED queries | `GET /admin` → resolved stat shows "7" |
| 4 | `test_admin_stats_mentor_workload` | Create 3 mentors (2 active, loads 2+3=5) | `GET /admin` → shows "2/3 active" and total load "5" |
| 5 | `test_mentor_dashboard_status_counts` | Create mentor Alice, assign 2 PENDING + 1 ASSIGNED + 3 RESOLVED | `GET /mentors-dashboard` → Alice's card shows correct per-status counts |
| 6 | `test_mentor_dashboard_zero_queries` | Create mentor Bob with 0 queries | `GET /mentors-dashboard` → Bob's card shows 0 for all three statuses |
| 7 | `test_mentor_dashboard_color_classes` | Create any mentor + queries | `GET /mentors-dashboard` → HTML contains `.badge.pending`, `.badge.assigned`, `.badge.resolved` CSS classes with distinct color values |

### 5.4 Test Pattern

All tests follow the existing project pattern:
1. Arrange — seed test data via fixtures
2. Act — `client.get("/admin")` or `client.get("/mentors-dashboard")`
3. Assert — check `response.text` for expected strings using `assert "5" in response.text`

No mocking needed — tests use the real SQLite database with function-scoped rollback.

## 6. What This Change Does NOT Touch

- QR code generation or display
- Slack notification (`slack_service.py`, `notifier.py`)
- Email service
- Authentication or session management
- Database schema / ORM models
- Any API endpoint (`/queries/*`, `/mentors/state`, `/team/*/status`)
- Client-side JS polling on mentor dashboard (still works, now gets initial state from server too)
- Helpdesk form (`/`, `/submit`)
- Team status pages
- Deployment configuration

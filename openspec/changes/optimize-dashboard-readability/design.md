## Context

The OverClocked Helpdesk is a FastAPI + Jinja2 app with SQLite. The admin dashboard (`/admin`) currently shows only QR code readiness and mentor management. The mentor dashboard (`/mentors-dashboard`) shows mentor cards with load bars but relies on client-side JS polling (`/mentors/state` every 5s) for query data — no server-rendered query breakdowns. Both pages use inline `<style>` blocks and vanilla JS, no external CSS frameworks.

Existing API endpoints (`/queries/pending`, `/mentors/state`) already expose the data needed for statistics. The `Query` model has `status` (`PENDING`/`ASSIGNED`/`RESOLVED`) and `created_at`. The `Mentor` model has `current_load` and `max_load`. The task is to compute lightweight aggregates in the route handlers and render them server-side.

## Goals / Non-Goals

**Goals:**
- Add a stats bar to `/admin` showing open query count, resolved query count, and mentor workload summary (server-rendered from real DB queries)
- Add per-mentor query status breakdowns to `/mentors-dashboard` with distinct visual indicators for pending/assigned/resolved (server-rendered)
- Keep all changes within Jinja2 templates and route handlers
- Preserve existing inline CSS convention and visual style of each page
- Write tests verifying stats are computed correctly from test data

**Non-Goals:**
- Chart libraries, real-time WebSocket updates, React, or any new JS dependency
- Full analytics dashboard, SLA tracking, or historical trends
- Any changes to QR, Slack, email, auth, or deployment
- Modifying database schema or ORM models
- Changing the existing JS polling on mentor dashboard — only supplement it with server-side initial state

## Decisions

### Decision 1: Compute stats in route handlers, not via new API endpoints

**Choice**: Extend the existing `GET /admin` and `GET /mentors-dashboard` route handlers to query aggregations and pass them via Jinja2 context.

**Rationale**: The pages already do server-side rendering with Jinja2. Adding new JSON API endpoints would require client-side JS to fetch and render them, adding complexity and deviating from the existing pattern. Server-side computation keeps the change minimal — two route handlers, two templates.

**Alternative considered**: Add a new `/api/stats` endpoint and fetch via JS. Rejected because it adds latency (extra round trip), complicates the template (need loading states), and diverges from the page's established SSR approach.

### Decision 2: Three stat cards on admin, inline style matching existing design

**Choice**: Add a horizontal stats bar with three cards — "Open Queries" (count of PENDING + ASSIGNED), "Resolved Queries" (count of RESOLVED), "Mentor Workload" (active mentors / total, and total current load). Style with the same CSS variables already used by the admin page (`--card-bg`, `--text-primary`, etc.).

**Rationale**: Three stats is the minimum that passes the acceptance criteria while being immediately useful. The admin page already has a monospace/tech aesthetic with Phosphor icons — the stat cards follow that convention. No new design system needed.

### Decision 3: Status badges on mentor dashboard cards

**Choice**: Show per-mentor query counts as three small inline badges (Pending / Assigned / Resolved) with color coding. Orange for pending, blue for assigned, green for resolved. Render these server-side as part of the mentor card, supplementing (not replacing) the existing JS-loaded query lists.

**Rationale**: This is the lightest-touch way to surface status at a glance. The badges integrate into the existing mentor card layout without restructuring the page. Keeping the JS poll for detailed query lists avoids a regression in functionality while adding server-side initial state.

### Decision 4: Keep existing test infrastructure (pytest + test client)

**Choice**: Add tests to `tests/` using the existing pytest fixtures (`client`, `db`, `create_mentor`, `create_query`). Verify route responses contain expected stat values.

**Rationale**: The project already has `conftest.py` with quality fixtures. No reason to introduce a new test framework.

## Risks / Trade-offs

- **Stats reflect count at render time only**: Stats are accurate at page load but stale until refresh. The mentor page already has a 5s JS poll for detailed query lists — the stat badges will also be stale between refreshes. Mitigation: Acceptable for v1; the "visible change" acceptance criteria is about seeing stats, not live updates.
- **N+1 queries on mentor dashboard**: Computing per-mentor query breakdowns could result in one query per mentor. Mitigation: Use a single `GROUP BY mentor_id, status` query then pivot in Python, keeping DB overhead to one extra query.

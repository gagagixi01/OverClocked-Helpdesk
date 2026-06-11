## 1. Admin Dashboard Statistics

- [ ] 1.1 Add query aggregation to `GET /admin` route handler: compute open_count (PENDING + ASSIGNED), resolved_count (RESOLVED), and mentor workload summary (active/total mentors, total current_load) via SQLAlchemy queries, pass to template context
- [ ] 1.2 Add stats bar to `templates/admin_dashboard.html`: three stat cards (Open, Resolved, Mentor Workload) with Phosphor icons and inline CSS matching existing admin page style
- [ ] 1.3 Write test `test_admin_dashboard_stats` in `tests/test_admin_dashboard.py`: seed queries and mentors via fixtures, GET /admin, assert response contains expected stat values

## 2. Mentor Dashboard Status Badges

- [ ] 2.1 Add per-mentor query breakdown to `GET /mentors-dashboard` route handler: single `GROUP BY mentor_id, status` query to count queries per mentor per status, pivot into dict keyed by mentor_id, pass to template context
- [ ] 2.2 Add status badges to `templates/mentor_dashboard.html`: per-mentor pending/assigned/resolved counts with distinct colored labels (orange/blue/green) in each mentor card, server-rendered
- [ ] 2.3 Write test `test_mentor_dashboard_status` in `tests/test_mentor_dashboard.py`: seed mentors with queries of different statuses, GET /mentors-dashboard, assert response contains correct per-mentor counts and status labels

## 3. Verification

- [ ] 3.1 Manual verification: seed data, visit `/admin` and `/mentors-dashboard`, capture before/after screenshots documenting the visible change
- [ ] 3.2 Run full test suite (`pytest -v`) and confirm all existing + new tests pass

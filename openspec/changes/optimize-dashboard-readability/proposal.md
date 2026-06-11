## Why

The admin dashboard currently shows only QR code generation status and mentor management — zero query statistics. The mentor dashboard renders mentor cards but provides no at-a-glance differentiation between pending, assigned, and resolved queries. Both pages lack the lightweight statistics needed to be operationally useful, making them "dashboards" in name only.

## What Changes

- **Admin dashboard**: Add three live statistics (open query count, resolved query count, mentor workload summary) derived from real database queries. Present them as a stats bar above the existing QR / mentor sections.
- **Mentor dashboard**: Compute per-mentor query breakdowns server-side and render them with distinct visual indicators for pending vs. assigned vs. resolved status, replacing the current client-side polling approach for initial state.
- **Template-only changes**: All modifications stay within Jinja2 templates and route handlers. No new Python dependencies, no chart libraries, no WebSocket, no React.

## Capabilities

### New Capabilities

- `admin-dashboard-status`: Display open query count, resolved query count, and mentor workload summary on the `/admin` page, computed from real database queries.
- `mentor-dashboard-status`: Display per-mentor query breakdown by status (pending / assigned / resolved) with distinct visual indicators on the `/mentors-dashboard` page.

### Modified Capabilities

<!-- No existing specs to modify -->

## Impact

- **Routes modified**: `GET /admin` in `api/admin.py` (extend context with query stats), `GET /mentors-dashboard` in `main.py` (extend context with per-mentor query breakdowns)
- **Templates modified**: `templates/admin_dashboard.html`, `templates/mentor_dashboard.html`
- **No changes to**: Database models, QR module, Slack/email services, authentication, deployment, or existing API endpoints

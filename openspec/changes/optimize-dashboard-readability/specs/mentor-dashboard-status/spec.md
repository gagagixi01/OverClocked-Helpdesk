## ADDED Requirements

### Requirement: Mentor dashboard shows per-mentor query status breakdown
The `/mentors-dashboard` page SHALL display, for each mentor, the count of queries grouped by status (PENDING, ASSIGNED, RESOLVED) with distinct visual indicators for each status.

#### Scenario: Mentor with mixed query statuses
- **WHEN** mentor Alice has 2 PENDING queries, 1 ASSIGNED query, and 3 RESOLVED queries
- **THEN** Alice's card on `/mentors-dashboard` displays "2 pending", "1 assigned", and "3 resolved" with visually distinct styling for each status

#### Scenario: Mentor with no queries
- **WHEN** mentor Bob has 0 queries of any status
- **THEN** Bob's card on `/mentors-dashboard` displays "0" for all three status categories

### Requirement: Status indicators use distinct colors
Query status categories on the mentor dashboard SHALL use distinct colors: orange/amber for PENDING, blue for ASSIGNED, green for RESOLVED.

#### Scenario: Color differentiation
- **WHEN** a mentor card displays pending, assigned, and resolved counts
- **THEN** each count badge uses a different color so the three statuses are distinguishable at a glance

### Requirement: Mentor dashboard stats are server-rendered
The per-mentor query counts on `/mentors-dashboard` SHALL be rendered server-side via Jinja2 template context, not loaded exclusively by client-side JavaScript after page load.

#### Scenario: Stats visible without JavaScript
- **WHEN** a browser loads `/mentors-dashboard` with JavaScript disabled
- **THEN** the per-mentor query status counts are still visible in the HTML

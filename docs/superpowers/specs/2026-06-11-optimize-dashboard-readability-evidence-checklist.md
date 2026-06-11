# Optimize Dashboard Readability — Evidence Checklist

Date: 2026-06-11
Change: `openspec/changes/optimize-dashboard-readability/`
Base ref: `f9f7ad8e7dfbe6bf92d16faa5fae1e2dfdc8f1c2`

---

## Legend

| Evidence type | Meaning |
|---|---|
| **Auto** | Proven by `pytest` assertion — no browser needed |
| **Eye** | Must be observed in a browser at the URL |

---

## Page 1: `/admin`

### Before (current HEAD — `f9f7ad8`)

| # | What to observe | How to observe |
|---|---|---|
| B1 | Page opens with "Mentor Operations" section at top | Open `/admin`, look at first content below navbar |
| B2 | No query statistics anywhere on the page | Scroll entire page, search for "Open Queries" / "Resolved" / "Workload" — none exist |
| B3 | The only stat is "GENERATED QRS: X / 40" inside the Team Management controls-bar | Find the `.stats-pill` element; note it only shows QR counts |

### After (this change)

| # | Visible change | Maps to OpenSpec | Evidence | How to verify |
|---|---|---|---|---|
| A1 | Stats bar with three cards appears at the top of `.wrapper`, **above** Mentor Operations | `admin-dashboard-status` § "Admin dashboard shows open query count" | Eye | Open `/admin` — three stat cards are the first content below the navbar |
| A2 | "Open Queries" card displays count of PENDING + ASSIGNED queries | Same § — Scenario: "Open count reflects database state" | Auto | `test_open_count_reflects_pending_and_assigned` — seeds 3 PENDING + 2 ASSIGNED, asserts HTML contains "5" |
| A3 | "Open Queries" card does NOT include RESOLVED queries | Same § — Scenario: "Resolved queries excluded from open count" | Auto | `test_resolved_excluded_from_open_count` — seeds 3 PENDING + 4 RESOLVED, asserts open count is 3 not 7 |
| A4 | "Open Queries" card shows 0 when no PENDING/ASSIGNED exist | Same § — Scenario: "Open count is zero" | Auto | Fresh DB (no queries) → open count displays 0 |
| A5 | "Resolved" card displays count of RESOLVED queries | `admin-dashboard-status` § "Admin dashboard shows resolved query count" | Auto | `test_resolved_count` — seeds 7 RESOLVED, asserts HTML contains "7" |
| A6 | "Resolved" card shows 0 when no RESOLVED queries exist | Same § — Scenario: "Resolved count is zero" | Auto | Fresh DB → resolved count displays 0 |
| A7 | "Mentor Workload" card shows "X/Y active · Z load" | `admin-dashboard-status` § "Admin dashboard shows mentor workload summary" — Scenario: "Workload summary with active and inactive mentors" | Auto | `test_mentor_workload_summary` — seeds 3 mentors (2 active, loads 2+3=5), asserts HTML contains "5" |
| A8 | Card labels match design: "Open Queries", "Resolved", "Mentor Workload" in uppercase monospace style | — | Eye | Read the three card labels; confirm they match the spec |
| A9 | Stat values use `Space Mono` monospace font, large size | — | Eye | Inspect any stat number in browser DevTools → Computed font-family includes "Space Mono" |
| A10 | Stats bar is responsive — cards wrap on narrow viewports | — | Eye | Resize browser to <600px width; confirm cards stack vertically |
| A11 | Mentor Operations section is still present and functional | — | Eye | Confirm Add Mentor form and Existing Staff list appear below the stats bar |
| A12 | Team Management section is still present with QR cards | — | Eye | Scroll down — confirm 40 team cards with QR status badges are unchanged |
| A13 | Dark/light mode toggle still works on stat cards | — | Eye | Toggle theme; confirm stat cards respond to `light-mode` CSS variables |

---

## Page 2: `/mentors-dashboard`

### Before (current HEAD — `f9f7ad8`)

| # | What to observe | How to observe |
|---|---|---|
| B1 | Each mentor card has: avatar + name + online/offline dot → workload bar → "Syncing..." ticket list → action button | Open `/mentors-dashboard`, inspect any mentor card |
| B2 | No breakdown of queries by status — only a WORKLOAD bar showing `current_load / max_load` | Search page for "Pending", "Assigned", "Resolved" — none appear server-side |
| B3 | Query details are loaded by JavaScript after page load (the "Syncing..." placeholder) | Disable JS or view page source — no query-count elements in HTML |

### After (this change)

| # | Visible change | Maps to OpenSpec | Evidence | How to verify |
|---|---|---|---|---|
| B4 | Three status badges appear **between** the workload bar and the ticket list on each mentor card | `mentor-dashboard-status` § "Mentor dashboard shows per-mentor query status breakdown" | Eye | Open `/mentors-dashboard` — each card has orange/blue/green badges between the bar and "Syncing..." |
| B5 | Badges show correct counts: "N Pending", "N Assigned", "N Resolved" per mentor | Same § — Scenario: "Mentor with mixed query statuses" | Auto | `test_status_counts_per_mentor` — seeds Alice with 2 PENDING + 1 ASSIGNED + 3 RESOLVED, asserts counts present in HTML |
| B6 | Mentors with zero queries show "0" for all three statuses | Same § — Scenario: "Mentor with no queries" | Auto | `test_zero_queries_displays_zeros` — seeds Bob with 0 queries, asserts "0 Pending / 0 Assigned / 0 Resolved" |
| B7 | Pending badge is orange/amber colored | `mentor-dashboard-status` § "Status indicators use distinct colors" | Auto + Eye | `test_status_badge_css_classes_present` asserts `.badge.pending` with `#f97316`; visually confirm orange tone |
| B8 | Assigned badge is blue colored | Same § | Auto + Eye | Test asserts `.badge.assigned` with `#3b82f6`; visually confirm blue tone |
| B9 | Resolved badge is green colored | Same § | Auto + Eye | Test asserts `.badge.resolved` with `#22c55e`; visually confirm green tone |
| B10 | Badges are visible in page source (server-rendered, not JS-dependent) | `mentor-dashboard-status` § "Mentor dashboard stats are server-rendered" — Scenario: "Stats visible without JavaScript" | Auto + Eye | `test_status_badge_css_classes_present` checks response.text directly (no JS execution); view-source:`/mentors-dashboard` contains badge HTML |
| B11 | Badge text uses `Space Mono` monospace font | — | Eye | Inspect any badge in DevTools → font-family includes "Space Mono" |
| B12 | Workload bar (current_load / max_load) still renders correctly | — | Eye | Confirm the WORKLOAD stat-row and progress bar still appear above the badges |
| B13 | JS polling still works — ticket list loads after page, ACCEPT/RESOLVE buttons functional | — | Eye | Wait 5 seconds; confirm "Syncing..." is replaced with actual query items |
| B14 | Toggle online/offline still works — card greys out, status dot changes | — | Eye | Click "GO OFFLINE"; confirm card gets `.unavailable` class, dot turns red |
| B15 | Filter buttons (ALL / ACTIVE / INACTIVE) still filter cards correctly | — | Eye | Click "INACTIVE"; confirm only offline cards are shown |
| B16 | Dark/light mode toggle still works on badges | — | Eye | Toggle theme; confirm badges are readable in both modes |

---

## Summary

| Page | Auto checks (pytest) | Eye checks (browser) |
|---|---|---|
| `/admin` | 4 tests: open count (with exclusion), resolved count, workload | Label text, monospace font, responsive layout, section ordering, theme toggle |
| `/mentors-dashboard` | 3 tests: per-mentor counts, zero-queries, CSS classes + server-render | Badge position, color distinction, JS polling intact, filter/toggle intact, theme toggle |

**Total: 7 automated assertions + 16 visual observations = 23 evidence points**

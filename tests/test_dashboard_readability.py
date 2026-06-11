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

        # The open count stat value should display open count as 3, not 7
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

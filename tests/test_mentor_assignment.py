import pytest
from unittest.mock import Mock

from tests.conftest import create_mentor, create_team, create_query


class TestAcceptQuery:
    """accept_query state machine — MA1 to MA9."""

    @pytest.fixture(autouse=True)
    def setup(self, db, client, monkeypatch):
        self.db = db
        self.client = client
        self.mock_email = Mock(return_value=True)
        monkeypatch.setattr(
            "overclocked_helpdesk.api.queries.send_email_alert",
            self.mock_email,
        )

    def test_successful_acceptance(self):
        """MA1: PENDING -> ASSIGNED, load +1."""
        mentor = create_mentor(self.db, name="M1", max_load=3, current_load=0)
        create_team(self.db, id=5, name="T5", mentor_id=mentor.id)
        query = create_query(self.db, team_id=5, status="PENDING", mentor_id=None)
        resp = self.client.patch(f"/queries/{query.id}/accept/{mentor.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["query_id"] == query.id
        assert data["mentor_id"] == mentor.id
        assert data["current_load"] == 1
        self.db.refresh(query)
        assert query.status == "ASSIGNED"
        assert query.mentor_id == mentor.id
        self.db.refresh(mentor)
        assert mentor.current_load == 1
        assert mentor.is_active is True

    def test_mentor_deactivates_when_reaching_max_load(self):
        """MA2: load = max_load -> is_active=False."""
        mentor = create_mentor(self.db, name="M1", max_load=2, current_load=1)
        create_team(self.db, id=5, name="T5", mentor_id=mentor.id)
        query = create_query(self.db, team_id=5, status="PENDING", mentor_id=None)
        resp = self.client.patch(f"/queries/{query.id}/accept/{mentor.id}")
        assert resp.status_code == 200
        self.db.refresh(mentor)
        assert mentor.current_load == 2
        assert mentor.is_active is False

    def test_mentor_stays_active_below_max_load(self):
        """MA3: load < max_load -> is_active stays True."""
        mentor = create_mentor(self.db, name="M1", max_load=5, current_load=2)
        create_team(self.db, id=5, name="T5", mentor_id=mentor.id)
        query = create_query(self.db, team_id=5, status="PENDING", mentor_id=None)
        resp = self.client.patch(f"/queries/{query.id}/accept/{mentor.id}")
        assert resp.status_code == 200
        self.db.refresh(mentor)
        assert mentor.current_load == 3
        assert mentor.is_active is True

    def test_reject_already_assigned_query(self):
        """MA4: query has mentor -> 400 'already taken'."""
        mentor = create_mentor(self.db, name="M1")
        other = create_mentor(self.db, name="M2", email="m2@t.com")
        create_team(self.db, id=5, name="T5", mentor_id=mentor.id)
        query = create_query(self.db, team_id=5, status="ASSIGNED", mentor_id=other.id)
        resp = self.client.patch(f"/queries/{query.id}/accept/{mentor.id}")
        assert resp.status_code == 400
        assert "already taken" in resp.json()["detail"].lower()
        self.db.refresh(query)
        assert query.status == "ASSIGNED"
        assert query.mentor_id == other.id
        self.db.refresh(mentor)
        assert mentor.current_load == 0

    def test_reject_inactive_mentor(self):
        """MA5: mentor inactive -> 400 'not available'."""
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
        """MA6: non-existent query -> 404."""
        mentor = create_mentor(self.db, name="M1")
        resp = self.client.patch(f"/queries/9999/accept/{mentor.id}")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_mentor_not_found_during_accept(self):
        """MA7: non-existent mentor -> 404."""
        create_team(self.db, id=5, name="T5", mentor_id=1)
        query = create_query(self.db, team_id=5, status="PENDING", mentor_id=None)
        resp = self.client.patch(f"/queries/{query.id}/accept/9999")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_email_sent_on_accept(self):
        """MA8: email mock called once."""
        mentor = create_mentor(self.db, name="M1", email="m1@test.com")
        create_team(self.db, id=5, name="T5", mentor_id=mentor.id)
        query = create_query(self.db, team_id=5, status="PENDING", mentor_id=None)
        resp = self.client.patch(f"/queries/{query.id}/accept/{mentor.id}")
        assert resp.status_code == 200
        self.mock_email.assert_called_once()

    def test_email_failure_does_not_rollback_assignment(self):
        """MA9: email fails but query stays ASSIGNED."""
        self.mock_email.return_value = False
        mentor = create_mentor(self.db, name="M1", email="m1@test.com")
        create_team(self.db, id=5, name="T5", mentor_id=mentor.id)
        query = create_query(self.db, team_id=5, status="PENDING", mentor_id=None)
        resp = self.client.patch(f"/queries/{query.id}/accept/{mentor.id}")
        assert resp.status_code == 200
        self.mock_email.assert_called_once()
        self.db.refresh(query)
        assert query.status == "ASSIGNED"
        assert query.mentor_id == mentor.id
        self.db.refresh(mentor)
        assert mentor.current_load == 1


class TestResolveQuery:
    """resolve_query state machine — MR1 to MR6."""

    @pytest.fixture(autouse=True)
    def setup(self, db, client):
        self.db = db
        self.client = client

    def test_successful_resolve_with_mentor(self):
        """MR1: ASSIGNED -> RESOLVED, load -1."""
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
        """MR2: overloaded mentor resolve -> is_active=True."""
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
        """MR3: PENDING no mentor -> RESOLVED, mentor untouched."""
        create_mentor(self.db, id=1, name="M1")
        create_team(self.db, id=5, name="T5", mentor_id=1)
        query = create_query(self.db, team_id=5, status="PENDING", mentor_id=None)
        resp = self.client.patch(f"/queries/{query.id}/resolve")
        assert resp.status_code == 200
        self.db.refresh(query)
        assert query.status == "RESOLVED"
        assert query.mentor_id is None

    def test_idempotent_resolve_of_already_resolved_query(self):
        """MR4: already RESOLVED -> {ok:true}, load unchanged."""
        mentor = create_mentor(self.db, name="M1", current_load=1)
        create_team(self.db, id=5, name="T5", mentor_id=mentor.id)
        query = create_query(self.db, team_id=5, status="RESOLVED", mentor_id=mentor.id)
        resp = self.client.patch(f"/queries/{query.id}/resolve")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True
        self.db.refresh(mentor)
        assert mentor.current_load == 1

    def test_current_load_never_goes_negative(self):
        """MR5: load=1 -> resolve -> load=0, never negative."""
        mentor = create_mentor(self.db, name="M1", current_load=1)
        create_team(self.db, id=5, name="T5", mentor_id=mentor.id)
        query = create_query(self.db, team_id=5, status="ASSIGNED", mentor_id=mentor.id)
        resp = self.client.patch(f"/queries/{query.id}/resolve")
        assert resp.status_code == 200
        self.db.refresh(mentor)
        assert mentor.current_load == 0
        assert mentor.is_active is True

    def test_query_not_found_during_resolve(self):
        """MR6: non-existent query -> 404."""
        resp = self.client.patch("/queries/9999/resolve")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

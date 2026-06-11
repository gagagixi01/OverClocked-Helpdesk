import pytest
from unittest.mock import Mock

from tests.conftest import create_mentor, create_team, create_query


class TestAcceptQuery:
    """accept_query 状态机全分支 — MA1 到 MA9。"""

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
        """MA1: 正常接受 — PENDING → ASSIGNED, load +1。"""
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

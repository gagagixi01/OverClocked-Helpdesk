import pytest
from unittest.mock import Mock
from sqlalchemy.orm import Session

from overclocked_helpdesk.models.query import Query
from overclocked_helpdesk.services.notifier import notify_and_create_query
from tests.conftest import create_team


class TestQueryCreation:
    """notify_and_create_query() 的最小成功路径和 Slack 分离行为。"""

    @pytest.fixture(autouse=True)
    def setup(self, db, monkeypatch):
        self.db = db
        # Mock Slack — 默认返回 True（成功）
        self.mock_slack = Mock(return_value=True)
        monkeypatch.setattr(
            "overclocked_helpdesk.services.notifier.send_slack_alert",
            self.mock_slack,
        )

    def test_creates_query_with_pending_status_and_no_mentor(self):
        """QC1: 成功路径 — status=PENDING, mentor_id=None, Slack 被调用。"""
        create_team(self.db, id=5, name="Team5", location="Room 5")

        query = notify_and_create_query(
            db=self.db,
            team_id=5,
            issue="WiFi down",
            location="Room 5",
        )

        assert query.id is not None
        assert query.status == "PENDING"
        assert query.mentor_id is None
        assert query.team_id == 5
        assert query.issue == "WiFi down"
        assert query.location == "Room 5"
        assert query.created_at is not None
        self.mock_slack.assert_called_once()

    def test_query_created_even_when_slack_unavailable(self):
        """QC2: Slack 不可用时 Query 仍成功创建。"""
        self.mock_slack.return_value = False
        create_team(self.db, id=5, name="Team5", location="Room 5")

        query = notify_and_create_query(
            db=self.db,
            team_id=5,
            issue="WiFi down",
            location="Room 5",
        )

        assert query.id is not None
        assert query.status == "PENDING"
        self.mock_slack.assert_called_once()
        # Slack 失败不影响持久化
        db_query = self.db.query(Query).filter(Query.id == query.id).first()
        assert db_query is not None
        assert db_query.status == "PENDING"

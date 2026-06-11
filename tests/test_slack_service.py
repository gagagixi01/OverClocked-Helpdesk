from unittest.mock import Mock

from overclocked_helpdesk.config import settings
from overclocked_helpdesk.services.slack_service import send_slack_alert


class TestSendSlackAlert:
    """send_slack_alert() 配置边界单元测试"""

    def test_returns_false_when_webhook_url_is_none(self, monkeypatch):
        """SLACK_WEBHOOK_URL=None 时不调用 requests.post，返回 False。"""
        monkeypatch.setattr(settings, "SLACK_WEBHOOK_URL", None)
        mock_post = Mock()
        monkeypatch.setattr(
            "overclocked_helpdesk.services.slack_service.requests.post",
            mock_post,
        )

        result = send_slack_alert("Team A", "Room 1", "No WiFi")

        assert result is False
        mock_post.assert_not_called()

    def test_returns_false_when_webhook_url_is_empty_string(self, monkeypatch):
        """SLACK_WEBHOOK_URL="" 时不调用 requests.post，返回 False。"""
        monkeypatch.setattr(settings, "SLACK_WEBHOOK_URL", "")
        mock_post = Mock()
        monkeypatch.setattr(
            "overclocked_helpdesk.services.slack_service.requests.post",
            mock_post,
        )

        result = send_slack_alert("Team B", "Room 2", "Printer broken")

        assert result is False
        mock_post.assert_not_called()

    def test_calls_requests_post_with_correct_payload_when_url_present(
        self, monkeypatch
    ):
        """SLACK_WEBHOOK_URL 有效时正常调用 requests.post，payload 形状不变。"""
        monkeypatch.setattr(
            settings, "SLACK_WEBHOOK_URL", "https://hooks.slack.com/test"
        )
        mock_post = Mock()
        mock_post.return_value.status_code = 200
        monkeypatch.setattr(
            "overclocked_helpdesk.services.slack_service.requests.post",
            mock_post,
        )

        result = send_slack_alert("Team C", "Room 3", "Monitor broken")

        assert result is True
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        # URL 正确传递
        assert call_args[0][0] == "https://hooks.slack.com/test"
        # payload 形状不变 — text 字段包含三个参数值
        json_payload = call_args[1]["json"]
        assert "Team C" in json_payload["text"]
        assert "Room 3" in json_payload["text"]
        assert "Monitor broken" in json_payload["text"]
        assert call_args[1]["timeout"] == 10

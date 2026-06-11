from unittest.mock import Mock

from overclocked_helpdesk.config import settings
from overclocked_helpdesk.utils.qr import generate_team_qr


class TestGenerateTeamQrBaseUrl:
    """generate_team_qr()  use configurable APP_BASE_URL"""

    def test_default_base_url_generates_localhost_url(self, monkeypatch):
        """default APP_BASE_URL: QR point to http://127.0.0.1:8000/team-status?team=<id>"""
        captured_urls = []

        def capture_add_data(self, url):
            captured_urls.append(url)

        monkeypatch.setattr(
            "overclocked_helpdesk.utils.qr.qrcode.QRCode.add_data",
            capture_add_data,
        )

        # also patch save to avoid actual file writes
        monkeypatch.setattr(
            "overclocked_helpdesk.utils.qr.qrcode.QRCode.make_image",
            Mock(return_value=Mock()),
        )
        monkeypatch.setattr(
            "PIL.Image.Image.save", Mock()
        )

        generate_team_qr(1)

        assert len(captured_urls) == 1
        assert captured_urls[0] == "http://127.0.0.1:8000/team-status?team=1"

    def test_custom_base_url_propagates_to_qr(self, monkeypatch):
        """custom APP_BASE_URL: QR point to correct domain"""
        monkeypatch.setattr(
            settings,
            "APP_BASE_URL",
            "https://helpdesk.example.com",
        )
        captured_urls = []

        def capture_add_data(self, url):
            captured_urls.append(url)

        monkeypatch.setattr(
            "overclocked_helpdesk.utils.qr.qrcode.QRCode.add_data",
            capture_add_data,
        )
        monkeypatch.setattr(
            "overclocked_helpdesk.utils.qr.qrcode.QRCode.make_image",
            Mock(return_value=Mock()),
        )
        monkeypatch.setattr(
            "PIL.Image.Image.save", Mock()
        )

        generate_team_qr(2)

        assert len(captured_urls) == 1
        assert captured_urls[0] == "https://helpdesk.example.com/team-status?team=2"

    def test_trailing_slash_in_base_url_does_not_double(self, monkeypatch):
        """APP_BASE_URL with trailing slash: no //team-status"""
        monkeypatch.setattr(
            settings,
            "APP_BASE_URL",
            "https://helpdesk.example.com/",
        )
        captured_urls = []

        def capture_add_data(self, url):
            captured_urls.append(url)

        monkeypatch.setattr(
            "overclocked_helpdesk.utils.qr.qrcode.QRCode.add_data",
            capture_add_data,
        )
        monkeypatch.setattr(
            "overclocked_helpdesk.utils.qr.qrcode.QRCode.make_image",
            Mock(return_value=Mock()),
        )
        monkeypatch.setattr(
            "PIL.Image.Image.save", Mock()
        )

        generate_team_qr(3)

        assert len(captured_urls) == 1
        assert captured_urls[0] == "https://helpdesk.example.com/team-status?team=3"
        assert "//team-status" not in captured_urls[0]

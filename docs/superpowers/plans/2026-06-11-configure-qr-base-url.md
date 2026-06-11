# Configure QR Base URL Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make QR code target URL use a configurable `APP_BASE_URL` setting instead of hardcoded `http://127.0.0.1:8000`.

**Architecture:** Add `APP_BASE_URL` field to the existing `Settings` class in `config.py` (default `http://127.0.0.1:8000`). Update `generate_team_qr()` in `qr.py` to read from settings and normalize trailing slashes with `rstrip("/")`. Signature stays `(team_id: int) -> str`. No new files, no new dependencies.

**Tech Stack:** Python 3.13, pytest, unittest.mock, qrcode (already installed)

**Base ref:** `f60597a96fba902707293e270cc6857d39d76cc5`

---

### Task 1: Write all three failing tests for configurable QR base URL

**Files:**
- Create: `tests/test_qr_config.py`

**Note:** All three tests written and run BEFORE touching `config.py` or `qr.py` — verify the tests correctly catch the hardcoded URL. Tests use `unittest.mock.Mock` + `monkeypatch.setattr` (matching existing project pattern in conftest.py and test_slack_service.py), NOT `pytest-mock`. The key trick: patch `qrcode.QRCode.add_data` to capture the URL string argument, then assert on the captured value — no PNG decoding needed.

- [ ] **Step 1: Create `tests/test_qr_config.py` with all three tests**

```python
from unittest.mock import Mock

from overclocked_helpdesk.config import settings
from overclocked_helpdesk.utils.qr import generate_team_qr


class TestGenerateTeamQrBaseUrl:
    """generate_team_qr() 使用可配置 APP_BASE_URL 的测试"""

    def test_default_base_url_generates_localhost_url(self, monkeypatch):
        """默认 APP_BASE_URL 时 QR 指向 http://127.0.0.1:8000/team-status?team=<id>"""
        captured_urls = []
        orig_add_data = generate_team_qr.__wrapped__ if hasattr(
            generate_team_qr, "__wrapped__"
        ) else None

        def capture_add_data(self, url):
            captured_urls.append(url)

        monkeypatch.setattr(
            "overclocked_helpdesk.utils.qr.qrcode.QRCode.add_data",
            capture_add_data,
        )

        # 也 patch save 以避免实际写文件
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
        """自定义 APP_BASE_URL 时 QR 指向对应域名"""
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
        """末尾带 / 的 APP_BASE_URL 不会生成 //team-status"""
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
```

- [ ] **Step 2: Run new tests — all three MUST FAIL**

```bash
python -m pytest tests/test_qr_config.py -v
```

Expected output:
- `test_default_base_url_generates_localhost_url` — **PASS** (current hardcoded URL happens to match the default)
- `test_custom_base_url_propagates_to_qr` — **FAIL** (current code hardcodes `127.0.0.1:8000` regardless of settings; `APP_BASE_URL` attribute doesn't exist on settings yet → `AttributeError`, OR if monkeypatch setattr succeeds, the URL stays `127.0.0.1:8000` instead of the custom domain)
- `test_trailing_slash_in_base_url_does_not_double` — **FAIL** (same reason)

**IMPORTANT**: If `test_default_base_url_generates_localhost_url` fails because `Settings` has no `APP_BASE_URL` attribute yet, that's OK — the `test_custom_base_url_propagates_to_qr` failure catches the main gap. If the default test somehow passes while the custom test fails, that's still a valid TDD red state. If all three pass unexpectedly, the tests are not correct — stop and investigate.

- [ ] **Step 3: Commit failing tests**

```bash
git add tests/test_qr_config.py
git commit -m "test: add failing QR base URL configuration tests

Three tests for generate_team_qr() — default localhost, custom domain,
and trailing slash normalization. Custom and trailing-slash tests FAIL
because APP_BASE_URL is not yet configurable.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 2: Add APP_BASE_URL to Settings and update generate_team_qr

**Files:**
- Modify: `overclocked_helpdesk/config.py:4-16` (add APP_BASE_URL field)
- Modify: `overclocked_helpdesk/utils/qr.py:9-25` (use settings + rstrip)

- [ ] **Step 1: Add `APP_BASE_URL` to `Settings` class**

Edit `overclocked_helpdesk/config.py` — add the `APP_BASE_URL` field after the Email section (before `model_config`):

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "sqlite:///./helpdesk.db"

    # App
    APP_BASE_URL: str = "http://127.0.0.1:8000"

    # Slack
    SLACK_BOT_TOKEN: str | None = None
    SLACK_WEBHOOK_URL: str | None = None

    # Email
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 465
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )


settings = Settings()
```

The only change is adding lines 8-9.

- [ ] **Step 2: Update `generate_team_qr()` to use settings**

Edit `overclocked_helpdesk/utils/qr.py` — import settings and use `APP_BASE_URL` with `rstrip("/")`:

```python
import qrcode
from pathlib import Path

from overclocked_helpdesk.config import settings


QR_DIR = Path("static/qr")
QR_DIR.mkdir(parents=True, exist_ok=True)


def generate_team_qr(team_id: int) -> str:
    """
    Generates a QR code for a team.
    QR opens the team status page.
    Returns relative file path.
    """

    base = settings.APP_BASE_URL.rstrip("/")
    url = f"{base}/team-status?team={team_id}"
    file_path = QR_DIR / f"team_{team_id}.png"

    qr = qrcode.QRCode(
        version=1,
        box_size=10,
        border=4
    )
    qr.add_data(url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    img.save(file_path)

    return str(file_path)
```

Changes: added line 4 (`from overclocked_helpdesk.config import settings`), replaced `url = f"http://127.0.0.1:8000/team-status?team={team_id}"` with lines 18-19 (`base = ...` + `url = ...`).

- [ ] **Step 3: Run new tests — all three MUST PASS**

```bash
python -m pytest tests/test_qr_config.py -v
```

Expected: 3 passed

- [ ] **Step 4: Commit the fix**

```bash
git add overclocked_helpdesk/config.py overclocked_helpdesk/utils/qr.py
git commit -m "feat: make QR code base URL configurable via APP_BASE_URL

Add APP_BASE_URL to Settings (default http://127.0.0.1:8000) and update
generate_team_qr() to use it with trailing slash normalization.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 3: Regression check — existing tests must pass, admin page unchanged

**Files:**
- Verify: `tests/test_query_creation.py` (no changes)
- Verify: `tests/test_mentor_assignment.py` (no changes)
- Verify: `tests/test_slack_service.py` (no changes)
- Verify: `tests/test_dashboard_readability.py` (no changes)

- [ ] **Step 1: Run full test suite**

```bash
python -m pytest tests/ -v
```

Expected: all existing tests pass. The new `test_qr_config.py` tests also pass. No regressions.

- [ ] **Step 2: Verify admin QR generation still works with default config**

```bash
python -c "
from overclocked_helpdesk.config import settings
from overclocked_helpdesk.utils.qr import generate_team_qr
import os

# 确认默认值
assert settings.APP_BASE_URL == 'http://127.0.0.1:8000'

# 生成 QR 并确认路径正确
path = generate_team_qr(42)
assert path == 'static/qr/team_42.png'
assert os.path.exists(path)
print(f'OK: QR generated at {path}')
"
```

Expected: `OK: QR generated at static/qr/team_42.png`

- [ ] **Step 3: Clean up generated test QR file**

```bash
rm -f static/qr/team_42.png
```

- [ ] **Step 4: Commit verified state**

```bash
git add -A
git commit -m "chore: regression verification — all tests pass, QR generation works

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 4: Final verification and cleanup

- [ ] **Step 1: Verify clean git status**

```bash
git status
```

No untracked files beyond what was committed. No unstaged changes.

- [ ] **Step 2: Verify all commits are on the right base**

```bash
git log --oneline f60597a..HEAD
```

Shows 3 commits: failing tests → implementation → regression verification.

- [ ] **Step 3: Confirm `APP_BASE_URL` is not in `.env` (zero-config backward compat)**

```bash
grep -c "APP_BASE_URL" .env 2>/dev/null || echo "APP_BASE_URL not in .env (good — using default)"
```

Expected: `APP_BASE_URL not in .env` or count 0. The default in `Settings` provides the value; no `.env` changes needed.

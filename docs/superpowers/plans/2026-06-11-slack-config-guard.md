# Slack Config Guard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an early-return guard to `send_slack_alert()` so it returns `False` without calling `requests.post` when `SLACK_WEBHOOK_URL` is `None` or empty string.

**Architecture:** One-line guard at the top of `send_slack_alert()` in `slack_service.py`. Three unit tests in a new `tests/test_slack_service.py` validate the guard behavior directly, independent of the notifier layer. Existing `test_query_creation.py` tests remain unchanged (they monkeypatch at the notifier level, bypassing slack_service internals). Mock strategy follows the existing project pattern: `unittest.mock.Mock` + `monkeypatch.setattr`, not `pytest-mock`.

**Tech Stack:** Python 3.13, pytest, unittest.mock, requests (mocked)

**Base ref:** `561b83285eb464e966745ac99173874abba45903`

---

### Task 1: Write all three failing tests for slack_service

**Files:**
- Create: `tests/test_slack_service.py`

**Note:** All three tests written and run BEFORE touching `slack_service.py` — verify tests catch the bug. Tests use `unittest.mock.Mock` + `monkeypatch.setattr` (matching conftest.py pattern), NOT `pytest-mock`.

- [ ] **Step 1: Create `tests/test_slack_service.py` with all three tests**

```python
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
```

- [ ] **Step 2: Run new tests — all three MUST FAIL**

```bash
python -m pytest tests/test_slack_service.py -v
```

Expected output:
- `test_returns_false_when_webhook_url_is_none` — **FAIL** (guard not yet added, `requests.post(None, ...)` raises `MissingSchema` or similar)
- `test_returns_false_when_webhook_url_is_empty_string` — **FAIL** (same reason)
- `test_calls_requests_post_with_correct_payload_when_url_present` — **PASS** (no guard needed for this path, but the mock returns `Mock.status_code` which is not `200`)

If any of the first two tests PASS unexpectedly, the tests are not correctly catching the bug — stop and investigate.

- [ ] **Step 3: Commit failing tests**

```bash
git add tests/test_slack_service.py
git commit -m "test: add failing slack_service config guard tests

Three tests for send_slack_alert() — None URL, empty URL, and valid URL
paths. First two FAIL because guard is not yet implemented.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 2: Add the guard to send_slack_alert

**Files:**
- Modify: `overclocked_helpdesk/services/slack_service.py:5` (insert after function signature, before payload construction)

- [ ] **Step 1: Add the early-return guard**

Edit `overclocked_helpdesk/services/slack_service.py` — insert `if not settings.SLACK_WEBHOOK_URL: return False` between the function signature and the payload construction:

```python
import requests
from overclocked_helpdesk.config import settings


def send_slack_alert(team_name: str, location: str, issue: str) -> bool:
    if not settings.SLACK_WEBHOOK_URL:
        return False

    payload = {
        "text": (
            "*New Helpdesk Query*\n"
            f"*Team:* {team_name}\n"
            f"*Location:* {location}\n"
            f"*Issue:* {issue}"
        )
    }

    response = requests.post(
        settings.SLACK_WEBHOOK_URL,
        json=payload,
        timeout=10
    )

    return response.status_code == 200
```

The only change is lines 6-7 (the `if not` guard + blank line). Everything else stays identical.

- [ ] **Step 2: Run new tests — all three MUST PASS**

```bash
python -m pytest tests/test_slack_service.py -v
```

Expected: 3 passed

- [ ] **Step 3: Commit the fix**

```bash
git add overclocked_helpdesk/services/slack_service.py
git commit -m "fix: guard send_slack_alert against missing SLACK_WEBHOOK_URL

Add early-return guard that returns False without calling requests.post
when SLACK_WEBHOOK_URL is None or empty string.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 3: Regression check — existing tests must pass

**Files:**
- Verify: `tests/test_query_creation.py` (no changes)
- Verify: `tests/test_mentor_assignment.py` (no changes)

- [ ] **Step 1: Run existing query creation tests**

```bash
python -m pytest tests/test_query_creation.py -v
```

Expected: 3 passed (QC1, QC2, QC3). These tests monkeypatch `notifier.send_slack_alert`, completely bypassing `slack_service.py`, so the guard has zero effect on them.

- [ ] **Step 2: Run full test suite**

```bash
python -m pytest tests/ -v
```

Expected: all tests pass (3 slack_service + 3 query_creation + all mentor_assignment tests).

---

### Task 4: Commit and verify clean state

- [ ] **Step 1: Verify clean git status**

```bash
git status
```

No untracked files beyond what was committed. No unstaged changes.

- [ ] **Step 2: Verify all commits are on the right base**

```bash
git log --oneline 561b832..HEAD
```

Shows 2 commits: the failing tests commit and the fix commit.

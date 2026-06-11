## 1. Guard implementation

- [ ] 1.1 Add `if not settings.SLACK_WEBHOOK_URL: return False` at the top of `send_slack_alert()` in `slack_service.py`

## 2. Unit tests for slack_service

- [ ] 2.1 Create `tests/test_slack_service.py` with `TestSendSlackAlert` class
- [ ] 2.2 Test: `SLACK_WEBHOOK_URL` is `None` → returns `False`, does not call `requests.post`
- [ ] 2.3 Test: `SLACK_WEBHOOK_URL` is `""` → returns `False`, does not call `requests.post`
- [ ] 2.4 Test: `SLACK_WEBHOOK_URL` is a valid URL → calls `requests.post` once with correct payload structure

## 3. Regression check

- [ ] 3.1 Run existing `tests/test_query_creation.py` — all 3 tests (QC1, QC2, QC3) must pass

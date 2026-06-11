## 1. Configuration

- [ ] 1.1 Add `APP_BASE_URL` field to `Settings` class in `overclocked_helpdesk/config.py` with default `http://127.0.0.1:8000`

## 2. QR Code Generation

- [ ] 2.1 Update `generate_team_qr()` in `overclocked_helpdesk/utils/qr.py` to import settings and use `APP_BASE_URL` with trailing slash normalization

## 3. Tests

- [ ] 3.1 Add test: default `APP_BASE_URL` generates `http://127.0.0.1:8000/team-status?team=<id>`
- [ ] 3.2 Add test: custom `APP_BASE_URL` propagates to QR content
- [ ] 3.3 Add test: trailing slash in `APP_BASE_URL` does not produce double slashes
- [ ] 3.4 Run full test suite to confirm no regressions

## 4. Verification

- [ ] 4.1 Manual check: admin QR generation button still works with default config
- [ ] 4.2 Manual check: generated QR image scans to correct URL in default config

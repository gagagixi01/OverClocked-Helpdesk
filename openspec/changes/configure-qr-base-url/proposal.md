## Why

The QR code target URL is hardcoded to `http://127.0.0.1:8000/team-status?team=<id>`, which works for local development but generates incorrect QR codes when the app is deployed to a real domain. Making the base URL configurable lets operators set the correct public-facing URL without code changes.

## What Changes

- Add `APP_BASE_URL` to `Settings` with a default of `http://127.0.0.1:8000`
- Update `generate_team_qr()` to read `APP_BASE_URL` from settings instead of using a hardcoded string
- Normalize trailing slashes so both `http://example.com` and `http://example.com/` produce clean `http://example.com/team-status?team=<id>`

## Capabilities

### New Capabilities
- `configurable-qr-base-url`: QR codes use a configurable base URL from application settings, allowing deployment to any domain without code changes

### Modified Capabilities
<!-- None - no existing specs are changing -->

## Impact

- **Affected files**: `overclocked_helpdesk/config.py`, `overclocked_helpdesk/utils/qr.py`
- **Dependencies**: `pydantic-settings` (already in use)
- **Backward compatibility**: Default value preserves existing localhost behavior; no downstream callers need changes

## Context

The current `generate_team_qr()` in `overclocked_helpdesk/utils/qr.py` constructs a QR code URL by hardcoding `http://127.0.0.1:8000` as the base. The `Settings` class in `config.py` has no base URL field. This is a small, single-module change with no new dependencies.

## Goals / Non-Goals

**Goals:**
- Add `APP_BASE_URL` to `Settings` with a default that preserves current behavior
- Make `generate_team_qr()` read the base URL from settings
- Handle trailing slashes in `APP_BASE_URL` safely (no double slashes)

**Non-Goals:**
- Changing the QR UI, team status page, or admin panel
- Adding deployment system integration
- Supporting query string parameters in `APP_BASE_URL`
- Changing the QR image storage path or format

## Decisions

**Decision 1: Use `pydantic-settings` field with a default rather than environment-only**

`APP_BASE_URL` goes into the existing `Settings` class alongside other config fields. Default value `http://127.0.0.1:8000` ensures zero-config backward compatibility. Users override via `.env` or environment variable.

**Decision 2: Normalize in `generate_team_qr()` with `rstrip("/")`**

Strip trailing slashes from `APP_BASE_URL` before appending `/team-status?...`. Simple, no URL parsing library needed. Alternative considered: using `urllib.parse.urljoin` — but it handles path joining differently and introduces unnecessary complexity for a simple concatenation.

**Decision 3: Keep `generate_team_qr(team_id)` signature unchanged**

The function already takes only `team_id`. Reading settings internally keeps callers clean. No other callers need updating.

## Risks / Trade-offs

- **Risk**: Someone sets `APP_BASE_URL` to a malformed URL (e.g., `not-a-url`) → **Mitigation**: This is user misconfiguration; no URL validation is added (out of scope per non-goals). The QR will simply contain the bad URL, which is visible when scanned.
- **Risk**: Settings import in `qr.py` creates a config dependency that wasn't there before → **Mitigation**: `qr.py` is already a project-internal module; this is a minor and acceptable coupling.

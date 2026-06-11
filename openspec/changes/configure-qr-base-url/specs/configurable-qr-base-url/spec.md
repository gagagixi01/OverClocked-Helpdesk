## ADDED Requirements

### Requirement: QR code uses configurable base URL
The system SHALL use the `APP_BASE_URL` setting as the base URL when generating QR codes, with a default value of `http://127.0.0.1:8000`.

#### Scenario: Default base URL generates localhost QR
- **WHEN** `APP_BASE_URL` is not explicitly set
- **THEN** `generate_team_qr(1)` SHALL produce a QR code pointing to `http://127.0.0.1:8000/team-status?team=1`

#### Scenario: Custom base URL generates correct QR
- **WHEN** `APP_BASE_URL` is set to `https://helpdesk.example.com`
- **THEN** `generate_team_qr(2)` SHALL produce a QR code pointing to `https://helpdesk.example.com/team-status?team=2`

### Requirement: Trailing slash in base URL does not produce double slashes
The system SHALL strip trailing slashes from `APP_BASE_URL` before constructing the team-status path.

#### Scenario: Base URL with trailing slash
- **WHEN** `APP_BASE_URL` is set to `https://helpdesk.example.com/`
- **THEN** `generate_team_qr(3)` SHALL produce a QR code pointing to `https://helpdesk.example.com/team-status?team=3`
- **AND** the generated URL SHALL NOT contain `//team-status`

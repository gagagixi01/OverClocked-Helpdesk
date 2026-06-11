## ADDED Requirements

### Requirement: send_slack_alert returns False when webhook URL is missing
The system SHALL return `False` from `send_slack_alert()` without calling `requests.post` when `SLACK_WEBHOOK_URL` is `None` or an empty string.

#### Scenario: Webhook URL is None
- **WHEN** `SLACK_WEBHOOK_URL` is `None` and `send_slack_alert(team_name, location, issue)` is called
- **THEN** the function returns `False` and does NOT call `requests.post`

#### Scenario: Webhook URL is empty string
- **WHEN** `SLACK_WEBHOOK_URL` is `""` and `send_slack_alert(team_name, location, issue)` is called
- **THEN** the function returns `False` and does NOT call `requests.post`

### Requirement: send_slack_alert preserves existing payload when webhook URL exists
The system SHALL call `requests.post` with the same payload structure as before when `SLACK_WEBHOOK_URL` is a non-empty string.

#### Scenario: Webhook URL present
- **WHEN** `SLACK_WEBHOOK_URL` is a valid URL string and `send_slack_alert("Team A", "Room 1", "No WiFi")` is called
- **THEN** `requests.post` is called exactly once with the URL, a JSON payload containing `team_name`, `location`, and `issue` fields, and a timeout of 10 seconds

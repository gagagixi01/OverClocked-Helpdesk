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

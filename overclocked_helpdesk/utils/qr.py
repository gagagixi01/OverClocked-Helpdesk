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

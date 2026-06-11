from fastapi import APIRouter, Request, HTTPException, Form, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import Session
import os

from overclocked_helpdesk.db.session import get_db
from overclocked_helpdesk.models.mentor import Mentor
from overclocked_helpdesk.models.query import Query
from overclocked_helpdesk.utils.qr import generate_team_qr

router = APIRouter(prefix="/admin", tags=["Admin"])
templates = Jinja2Templates(directory="templates")

QR_DIR = "static/qr"


# -------------------------
# Helpers
# -------------------------
def qr_exists(team_id: int) -> bool:
    return os.path.exists(f"{QR_DIR}/team_{team_id}.png")


# -------------------------
# Admin Dashboard
# -------------------------
@router.get("", response_class=HTMLResponse)
def admin_dashboard(
    request: Request,
    db: Session = Depends(get_db)
):
    teams = [
        {"id": i, "qr_exists": qr_exists(i)}
        for i in range(1, 41)
    ]

    mentors = db.query(Mentor).order_by(Mentor.id.asc()).all()

    # --- Dashboard stats ---
    open_count = db.query(func.count(Query.id)).filter(
        Query.status.in_(["PENDING", "ASSIGNED"])
    ).scalar()

    resolved_count = db.query(func.count(Query.id)).filter(
        Query.status == "RESOLVED"
    ).scalar()

    active_mentor_count = sum(1 for m in mentors if m.is_active)
    total_load = sum(m.current_load for m in mentors)

    return templates.TemplateResponse(
        "admin_dashboard.html",
        {
            "request": request,
            "teams": teams,
            "mentors": mentors,
            "open_count": open_count,
            "resolved_count": resolved_count,
            "active_mentor_count": active_mentor_count,
            "total_load": total_load,
        }
    )


# -------------------------
# Generate QR
# -------------------------
@router.post("/teams/{team_id}/generate-qr")
def generate_qr(team_id: int):
    if team_id < 1 or team_id > 40:
        raise HTTPException(status_code=400, detail="Invalid team")

    path = generate_team_qr(team_id)
    return {"ok": True, "path": path}


# -------------------------
# Add Mentor
# -------------------------
@router.post("/mentors")
def add_mentor(
    name: str = Form(...),
    email: str = Form(...),
    max_load: int = Form(3),
    db: Session = Depends(get_db)
):
    mentor = Mentor(
        name=name.strip(),
        email=email.strip(),
        max_load=max_load,
        current_load=0,
        is_active=True
    )

    db.add(mentor)
    db.commit()
    db.refresh(mentor)

    return {"ok": True, "id": mentor.id}


# -------------------------
# Update Mentor
# -------------------------
@router.patch("/mentors/{mentor_id}")
def update_mentor(
    mentor_id: int,
    name: str = Form(...),
    email: str = Form(...),
    max_load: int = Form(...),
    is_active: bool = Form(...),
    db: Session = Depends(get_db)
):
    mentor = db.query(Mentor).filter(Mentor.id == mentor_id).first()

    if not mentor:
        raise HTTPException(status_code=404, detail="Mentor not found")

    mentor.name = name.strip()
    mentor.email = email.strip()
    mentor.max_load = max_load
    mentor.is_active = is_active

    # safety clamp
    if mentor.current_load > mentor.max_load:
        mentor.current_load = mentor.max_load

    db.commit()
    return {"ok": True}


# -------------------------
# Delete Mentor
# -------------------------
@router.delete("/mentors/{mentor_id}")
def delete_mentor(
    mentor_id: int,
    db: Session = Depends(get_db)
):
    mentor = db.query(Mentor).filter(Mentor.id == mentor_id).first()

    if not mentor:
        raise HTTPException(status_code=404, detail="Mentor not found")

    if mentor.current_load > 0:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete mentor with active workload"
        )

    db.delete(mentor)
    db.commit()

    return {"ok": True}

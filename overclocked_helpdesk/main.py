from fastapi import FastAPI, Request, Form, BackgroundTasks, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from overclocked_helpdesk.db.session import SessionLocal, engine, Base, get_db
from overclocked_helpdesk.services.notifier import notify_and_create_query

# ROUTERS
from overclocked_helpdesk.api.queries import router as queries_router
from overclocked_helpdesk.api.qr import router as qr_router
from overclocked_helpdesk.api.admin import router as admin_router

# MODELS
from collections import defaultdict
from overclocked_helpdesk.models.mentor import Mentor
from overclocked_helpdesk.models.query import Query
from overclocked_helpdesk.models.team import Team


app = FastAPI(title="OverClocked Helpdesk")
app.include_router(qr_router)
app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(admin_router)

# ✅ REGISTER ROUTERS
app.include_router(queries_router)

# Create DB tables
Base.metadata.create_all(bind=engine)

templates = Jinja2Templates(directory="templates")


# ------------------------
# Background notifier
# ------------------------

def background_notify(team_id: int, issue: str, location: str):
    db = SessionLocal()
    try:
        notify_and_create_query(
            db=db,
            team_id=team_id,
            issue=issue,
            location=location
        )
    finally:
        db.close()


# ------------------------
# Helpdesk UI
# ------------------------

@app.get("/", response_class=HTMLResponse)
def show_helpdesk_form(request: Request):
    return templates.TemplateResponse(
        "helpdesk_form.html",
        {"request": request}
    )


@app.post("/submit")
def submit_helpdesk_form(
    background_tasks: BackgroundTasks,
    team_id: int = Form(...),
    issue: str = Form(...),
    location: str = Form(...)
):
    print("SUBMIT HIT", team_id, issue, location)

    background_tasks.add_task(
        background_notify,
        team_id,
        issue,
        location
    )

    return JSONResponse({
        "ok": True,
        "team_id": team_id
    })



# ------------------------
# Team Status (HTML)
# ------------------------

@app.get("/team-status", response_class=HTMLResponse)
def team_status_page(
    request: Request,
    team: int
):
    return templates.TemplateResponse(
        "team_status.html",
        {
            "request": request,
            "team_id": team
        }
    )


# ------------------------
# Team Status (API)
# ------------------------

@app.get("/team/{team_id}/status")
def team_status_api(
    team_id: int,
    db: Session = Depends(get_db)
):
    latest_query = (
        db.query(Query)
        .filter(Query.team_id == team_id)
        .order_by(desc(Query.created_at))
        .first()
    )

    if not latest_query:
        return JSONResponse(
            {"detail": "No active query"},
            status_code=404
        )

    mentor = (
        db.query(Mentor)
        .filter(Mentor.id == latest_query.mentor_id)
        .first()
    )

    return {
        "issue": latest_query.issue,
        "status": latest_query.status,
        "mentor": mentor.name if mentor else None,
        "updated_at": latest_query.created_at.strftime("%Y-%m-%d %H:%M:%S")
    }


# ------------------------
# Mentor Dashboard (HTML)
# ------------------------

@app.get("/mentors-dashboard", response_class=HTMLResponse)
def mentors_dashboard(
    request: Request,
    db: Session = Depends(get_db)
):
    mentors = db.query(Mentor).all()

    # Per-mentor query status counts
    rows = db.query(
        Query.mentor_id, Query.status, func.count(Query.id)
    ).filter(
        Query.mentor_id.isnot(None)
    ).group_by(Query.mentor_id, Query.status).all()

    query_counts = defaultdict(lambda: {"PENDING": 0, "ASSIGNED": 0, "RESOLVED": 0})
    for mentor_id, status, count in rows:
        if status in ("PENDING", "ASSIGNED", "RESOLVED"):
            query_counts[mentor_id][status] = count

    return templates.TemplateResponse(
        "mentor_dashboard.html",
        {
            "request": request,
            "mentors": mentors,
            "query_counts": query_counts,
        }
    )


# ------------------------
# Mentor State (API)
# ------------------------

@app.get("/mentors/state")
def mentors_state(db: Session = Depends(get_db)):
    mentors = db.query(Mentor).all()
    return [
        {
            "id": m.id,
            "name": m.name,
            "is_active": m.is_active,
            "current_load": m.current_load,
            "max_load": m.max_load,
        }
        for m in mentors
    ]


# ------------------------
# Toggle Mentor Availability
# ------------------------

@app.patch("/mentors/{mentor_id}/toggle-availability")
def toggle_mentor_availability(
    mentor_id: int,
    db: Session = Depends(get_db)
):
    mentor = db.query(Mentor).filter(Mentor.id == mentor_id).first()

    if not mentor:
        raise HTTPException(status_code=404, detail="Mentor not found")

    mentor.is_active = not mentor.is_active
    db.commit()
    db.refresh(mentor)

    return {
        "id": mentor.id,
        "name": mentor.name,
        "is_active": mentor.is_active,
        "current_load": mentor.current_load,
        "max_load": mentor.max_load,
    }

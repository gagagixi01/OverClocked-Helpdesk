import tempfile
import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from overclocked_helpdesk.db.session import Base

# Import all models so SQLAlchemy registers them on Base.metadata
import overclocked_helpdesk.models.mentor  # noqa: F401
import overclocked_helpdesk.models.team    # noqa: F401
import overclocked_helpdesk.models.query   # noqa: F401


@pytest.fixture(autouse=True)
def engine():
    """每个测试函数独立创建临时文件数据库，建表，测试后销毁。
    使用临时文件（非 :memory:）确保 TestClient worker 线程可以访问同一数据库。"""
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    _engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=_engine)
    yield _engine
    Base.metadata.drop_all(bind=_engine)
    _engine.dispose()
    os.unlink(db_path)


@pytest.fixture
def db(engine):
    """每个测试函数独立 session。测试后 rollback + close。"""
    session = Session(bind=engine)
    yield session
    session.rollback()
    session.close()


from overclocked_helpdesk.models.mentor import Mentor
from overclocked_helpdesk.models.team import Team
from overclocked_helpdesk.models.query import Query


def create_mentor(db, **kwargs):
    defaults = {
        "name": "Mentor_Default",
        "email": "mentor@test.com",
        "max_load": 3,
        "current_load": 0,
        "is_active": True,
    }
    defaults.update(kwargs)
    obj = Mentor(**defaults)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def create_team(db, **kwargs):
    defaults = {"name": "Team_Default", "location": "Room 1", "mentor_id": 1}
    defaults.update(kwargs)
    obj = Team(**defaults)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def create_query(db, **kwargs):
    defaults = {
        "team_id": 1,
        "mentor_id": None,
        "issue": "Test issue",
        "location": "Test location",
        "status": "PENDING",
    }
    defaults.update(kwargs)
    obj = Query(**defaults)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


from fastapi.testclient import TestClient
from overclocked_helpdesk.main import app
from overclocked_helpdesk.db.session import get_db


@pytest.fixture
def client(db):
    """TestClient with get_db overridden to use test :memory: session."""
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as _client:
        yield _client
    app.dependency_overrides.clear()

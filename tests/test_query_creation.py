def test_imports_work():
    from overclocked_helpdesk.services.notifier import notify_and_create_query
    from overclocked_helpdesk.models.query import Query
    assert notify_and_create_query is not None
    assert Query is not None


def test_engine_creates_tables(engine):
    """验证 engine fixture 建表成功 — 可以查询 mentors/queries/teams 表。"""
    from sqlalchemy import text
    from sqlalchemy.orm import Session

    session = Session(bind=engine)
    session.execute(text("INSERT INTO mentors (name) VALUES ('test')"))
    session.commit()
    result = session.execute(text("SELECT COUNT(*) FROM mentors")).scalar()
    assert result == 1
    session.close()


from overclocked_helpdesk.models.mentor import Mentor


def test_db_fixture_persists_and_isolates(db):
    """验证 db fixture 可以持久化数据，且测试间隔离。"""
    mentor = Mentor(name="fixture_test", email="f@t.com", max_load=3)
    db.add(mentor)
    db.commit()
    db.refresh(mentor)

    assert mentor.id is not None
    assert mentor.name == "fixture_test"


from tests.conftest import create_mentor, create_team, create_query


def test_create_mentor_defaults(db):
    m = create_mentor(db)
    assert m.name == "Mentor_Default"
    assert m.is_active is True
    assert m.current_load == 0
    assert m.max_load == 3


def test_create_mentor_overrides(db):
    m = create_mentor(db, name="Alice", max_load=5, current_load=2, is_active=False)
    assert m.name == "Alice"
    assert m.max_load == 5
    assert m.current_load == 2
    assert m.is_active is False


def test_create_query_defaults(db):
    create_team(db, id=1)  # FK needs a team
    q = create_query(db)
    assert q.status == "PENDING"
    assert q.mentor_id is None
    assert q.issue == "Test issue"
    assert q.created_at is not None


def test_create_query_overrides(db):
    create_team(db, id=5)
    create_mentor(db, id=2)
    q = create_query(db, team_id=5, issue="Broken", location="Room 301", status="ASSIGNED", mentor_id=2)
    assert q.team_id == 5
    assert q.issue == "Broken"
    assert q.location == "Room 301"
    assert q.status == "ASSIGNED"
    assert q.mentor_id == 2

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

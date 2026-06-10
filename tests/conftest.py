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
    """每个测试函数独立创建 :memory: engine，建表，测试后销毁。"""
    _engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=_engine)
    yield _engine
    Base.metadata.drop_all(bind=_engine)
    _engine.dispose()


@pytest.fixture
def db(engine):
    """每个测试函数独立 session。测试后 rollback + close。"""
    session = Session(bind=engine)
    yield session
    session.rollback()
    session.close()

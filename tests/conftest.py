import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from testcontainers.postgres import PostgresContainer

from app import db as db_module
from app.models import Base


@pytest.fixture(scope="session")
def pg_container():
    """Один контейнер PostgreSQL на всю сессию pytest."""
    with PostgresContainer("postgres:16-alpine", driver="psycopg") as pg:
        yield pg


@pytest.fixture(scope="session")
def engine(pg_container):
    eng = create_engine(pg_container.get_connection_url(), future=True)
    Base.metadata.create_all(eng)
    try:
        yield eng
    finally:
        eng.dispose()


@pytest.fixture(scope="session")
def session_factory(engine):
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@pytest.fixture(autouse=True)
def _patch_session_local(session_factory, monkeypatch):
    """Подменяем `app.db.SessionLocal` тестовой фабрикой.

    `enricher` и `seed` импортируют модуль `db` целиком, поэтому
    одного monkeypatch хватает.
    """
    monkeypatch.setattr(db_module, "SessionLocal", session_factory)


@pytest.fixture(autouse=True)
def _clean_items(engine):
    """Чистим таблицу после каждого теста, чтобы они не зависели друг от друга."""
    yield
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE items RESTART IDENTITY CASCADE"))


@pytest.fixture
def session(session_factory) -> Session:
    s = session_factory()
    try:
        yield s
    finally:
        s.close()

"""Test app with a separate, fresh in-memory database for every test."""

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import get_db
from app.main import app
from app.models import Base


@pytest.fixture
def test_engine() -> Iterator[Engine]:
    """An in-memory SQLite database with all tables, discarded after the test."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture
def test_session_factory(test_engine: Engine) -> sessionmaker[Session]:
    """Creates sessions bound to the test database."""
    return sessionmaker(bind=test_engine, autoflush=False, expire_on_commit=False)


@pytest.fixture
def client(test_session_factory: sessionmaker[Session]) -> Iterator[TestClient]:
    """A test client whose requests use the test database, never the real one."""

    def get_test_db() -> Iterator[Session]:
        with test_session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = get_test_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def db_session(test_session_factory: sessionmaker[Session]) -> Iterator[Session]:
    """A session for checking directly what is stored in the test database."""
    with test_session_factory() as session:
        yield session


@pytest.fixture
def valid_payload() -> dict[str, Any]:
    """A correct request body for logging a symptom."""
    return {
        "symptom": "Headache",
        "notes": "Started in the morning, worse after lunch, eased after rest.",
        "date": "2026-11-02",
        "severity": 3,
    }

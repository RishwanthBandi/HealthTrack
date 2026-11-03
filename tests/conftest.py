"""Test app with a separate, fresh in-memory database for every test."""

from collections.abc import Iterator

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
def client(test_engine: Engine) -> Iterator[TestClient]:
    """A test client whose requests use the test database, never the real one."""
    TestSession = sessionmaker(bind=test_engine, autoflush=False, expire_on_commit=False)

    def get_test_db() -> Iterator[Session]:
        with TestSession() as session:
            yield session

    app.dependency_overrides[get_db] = get_test_db
    yield TestClient(app)
    app.dependency_overrides.clear()

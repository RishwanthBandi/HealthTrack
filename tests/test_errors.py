"""Tests for error handling (FR-05) and basic app startup."""

import logging
from collections.abc import Callable, Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

from app.db import get_db
from app.main import app
from app.models import Symptom

DATABASE_ERROR_BODY = {
    "error": {
        "code": "database_error",
        "message": "The service could not reach the database. Please try again later.",
    }
}
INTERNAL_ERROR_BODY = {
    "error": {
        "code": "internal_error",
        "message": "Something went wrong on our side. Please try again later.",
    }
}
ENDPOINTS = [
    ("POST", "/patients/1/symptoms"),
    ("GET", "/patients/1/symptoms"),
    ("GET", "/patients/1/insights"),
]
VALID_BODY = {"symptom": "Headache", "date": "2026-11-02", "severity": 3}


def database_failure(statement: str) -> OperationalError:
    """The kind of error SQLAlchemy raises when the database cannot be used."""
    return OperationalError(statement, {}, Exception("unable to open database file"))


@pytest.fixture
def client_with_database() -> Iterator[Callable[..., TestClient]]:
    """Build a test client whose database dependency is replaced by the given function."""

    def build(get_test_db: Callable[[], Any], raise_server_exceptions: bool = True) -> TestClient:
        app.dependency_overrides[get_db] = get_test_db
        return TestClient(app, raise_server_exceptions=raise_server_exceptions)

    yield build
    app.dependency_overrides.clear()


def get_unreachable_db() -> Session:
    """Database dependency that fails as if the database were unavailable."""
    raise database_failure("SELECT symptoms.id FROM symptoms WHERE symptoms.patient_id = ?")


def test_app_starts_and_serves_api_docs(client: TestClient) -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert response.json()["info"]["title"] == "HealthTrack API"


@pytest.mark.parametrize(("method", "url"), ENDPOINTS)
def test_fr05_database_error_returns_500_with_standard_error_format(
    client_with_database: Callable[..., TestClient], method: str, url: str
) -> None:
    client = client_with_database(get_unreachable_db)

    response = client.request(method, url, json=VALID_BODY if method == "POST" else None)

    assert response.status_code == 500
    assert response.json() == DATABASE_ERROR_BODY


def test_fr05_database_error_does_not_reveal_sql_or_internal_details(
    client_with_database: Callable[..., TestClient],
) -> None:
    client = client_with_database(get_unreachable_db)

    response = client.get("/patients/1/symptoms")

    for internal_detail in ["SELECT", "symptoms.patient_id", "unable to open", "Traceback"]:
        assert internal_detail not in response.text


def test_fr05_database_error_is_logged_on_the_server(
    client_with_database: Callable[..., TestClient], caplog: pytest.LogCaptureFixture
) -> None:
    client = client_with_database(get_unreachable_db)

    with caplog.at_level(logging.ERROR, logger="app.errors"):
        client.get("/patients/1/symptoms")

    [record] = [record for record in caplog.records if record.name == "app.errors"]
    assert "GET /patients/1/symptoms" in record.getMessage()
    assert record.exc_info is not None
    assert isinstance(record.exc_info[1], OperationalError)


def test_fr05_failed_save_leaves_no_half_saved_data(
    client_with_database: Callable[..., TestClient],
    test_session_factory: sessionmaker[Session],
    db_session: Session,
) -> None:
    def get_db_that_fails_on_commit() -> Iterator[Session]:
        with test_session_factory() as session:

            def send_insert_then_fail() -> None:
                session.flush()
                raise database_failure("COMMIT")

            session.commit = send_insert_then_fail  # type: ignore[method-assign]
            yield session

    client = client_with_database(get_db_that_fails_on_commit)

    response = client.post("/patients/1/symptoms", json=VALID_BODY)

    assert response.status_code == 500
    assert db_session.scalar(select(func.count()).select_from(Symptom)) == 0


def test_fr05_unexpected_error_returns_500_internal_error_without_details(
    client_with_database: Callable[..., TestClient], caplog: pytest.LogCaptureFixture
) -> None:
    def get_db_with_a_bug() -> Session:
        raise RuntimeError("secret internal detail")

    client = client_with_database(get_db_with_a_bug, raise_server_exceptions=False)

    with caplog.at_level(logging.ERROR, logger="app.errors"):
        response = client.get("/patients/1/symptoms")

    assert response.status_code == 500
    assert response.json() == INTERNAL_ERROR_BODY
    assert "secret internal detail" not in response.text
    assert any(
        record.name == "app.errors" and isinstance(record.exc_info[1], RuntimeError)
        for record in caplog.records
        if record.exc_info
    )


@pytest.mark.parametrize("url", ["/unknown", "/patients/1/unknown", "/patients"])
def test_fr05_unknown_url_returns_404_not_found(client: TestClient, url: str) -> None:
    response = client.get(url)

    assert response.status_code == 404
    assert response.json() == {
        "error": {"code": "not_found", "message": "The requested URL was not found."}
    }


@pytest.mark.parametrize(
    ("method", "url"), [("DELETE", "/patients/1/symptoms"), ("PUT", "/patients/1/insights")]
)
def test_fr05_wrong_http_method_returns_405_method_not_allowed(
    client: TestClient, method: str, url: str
) -> None:
    response = client.request(method, url)

    assert response.status_code == 405
    assert response.json() == {
        "error": {
            "code": "method_not_allowed",
            "message": "This HTTP method is not allowed for this URL.",
        }
    }


def test_fr05_malformed_json_body_returns_422_validation_error(client: TestClient) -> None:
    response = client.post(
        "/patients/1/symptoms",
        content='{"symptom": "Headache", "severity": 3',
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert response.json()["error"]["details"] == [
        {"field": "body", "message": "the request body is not valid JSON"}
    ]


@pytest.mark.parametrize(("method", "url"), ENDPOINTS)
def test_fr05_every_endpoint_documents_the_500_database_error(
    client: TestClient, method: str, url: str
) -> None:
    path = url.replace("/1/", "/{patient_id}/")
    operation = client.get("/openapi.json").json()["paths"][path][method.lower()]

    error_500 = operation["responses"]["500"]
    assert error_500["content"]["application/json"]["example"] == DATABASE_ERROR_BODY

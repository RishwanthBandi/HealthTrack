"""Tests for input validation (FR-03)."""

from typing import Any

import pytest
from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Symptom


def error_details(response: Response) -> list[dict[str, str]]:
    """The list of field problems from a standard validation error response."""
    return response.json()["error"]["details"]


def test_fr03_validation_error_uses_standard_error_format(
    client: TestClient, valid_payload: dict[str, Any]
) -> None:
    response = client.post("/patients/1/symptoms", json={**valid_payload, "severity": 0})

    assert response.status_code == 422
    assert response.json() == {
        "error": {
            "code": "validation_error",
            "message": "Invalid input.",
            "details": [{"field": "severity", "message": "severity must be between 1 and 5"}],
        }
    }


@pytest.mark.parametrize("severity", [0, 6, -1])
def test_fr03_rejects_severity_outside_1_to_5(
    client: TestClient, db_session: Session, valid_payload: dict[str, Any], severity: int
) -> None:
    response = client.post("/patients/1/symptoms", json={**valid_payload, "severity": severity})

    assert response.status_code == 422
    assert error_details(response) == [
        {"field": "severity", "message": "severity must be between 1 and 5"}
    ]
    assert db_session.scalars(select(Symptom)).all() == []


@pytest.mark.parametrize("severity", [2.5, "abc", "3", None, True])
def test_fr03_rejects_severity_that_is_not_a_whole_number(
    client: TestClient, db_session: Session, valid_payload: dict[str, Any], severity: object
) -> None:
    response = client.post("/patients/1/symptoms", json={**valid_payload, "severity": severity})

    assert response.status_code == 422
    assert error_details(response) == [
        {"field": "severity", "message": "severity must be a whole number between 1 and 5"}
    ]
    assert db_session.scalars(select(Symptom)).all() == []


def test_fr03_rejects_missing_severity(client: TestClient, valid_payload: dict[str, Any]) -> None:
    del valid_payload["severity"]

    response = client.post("/patients/1/symptoms", json=valid_payload)

    assert response.status_code == 422
    assert error_details(response) == [{"field": "severity", "message": "severity is required"}]


@pytest.mark.parametrize("severity", [1, 5])
def test_fr03_accepts_severity_boundaries_1_and_5(
    client: TestClient, valid_payload: dict[str, Any], severity: int
) -> None:
    response = client.post("/patients/1/symptoms", json={**valid_payload, "severity": severity})

    assert response.status_code == 201
    assert response.json()["severity"] == severity


@pytest.mark.parametrize("symptom", ["", "    "])
def test_fr03_rejects_empty_or_whitespace_only_symptom(
    client: TestClient, db_session: Session, valid_payload: dict[str, Any], symptom: str
) -> None:
    response = client.post("/patients/1/symptoms", json={**valid_payload, "symptom": symptom})

    assert response.status_code == 422
    assert error_details(response) == [{"field": "symptom", "message": "symptom must not be empty"}]
    assert db_session.scalars(select(Symptom)).all() == []


def test_fr03_rejects_missing_symptom(client: TestClient, valid_payload: dict[str, Any]) -> None:
    del valid_payload["symptom"]

    response = client.post("/patients/1/symptoms", json=valid_payload)

    assert response.status_code == 422
    assert error_details(response) == [{"field": "symptom", "message": "symptom is required"}]


@pytest.mark.parametrize("symptom", [None, 123])
def test_fr03_rejects_symptom_that_is_not_text(
    client: TestClient, valid_payload: dict[str, Any], symptom: object
) -> None:
    response = client.post("/patients/1/symptoms", json={**valid_payload, "symptom": symptom})

    assert response.status_code == 422
    assert error_details(response) == [{"field": "symptom", "message": "symptom must be text"}]


def test_fr03_rejects_symptom_longer_than_100_characters(
    client: TestClient, db_session: Session, valid_payload: dict[str, Any]
) -> None:
    response = client.post("/patients/1/symptoms", json={**valid_payload, "symptom": "a" * 101})

    assert response.status_code == 422
    assert error_details(response) == [
        {
            "field": "symptom",
            "message": "symptom must be at most 100 characters (use notes for details)",
        }
    ]
    assert db_session.scalars(select(Symptom)).all() == []


def test_fr03_accepts_symptom_of_exactly_100_characters(
    client: TestClient, valid_payload: dict[str, Any]
) -> None:
    response = client.post("/patients/1/symptoms", json={**valid_payload, "symptom": "a" * 100})

    assert response.status_code == 201


def test_fr03_lists_all_problems_when_several_fields_are_wrong(
    client: TestClient, db_session: Session
) -> None:
    payload = {"symptom": "   ", "date": "yesterday", "severity": 9}

    response = client.post("/patients/1/symptoms", json=payload)

    assert response.status_code == 422
    assert error_details(response) == [
        {"field": "symptom", "message": "symptom must not be empty"},
        {"field": "date", "message": "date must be a valid date in YYYY-MM-DD format"},
        {"field": "severity", "message": "severity must be between 1 and 5"},
    ]
    assert db_session.scalars(select(Symptom)).all() == []

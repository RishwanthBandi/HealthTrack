"""Tests for logging (FR-01) and retrieving (FR-02) symptoms."""

import datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Symptom


def test_fr01_logs_symptom_and_returns_201_with_saved_record(
    client: TestClient, valid_payload: dict[str, Any]
) -> None:
    response = client.post("/patients/1/symptoms", json=valid_payload)

    assert response.status_code == 201
    body = response.json()
    assert body["id"] == 1
    assert body["patient_id"] == 1
    assert body["symptom"] == "Headache"
    assert body["notes"] == valid_payload["notes"]
    assert body["date"] == "2026-11-02"
    assert body["severity"] == 3
    assert body["created_at"].endswith("Z")


def test_fr01_saves_symptom_in_database_with_correct_date_and_severity(
    client: TestClient, db_session: Session, valid_payload: dict[str, Any]
) -> None:
    client.post("/patients/7/symptoms", json=valid_payload)

    saved = db_session.scalars(select(Symptom)).one()
    assert saved.patient_id == 7
    assert saved.symptom == "Headache"
    assert saved.notes == valid_payload["notes"]
    assert saved.date == datetime.date(2026, 11, 2)
    assert saved.severity == 3
    assert saved.created_at is not None


def test_fr01_trims_symptom_and_notes_before_saving(
    client: TestClient, db_session: Session, valid_payload: dict[str, Any]
) -> None:
    payload = {**valid_payload, "symptom": "  Headache  ", "notes": "  Worse at night.  "}

    response = client.post("/patients/1/symptoms", json=payload)

    assert response.status_code == 201
    saved = db_session.scalars(select(Symptom)).one()
    assert saved.symptom == "Headache"
    assert saved.notes == "Worse at night."


@pytest.mark.parametrize("notes", ["", "   ", None])
def test_fr01_stores_empty_or_whitespace_only_notes_as_null(
    client: TestClient, db_session: Session, valid_payload: dict[str, Any], notes: str | None
) -> None:
    response = client.post("/patients/1/symptoms", json={**valid_payload, "notes": notes})

    assert response.status_code == 201
    assert response.json()["notes"] is None
    assert db_session.scalars(select(Symptom)).one().notes is None


def test_fr01_accepts_missing_notes(client: TestClient, valid_payload: dict[str, Any]) -> None:
    del valid_payload["notes"]

    response = client.post("/patients/1/symptoms", json=valid_payload)

    assert response.status_code == 201
    assert response.json()["notes"] is None


def test_fr01_accepts_notes_of_exactly_2000_characters(
    client: TestClient, valid_payload: dict[str, Any]
) -> None:
    response = client.post("/patients/1/symptoms", json={**valid_payload, "notes": "a" * 2000})

    assert response.status_code == 201


def test_fr01_rejects_notes_longer_than_2000_characters(
    client: TestClient, db_session: Session, valid_payload: dict[str, Any]
) -> None:
    response = client.post("/patients/1/symptoms", json={**valid_payload, "notes": "a" * 2001})

    assert response.status_code == 422
    assert {
        "field": "notes",
        "message": "notes must be at most 2000 characters",
    } in response.json()["error"]["details"]
    assert db_session.scalars(select(Symptom)).all() == []


def test_fr01_rejects_missing_date(client: TestClient, valid_payload: dict[str, Any]) -> None:
    del valid_payload["date"]

    response = client.post("/patients/1/symptoms", json=valid_payload)

    assert response.status_code == 422
    assert {"field": "date", "message": "date is required"} in response.json()["error"]["details"]


@pytest.mark.parametrize("date", ["2026-13-45", "yesterday", "2026/11/02", "2026-1-2", 20261102])
def test_fr01_rejects_date_that_is_not_a_real_yyyy_mm_dd_date(
    client: TestClient, valid_payload: dict[str, Any], date: object
) -> None:
    response = client.post("/patients/1/symptoms", json={**valid_payload, "date": date})

    assert response.status_code == 422
    assert {
        "field": "date",
        "message": "date must be a valid date in YYYY-MM-DD format",
    } in response.json()["error"]["details"]


def test_fr01_rejects_future_date(
    client: TestClient, db_session: Session, valid_payload: dict[str, Any]
) -> None:
    tomorrow = datetime.date.today() + datetime.timedelta(days=1)

    response = client.post(
        "/patients/1/symptoms", json={**valid_payload, "date": tomorrow.isoformat()}
    )

    assert response.status_code == 422
    assert {
        "field": "date",
        "message": "date cannot be in the future",
    } in response.json()["error"]["details"]
    assert db_session.scalars(select(Symptom)).all() == []


def test_fr01_accepts_today_as_date(client: TestClient, valid_payload: dict[str, Any]) -> None:
    today = datetime.date.today().isoformat()

    response = client.post("/patients/1/symptoms", json={**valid_payload, "date": today})

    assert response.status_code == 201
    assert response.json()["date"] == today


@pytest.mark.parametrize("patient_id", ["0", "-1", "abc", "1.5"])
def test_fr01_rejects_patient_id_that_is_not_a_positive_whole_number(
    client: TestClient, db_session: Session, valid_payload: dict[str, Any], patient_id: str
) -> None:
    response = client.post(f"/patients/{patient_id}/symptoms", json=valid_payload)

    assert response.status_code == 422
    assert {
        "field": "patient_id",
        "message": "patient_id must be a positive whole number",
    } in response.json()["error"]["details"]
    assert db_session.scalars(select(Symptom)).all() == []


def test_fr01_ignores_extra_unknown_fields(
    client: TestClient, valid_payload: dict[str, Any]
) -> None:
    response = client.post(
        "/patients/1/symptoms", json={**valid_payload, "mood": "tired", "id": 999}
    )

    assert response.status_code == 201
    assert "mood" not in response.json()
    assert response.json()["id"] == 1

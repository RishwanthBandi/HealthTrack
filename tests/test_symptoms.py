"""Tests for logging (FR-01) and retrieving (FR-02) symptoms."""

import datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient
from httpx import Response
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


def add_symptom(
    db_session: Session, patient_id: int, symptom: str, date: str, severity: int = 3
) -> None:
    """Store one symptom directly in the test database."""
    db_session.add(
        Symptom(
            patient_id=patient_id,
            symptom=symptom,
            date=datetime.date.fromisoformat(date),
            severity=severity,
        )
    )
    db_session.commit()


@pytest.fixture
def october_symptoms(db_session: Session) -> None:
    """Patient 1 has entries on 1, 5, 10 and 15 Oct; patient 2 has one on 5 Oct."""
    add_symptom(db_session, 1, "Headache", "2026-10-01")
    add_symptom(db_session, 1, "Fever", "2026-10-05")
    add_symptom(db_session, 1, "Cough", "2026-10-10")
    add_symptom(db_session, 1, "Nausea", "2026-10-15")
    add_symptom(db_session, 2, "Rash", "2026-10-05")


def listed_dates(response: Response) -> list[str]:
    """The dates of the listed symptoms, in the order the API returned them."""
    return [entry["date"] for entry in response.json()]


@pytest.mark.usefixtures("october_symptoms")
def test_fr02_returns_only_symptoms_within_date_range(client: TestClient) -> None:
    response = client.get(
        "/patients/1/symptoms", params={"start_date": "2026-10-02", "end_date": "2026-10-12"}
    )

    assert response.status_code == 200
    assert listed_dates(response) == ["2026-10-10", "2026-10-05"]


@pytest.mark.usefixtures("october_symptoms")
def test_fr02_includes_entries_on_start_date_and_end_date(client: TestClient) -> None:
    response = client.get(
        "/patients/1/symptoms", params={"start_date": "2026-10-05", "end_date": "2026-10-10"}
    )

    assert listed_dates(response) == ["2026-10-10", "2026-10-05"]


@pytest.mark.usefixtures("october_symptoms")
def test_fr02_accepts_same_start_and_end_date(client: TestClient) -> None:
    response = client.get(
        "/patients/1/symptoms", params={"start_date": "2026-10-05", "end_date": "2026-10-05"}
    )

    assert response.status_code == 200
    assert listed_dates(response) == ["2026-10-05"]


@pytest.mark.usefixtures("october_symptoms")
def test_fr02_returns_only_the_requested_patients_symptoms(client: TestClient) -> None:
    response = client.get("/patients/2/symptoms")

    assert response.status_code == 200
    assert [entry["symptom"] for entry in response.json()] == ["Rash"]
    assert all(entry["patient_id"] == 2 for entry in response.json())


def test_fr02_sorts_symptoms_newest_first(client: TestClient, db_session: Session) -> None:
    add_symptom(db_session, 1, "Fever", "2026-10-05")
    add_symptom(db_session, 1, "Headache", "2026-10-20")
    add_symptom(db_session, 1, "Cough", "2026-10-01")
    add_symptom(db_session, 1, "Nausea", "2026-10-20")

    response = client.get("/patients/1/symptoms")

    assert [(entry["date"], entry["symptom"]) for entry in response.json()] == [
        ("2026-10-20", "Nausea"),
        ("2026-10-20", "Headache"),
        ("2026-10-05", "Fever"),
        ("2026-10-01", "Cough"),
    ]


@pytest.mark.usefixtures("october_symptoms")
def test_fr02_returns_all_fields_of_each_symptom(client: TestClient) -> None:
    response = client.get("/patients/2/symptoms")

    entry = response.json()[0]
    assert set(entry) == {"id", "patient_id", "symptom", "notes", "date", "severity", "created_at"}
    assert entry["created_at"].endswith("Z")


@pytest.mark.usefixtures("october_symptoms")
def test_fr02_returns_empty_list_when_no_symptoms_in_range(client: TestClient) -> None:
    response = client.get(
        "/patients/1/symptoms", params={"start_date": "2026-09-01", "end_date": "2026-09-30"}
    )

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.usefixtures("october_symptoms")
def test_fr02_returns_empty_list_for_patient_who_never_logged(client: TestClient) -> None:
    response = client.get("/patients/99/symptoms")

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.usefixtures("october_symptoms")
def test_fr02_only_start_date_returns_everything_from_that_date(client: TestClient) -> None:
    response = client.get("/patients/1/symptoms", params={"start_date": "2026-10-10"})

    assert listed_dates(response) == ["2026-10-15", "2026-10-10"]


@pytest.mark.usefixtures("october_symptoms")
def test_fr02_only_end_date_returns_everything_up_to_that_date(client: TestClient) -> None:
    response = client.get("/patients/1/symptoms", params={"end_date": "2026-10-05"})

    assert listed_dates(response) == ["2026-10-05", "2026-10-01"]


@pytest.mark.usefixtures("october_symptoms")
def test_fr02_no_dates_returns_all_of_the_patients_symptoms(client: TestClient) -> None:
    response = client.get("/patients/1/symptoms")

    assert listed_dates(response) == ["2026-10-15", "2026-10-10", "2026-10-05", "2026-10-01"]


def test_fr02_rejects_start_date_after_end_date(client: TestClient) -> None:
    response = client.get(
        "/patients/1/symptoms", params={"start_date": "2026-10-10", "end_date": "2026-10-01"}
    )

    assert response.status_code == 422
    assert response.json()["error"]["details"] == [
        {"field": "end_date", "message": "start_date must be on or before end_date"}
    ]


@pytest.mark.parametrize("field", ["start_date", "end_date"])
@pytest.mark.parametrize("value", ["2026-13-45", "yesterday", "2026/10/01", "2026-1-2", ""])
def test_fr02_rejects_invalid_date_format(client: TestClient, field: str, value: str) -> None:
    response = client.get("/patients/1/symptoms", params={field: value})

    assert response.status_code == 422
    assert response.json()["error"]["details"] == [
        {"field": field, "message": f"{field} must be a valid date in YYYY-MM-DD format"}
    ]


@pytest.mark.parametrize("patient_id", ["0", "-1", "abc"])
def test_fr02_rejects_patient_id_that_is_not_a_positive_whole_number(
    client: TestClient, patient_id: str
) -> None:
    response = client.get(f"/patients/{patient_id}/symptoms")

    assert response.status_code == 422
    assert response.json()["error"]["details"] == [
        {"field": "patient_id", "message": "patient_id must be a positive whole number"}
    ]

"""Tests for insights (FR-04)."""

import pytest
from fastapi.testclient import TestClient

from tests.conftest import AddSymptom


@pytest.fixture
def week_of_symptoms(add_symptom: AddSymptom) -> None:
    """Patient 1: Headache x3 and Fever x2 from 1 to 7 Nov, plus entries outside that week.

    Patient 2 has a Rash on 3 Nov that must never appear in patient 1's insights.
    """
    add_symptom(1, "Headache", "2026-11-01", severity=4)
    add_symptom(1, "Fever", "2026-11-02", severity=3)
    add_symptom(1, "Headache", "2026-11-03", severity=2)
    add_symptom(1, "Fever", "2026-11-05", severity=5)
    add_symptom(1, "Headache", "2026-11-07", severity=3)
    add_symptom(1, "Cough", "2026-10-31", severity=1)
    add_symptom(1, "Cough", "2026-11-08", severity=1)
    add_symptom(2, "Rash", "2026-11-03", severity=5)


@pytest.mark.usefixtures("week_of_symptoms")
def test_fr04_returns_most_frequent_symptom_and_overall_average_severity(
    client: TestClient,
) -> None:
    response = client.get(
        "/patients/1/insights", params={"start_date": "2026-11-01", "end_date": "2026-11-07"}
    )

    assert response.status_code == 200
    assert response.json() == {
        "patient_id": 1,
        "start_date": "2026-11-01",
        "end_date": "2026-11-07",
        "total_entries": 5,
        "most_frequent_symptoms": [{"symptom": "headache", "count": 3, "average_severity": 3.0}],
        "overall_average_severity": 3.4,
    }


@pytest.mark.usefixtures("week_of_symptoms")
def test_fr04_includes_entries_on_start_date_and_end_date(client: TestClient) -> None:
    response = client.get(
        "/patients/1/insights", params={"start_date": "2026-10-31", "end_date": "2026-11-08"}
    )

    body = response.json()
    assert body["total_entries"] == 7
    assert body["most_frequent_symptoms"] == [
        {"symptom": "headache", "count": 3, "average_severity": 3.0}
    ]


@pytest.mark.usefixtures("week_of_symptoms")
def test_fr04_only_uses_the_requested_patients_entries(client: TestClient) -> None:
    response = client.get("/patients/2/insights")

    body = response.json()
    assert body["total_entries"] == 1
    assert body["most_frequent_symptoms"] == [
        {"symptom": "rash", "count": 1, "average_severity": 5.0}
    ]
    assert body["overall_average_severity"] == 5


def test_fr04_returns_all_tied_symptoms(client: TestClient, add_symptom: AddSymptom) -> None:
    add_symptom(1, "Headache", "2026-11-01", severity=4)
    add_symptom(1, "Fever", "2026-11-02", severity=2)
    add_symptom(1, "Headache", "2026-11-03", severity=2)
    add_symptom(1, "Fever", "2026-11-04", severity=1)
    add_symptom(1, "Cough", "2026-11-05", severity=5)

    response = client.get("/patients/1/insights")

    assert response.json()["most_frequent_symptoms"] == [
        {"symptom": "fever", "count": 2, "average_severity": 1.5},
        {"symptom": "headache", "count": 2, "average_severity": 3.0},
    ]


def test_fr04_gives_each_frequent_symptom_its_own_average_and_keeps_overall_average(
    client: TestClient, add_symptom: AddSymptom
) -> None:
    add_symptom(1, "Headache", "2026-11-01", severity=4)
    add_symptom(1, "Fever", "2026-11-02", severity=2)
    add_symptom(1, "Headache", "2026-11-03", severity=2)
    add_symptom(1, "Fever", "2026-11-04", severity=1)
    add_symptom(1, "Cough", "2026-11-05", severity=5)

    body = client.get("/patients/1/insights").json()

    averages = {
        item["symptom"]: item["average_severity"] for item in body["most_frequent_symptoms"]
    }
    assert averages == {"fever": 1.5, "headache": 3.0}
    assert body["overall_average_severity"] == 2.8


def test_fr04_rounds_each_symptoms_average_severity_to_2_decimals_half_up(
    client: TestClient, add_symptom: AddSymptom
) -> None:
    for day, severity in enumerate([1, 1, 2], start=1):
        add_symptom(1, "Headache", f"2026-11-0{day}", severity=severity)
    for day, severity in enumerate([3, 3, 2], start=4):
        add_symptom(1, "Fever", f"2026-11-0{day}", severity=severity)

    body = client.get("/patients/1/insights").json()

    assert body["most_frequent_symptoms"] == [
        {"symptom": "fever", "count": 3, "average_severity": 2.67},
        {"symptom": "headache", "count": 3, "average_severity": 1.33},
    ]
    assert body["overall_average_severity"] == 2.0


def test_fr04_counts_different_capitalisation_and_spaces_as_same_symptom(
    client: TestClient, add_symptom: AddSymptom
) -> None:
    add_symptom(1, "Headache", "2026-11-01", severity=1)
    add_symptom(1, "headache", "2026-11-02", severity=2)
    add_symptom(1, " HEADACHE ", "2026-11-03", severity=4)
    add_symptom(1, "Fever", "2026-11-04")
    add_symptom(1, "Fever", "2026-11-05")

    response = client.get("/patients/1/insights")

    assert response.json()["most_frequent_symptoms"] == [
        {"symptom": "headache", "count": 3, "average_severity": 2.33}
    ]


def test_fr04_counts_frequency_on_symptom_field_not_notes(
    client: TestClient, add_symptom: AddSymptom
) -> None:
    add_symptom(1, "Fever", "2026-11-01", notes="headache too")
    add_symptom(1, "Fever", "2026-11-02", notes="headache, headache")
    add_symptom(1, "Headache", "2026-11-03")

    response = client.get("/patients/1/insights")

    assert response.json()["most_frequent_symptoms"] == [
        {"symptom": "fever", "count": 2, "average_severity": 3.0}
    ]


def test_fr04_rounds_overall_average_severity_to_2_decimals(
    client: TestClient, add_symptom: AddSymptom
) -> None:
    add_symptom(1, "Headache", "2026-11-01", severity=1)
    add_symptom(1, "Headache", "2026-11-02", severity=2)
    add_symptom(1, "Headache", "2026-11-03", severity=2)

    response = client.get("/patients/1/insights")

    assert response.json()["overall_average_severity"] == 1.67


def test_fr04_rounds_overall_average_severity_half_up(
    client: TestClient, add_symptom: AddSymptom
) -> None:
    for day, severity in enumerate([2, 2, 2, 2, 2, 2, 2, 3], start=1):
        add_symptom(1, "Headache", f"2026-11-0{day}", severity=severity)

    response = client.get("/patients/1/insights")

    assert response.json()["overall_average_severity"] == 2.13


@pytest.mark.usefixtures("week_of_symptoms")
def test_fr04_returns_empty_insights_when_no_entries_in_period(client: TestClient) -> None:
    response = client.get(
        "/patients/1/insights", params={"start_date": "2026-09-01", "end_date": "2026-09-30"}
    )

    assert response.status_code == 200
    assert response.json() == {
        "patient_id": 1,
        "start_date": "2026-09-01",
        "end_date": "2026-09-30",
        "total_entries": 0,
        "most_frequent_symptoms": [],
        "overall_average_severity": None,
    }


@pytest.mark.usefixtures("week_of_symptoms")
def test_fr04_returns_empty_insights_for_patient_who_never_logged(client: TestClient) -> None:
    response = client.get("/patients/99/insights")

    assert response.status_code == 200
    body = response.json()
    assert body["total_entries"] == 0
    assert body["most_frequent_symptoms"] == []
    assert body["overall_average_severity"] is None


def test_fr04_single_entry_is_most_frequent_and_its_severity_is_the_average(
    client: TestClient, add_symptom: AddSymptom
) -> None:
    add_symptom(1, "Nausea", "2026-11-01", severity=4)

    response = client.get("/patients/1/insights")

    body = response.json()
    assert body["total_entries"] == 1
    assert body["most_frequent_symptoms"] == [
        {"symptom": "nausea", "count": 1, "average_severity": 4.0}
    ]
    assert body["overall_average_severity"] == 4


@pytest.mark.usefixtures("week_of_symptoms")
def test_fr04_only_start_date_uses_everything_from_that_date(client: TestClient) -> None:
    response = client.get("/patients/1/insights", params={"start_date": "2026-11-05"})

    body = response.json()
    assert body["start_date"] == "2026-11-05"
    assert body["end_date"] is None
    assert body["total_entries"] == 3


@pytest.mark.usefixtures("week_of_symptoms")
def test_fr04_only_end_date_uses_everything_up_to_that_date(client: TestClient) -> None:
    response = client.get("/patients/1/insights", params={"end_date": "2026-11-01"})

    body = response.json()
    assert body["start_date"] is None
    assert body["end_date"] == "2026-11-01"
    assert body["total_entries"] == 2


@pytest.mark.usefixtures("week_of_symptoms")
def test_fr04_no_dates_uses_all_of_the_patients_entries(client: TestClient) -> None:
    response = client.get("/patients/1/insights")

    body = response.json()
    assert body["start_date"] is None
    assert body["end_date"] is None
    assert body["total_entries"] == 7


def test_fr04_rejects_start_date_after_end_date(client: TestClient) -> None:
    response = client.get(
        "/patients/1/insights", params={"start_date": "2026-11-07", "end_date": "2026-11-01"}
    )

    assert response.status_code == 422
    assert response.json()["error"]["details"] == [
        {"field": "end_date", "message": "start_date must be on or before end_date"}
    ]


@pytest.mark.parametrize("field", ["start_date", "end_date"])
@pytest.mark.parametrize("value", ["2026-13-45", "yesterday", ""])
def test_fr04_rejects_invalid_date_format(client: TestClient, field: str, value: str) -> None:
    response = client.get("/patients/1/insights", params={field: value})

    assert response.status_code == 422
    assert response.json()["error"]["details"] == [
        {"field": field, "message": f"{field} must be a valid date in YYYY-MM-DD format"}
    ]


@pytest.mark.parametrize(
    ("patient_id", "message"),
    [
        ("0", "patient_id must be a positive whole number"),
        ("abc", "patient_id must be a positive whole number"),
        ("2147483648", "patient_id must be at most 2147483647"),
    ],
)
def test_fr04_rejects_invalid_patient_id(client: TestClient, patient_id: str, message: str) -> None:
    response = client.get(f"/patients/{patient_id}/insights")

    assert response.status_code == 422
    assert response.json()["error"]["details"] == [{"field": "patient_id", "message": message}]

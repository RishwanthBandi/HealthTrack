"""Tests for error handling (FR-05) and basic app startup."""

from fastapi.testclient import TestClient


def test_app_starts_and_serves_api_docs(client: TestClient) -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert response.json()["info"]["title"] == "HealthTrack API"

"""All HTTP calls to the HealthTrack API, with friendly error messages."""

import datetime
import os
from typing import Any
from urllib.parse import quote

import requests

API_BASE_URL = os.environ.get("HEALTHTRACK_API_URL", "http://localhost:8000")
REQUEST_TIMEOUT_SECONDS = 10
CANNOT_REACH_API_MESSAGE = "Cannot reach the HealthTrack API. Is it running?"


class ApiError(Exception):
    """A request failed; holds a message and field problems ready to show the user."""

    def __init__(self, message: str, details: list[str] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or []


def log_symptom(
    patient_id: str, symptom: str, notes: str, date: datetime.date, severity: int
) -> dict[str, Any]:
    """Log a symptom and return the saved entry, or raise ApiError.

    Values are sent exactly as entered; the API does all the validation.
    """
    if not patient_id.strip():
        raise ApiError("Invalid input.", ["patient_id is required"])
    payload = {
        "symptom": symptom,
        "notes": notes,
        "date": date.isoformat(),
        "severity": severity,
    }
    try:
        response = requests.post(
            f"{API_BASE_URL}/patients/{quote(patient_id, safe='')}/symptoms",
            json=payload,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except requests.RequestException as error:
        raise ApiError(CANNOT_REACH_API_MESSAGE) from error
    if not response.ok:
        raise error_from_response(response)
    return response.json()


def error_from_response(response: requests.Response) -> ApiError:
    """Turn an API error response (standard error format) into an ApiError."""
    try:
        error = response.json()["error"]
    except (ValueError, KeyError, TypeError):
        return ApiError(f"Unexpected response from the API (status {response.status_code}).")
    details = [detail["message"] for detail in error.get("details", [])]
    return ApiError(error["message"], details)

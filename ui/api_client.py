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
    payload = {
        "symptom": symptom,
        "notes": notes,
        "date": date.isoformat(),
        "severity": severity,
    }
    return send_request("POST", patient_url(patient_id, "symptoms"), json=payload)


def list_symptoms(
    patient_id: str, start_date: datetime.date | None, end_date: datetime.date | None
) -> list[dict[str, Any]]:
    """A patient's symptoms in the date range, newest first, or raise ApiError.

    Empty dates are left out of the request, meaning "no limit".
    """
    params = date_range_params(start_date, end_date)
    return send_request("GET", patient_url(patient_id, "symptoms"), params=params)


def get_insights(
    patient_id: str, start_date: datetime.date | None, end_date: datetime.date | None
) -> dict[str, Any]:
    """A patient's insights for the date range, or raise ApiError.

    Empty dates are left out of the request, meaning "no limit".
    """
    params = date_range_params(start_date, end_date)
    return send_request("GET", patient_url(patient_id, "insights"), params=params)


def date_range_params(
    start_date: datetime.date | None, end_date: datetime.date | None
) -> dict[str, str]:
    """Query parameters for the dates that were given; empty dates are left out."""
    params = {}
    if start_date is not None:
        params["start_date"] = start_date.isoformat()
    if end_date is not None:
        params["end_date"] = end_date.isoformat()
    return params


def patient_url(patient_id: str, resource: str) -> str:
    """URL of a patient's resource, with the patient ID sent exactly as entered."""
    if not patient_id.strip():
        raise ApiError("Invalid input.", ["patient_id is required"])
    return f"{API_BASE_URL}/patients/{quote(patient_id, safe='')}/{resource}"


def send_request(
    method: str,
    url: str,
    json: dict[str, Any] | None = None,
    params: dict[str, str] | None = None,
) -> Any:
    """Send one request and return the JSON response, or raise ApiError."""
    try:
        response = requests.request(
            method, url, json=json, params=params, timeout=REQUEST_TIMEOUT_SECONDS
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

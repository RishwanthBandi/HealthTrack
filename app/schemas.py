"""Pydantic request/response models. All validation rules live here."""

import datetime
import re
from typing import Annotated, Any

from fastapi import Path
from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator
from pydantic_core import PydanticCustomError

SYMPTOM_MAX_LENGTH = 100
NOTES_MAX_LENGTH = 2000
SEVERITY_MIN = 1
SEVERITY_MAX = 5
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")

PatientId = Annotated[
    int,
    Path(gt=0, description="The patient's ID: a positive whole number.", examples=[1]),
]


def parse_iso_date(field_name: str, value: Any) -> datetime.date:
    """Turn a 'YYYY-MM-DD' string into a date, or raise a clear validation error."""
    if isinstance(value, datetime.date):
        return value
    if isinstance(value, str) and DATE_PATTERN.match(value):
        try:
            return datetime.date.fromisoformat(value)
        except ValueError:
            pass
    raise PydanticCustomError(
        "date_format", f"{field_name} must be a valid date in YYYY-MM-DD format"
    )


class SymptomCreate(BaseModel):
    """Request body for logging a symptom. Unknown extra fields are ignored."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "symptom": "Headache",
                    "notes": "Started in the morning, worse after lunch, eased after rest.",
                    "date": "2026-11-02",
                    "severity": 3,
                }
            ]
        }
    )

    symptom: str = Field(
        min_length=1,
        max_length=SYMPTOM_MAX_LENGTH,
        description="Short symptom name, e.g. 'Headache'. Spaces at both ends are removed.",
    )
    notes: str | None = Field(
        default=None,
        max_length=NOTES_MAX_LENGTH,
        description="Optional details. Empty or whitespace-only notes are stored as null.",
    )
    date: datetime.date = Field(
        description="Day the symptom happened (YYYY-MM-DD), not in the future."
    )
    severity: int = Field(
        ge=SEVERITY_MIN, le=SEVERITY_MAX, description="How bad it was: whole number 1 to 5."
    )

    @field_validator("symptom", mode="before")
    @classmethod
    def clean_symptom(cls, value: Any) -> str:
        """Trim the symptom and check it is not empty and not too long."""
        if not isinstance(value, str):
            raise PydanticCustomError("symptom_type", "symptom must be text")
        trimmed = value.strip()
        if not trimmed:
            raise PydanticCustomError("symptom_empty", "symptom must not be empty")
        if len(trimmed) > SYMPTOM_MAX_LENGTH:
            raise PydanticCustomError(
                "symptom_too_long",
                f"symptom must be at most {SYMPTOM_MAX_LENGTH} characters (use notes for details)",
            )
        return trimmed

    @field_validator("notes", mode="before")
    @classmethod
    def clean_notes(cls, value: Any) -> str | None:
        """Trim the notes, turn empty notes into None and check the length."""
        if value is None:
            return None
        if not isinstance(value, str):
            raise PydanticCustomError("notes_type", "notes must be text")
        trimmed = value.strip()
        if len(trimmed) > NOTES_MAX_LENGTH:
            raise PydanticCustomError(
                "notes_too_long", f"notes must be at most {NOTES_MAX_LENGTH} characters"
            )
        return trimmed or None

    @field_validator("date", mode="before")
    @classmethod
    def check_date(cls, value: Any) -> datetime.date:
        """Accept only a real YYYY-MM-DD date that is not in the future."""
        parsed = parse_iso_date("date", value)
        if parsed > datetime.date.today():
            raise PydanticCustomError("date_in_future", "date cannot be in the future")
        return parsed

    @field_validator("severity", mode="before")
    @classmethod
    def check_severity(cls, value: Any) -> int:
        """Accept only a whole number from 1 to 5 (rejects 2.5, '3', true)."""
        if isinstance(value, bool) or not isinstance(value, int):
            raise PydanticCustomError(
                "severity_type",
                f"severity must be a whole number between {SEVERITY_MIN} and {SEVERITY_MAX}",
            )
        if not SEVERITY_MIN <= value <= SEVERITY_MAX:
            raise PydanticCustomError(
                "severity_range", f"severity must be between {SEVERITY_MIN} and {SEVERITY_MAX}"
            )
        return value


class DateRange(BaseModel):
    """Optional, inclusive date range filter, given as query parameters."""

    start_date: datetime.date | None = Field(
        default=None, description="First day to include (YYYY-MM-DD). Leave out for no limit."
    )
    end_date: datetime.date | None = Field(
        default=None, description="Last day to include (YYYY-MM-DD). Leave out for no limit."
    )

    @field_validator("start_date", "end_date", mode="before")
    @classmethod
    def check_date_format(cls, value: Any, info: ValidationInfo) -> datetime.date | None:
        """Accept only a real YYYY-MM-DD date, or nothing."""
        if value is None:
            return None
        return parse_iso_date(info.field_name or "date", value)

    @field_validator("end_date")
    @classmethod
    def check_order(cls, value: datetime.date | None, info: ValidationInfo) -> datetime.date | None:
        """start_date must not be after end_date."""
        start_date = info.data.get("start_date")
        if value is not None and start_date is not None and start_date > value:
            raise PydanticCustomError(
                "date_range_order", "start_date must be on or before end_date"
            )
        return value


class SymptomRead(BaseModel):
    """A saved symptom entry."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": 1,
                    "patient_id": 1,
                    "symptom": "Headache",
                    "notes": "Started in the morning, worse after lunch, eased after rest.",
                    "date": "2026-11-02",
                    "severity": 3,
                    "created_at": "2026-11-02T14:05:00Z",
                }
            ]
        },
    )

    id: int
    patient_id: int
    symptom: str
    notes: str | None
    date: datetime.date
    severity: int
    created_at: datetime.datetime = Field(description="When the entry was saved (UTC).")

    @field_validator("created_at")
    @classmethod
    def mark_as_utc(cls, value: datetime.datetime) -> datetime.datetime:
        """SQLite drops the time zone; stored times are always UTC."""
        if value.tzinfo is None:
            return value.replace(tzinfo=datetime.UTC)
        return value


class ErrorDetail(BaseModel):
    """One problem with one field."""

    field: str
    message: str


class ErrorBody(BaseModel):
    """The contents of every error response."""

    code: str
    message: str
    details: list[ErrorDetail] | None = None


class ErrorResponse(BaseModel):
    """Standard error format used by every error (FR-05)."""

    error: ErrorBody


VALIDATION_ERROR_EXAMPLE = {
    "error": {
        "code": "validation_error",
        "message": "Invalid input.",
        "details": [{"field": "severity", "message": "severity must be between 1 and 5"}],
    }
}

DATE_RANGE_ERROR_EXAMPLE = {
    "error": {
        "code": "validation_error",
        "message": "Invalid input.",
        "details": [{"field": "end_date", "message": "start_date must be on or before end_date"}],
    }
}

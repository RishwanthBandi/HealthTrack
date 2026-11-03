"""Symptom endpoints: log and list a patient's symptoms."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import (
    DATABASE_ERROR_EXAMPLE,
    DATE_RANGE_ERROR_EXAMPLE,
    VALIDATION_ERROR_EXAMPLE,
    DateRange,
    ErrorResponse,
    PatientId,
    SymptomCreate,
    SymptomRead,
)
from app.services import symptom_service

router = APIRouter(prefix="/patients/{patient_id}/symptoms", tags=["Symptoms"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=SymptomRead,
    summary="Log a symptom",
    responses={
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "model": ErrorResponse,
            "description": "Invalid input. Every problem is listed in `details`.",
            "content": {"application/json": {"example": VALIDATION_ERROR_EXAMPLE}},
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "model": ErrorResponse,
            "description": "Database error. The request had no effect; try again later.",
            "content": {"application/json": {"example": DATABASE_ERROR_EXAMPLE}},
        },
    },
)
def log_symptom(
    patient_id: PatientId,
    new_symptom: SymptomCreate,
    session: Annotated[Session, Depends(get_db)],
) -> SymptomRead:
    """Log one symptom for a patient (FR-01).

    - `symptom`: required, 1–100 characters after trimming spaces.
    - `notes`: optional, up to 2,000 characters; empty notes are stored as `null`.
    - `date`: required, `YYYY-MM-DD`, not in the future.
    - `severity`: required whole number from 1 to 5.

    Unknown extra fields are ignored. Returns the saved entry.
    """
    return symptom_service.log_symptom(session, patient_id, new_symptom)


@router.get(
    "",
    response_model=list[SymptomRead],
    summary="List a patient's symptoms",
    responses={
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "model": ErrorResponse,
            "description": "Invalid patient ID or dates. Every problem is listed in `details`.",
            "content": {"application/json": {"example": DATE_RANGE_ERROR_EXAMPLE}},
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "model": ErrorResponse,
            "description": "Database error. The request had no effect; try again later.",
            "content": {"application/json": {"example": DATABASE_ERROR_EXAMPLE}},
        },
    },
)
def list_symptoms(
    patient_id: PatientId,
    date_range: Annotated[DateRange, Query()],
    session: Annotated[Session, Depends(get_db)],
) -> list[SymptomRead]:
    """List a patient's symptoms, newest first (FR-02).

    - `start_date` and `end_date` are optional and **inclusive** (`YYYY-MM-DD`).
    - Only `start_date`: everything from that day on. Only `end_date`: everything up to it.
    - Neither: all of the patient's symptoms.
    - `start_date` after `end_date` is rejected.

    Returns `[]` when there are no matching symptoms.
    """
    return symptom_service.list_symptoms(session, patient_id, date_range)

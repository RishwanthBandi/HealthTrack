"""Symptom endpoints: log and list a patient's symptoms."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import (
    VALIDATION_ERROR_EXAMPLE,
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

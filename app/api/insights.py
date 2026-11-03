"""Insights endpoint for a patient's symptoms over a period."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import DATE_RANGE_ERROR_EXAMPLE, DateRange, ErrorResponse, Insights, PatientId
from app.services import insights_service

router = APIRouter(prefix="/patients/{patient_id}/insights", tags=["Insights"])


@router.get(
    "",
    response_model=Insights,
    summary="Get insights for a period",
    responses={
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "model": ErrorResponse,
            "description": "Invalid patient ID or dates. Every problem is listed in `details`.",
            "content": {"application/json": {"example": DATE_RANGE_ERROR_EXAMPLE}},
        },
    },
)
def get_insights(
    patient_id: PatientId,
    date_range: Annotated[DateRange, Query()],
    session: Annotated[Session, Depends(get_db)],
) -> Insights:
    """Most frequent symptom(s) and average severity for a period (FR-04).

    - Date rules are the same as for listing symptoms: `start_date` and `end_date` are
      optional and **inclusive**, and `start_date` may not be after `end_date`.
    - Frequency counts the `symptom` field only (not `notes`). "Headache", "headache"
      and " HEADACHE " count as the same symptom.
    - Ties: every symptom with the highest count is returned.
    - Each item in `most_frequent_symptoms` has its **own** `average_severity`.
    - `overall_average_severity` is the average of **all** entries in the period.
    - All averages are rounded to 2 decimals (half up).

    With no entries in the period: `total_entries` is 0, `most_frequent_symptoms` is `[]`
    and `overall_average_severity` is `null`.
    """
    return insights_service.get_insights(session, patient_id, date_range)

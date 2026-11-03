"""Business logic for logging and retrieving symptoms."""

from sqlalchemy.orm import Session

from app import repository
from app.schemas import DateRange, SymptomCreate, SymptomRead


def log_symptom(session: Session, patient_id: int, new_symptom: SymptomCreate) -> SymptomRead:
    """Save a validated symptom for a patient and return the saved entry."""
    entry = repository.create_symptom(
        session,
        patient_id=patient_id,
        symptom=new_symptom.symptom,
        notes=new_symptom.notes,
        date=new_symptom.date,
        severity=new_symptom.severity,
    )
    return SymptomRead.model_validate(entry)


def list_symptoms(session: Session, patient_id: int, date_range: DateRange) -> list[SymptomRead]:
    """A patient's symptoms within the date range, newest first."""
    entries = repository.list_symptoms(
        session,
        patient_id=patient_id,
        start_date=date_range.start_date,
        end_date=date_range.end_date,
    )
    return [SymptomRead.model_validate(entry) for entry in entries]

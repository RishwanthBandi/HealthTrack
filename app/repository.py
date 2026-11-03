"""Database reads and writes only. No business logic."""

import datetime

from sqlalchemy.orm import Session

from app.models import Symptom


def create_symptom(
    session: Session,
    patient_id: int,
    symptom: str,
    notes: str | None,
    date: datetime.date,
    severity: int,
) -> Symptom:
    """Insert one symptom row and commit it."""
    entry = Symptom(
        patient_id=patient_id, symptom=symptom, notes=notes, date=date, severity=severity
    )
    session.add(entry)
    session.commit()
    return entry

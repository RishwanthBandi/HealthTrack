"""Database reads and writes only. No business logic."""

import datetime

from sqlalchemy import select
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


def list_symptoms(
    session: Session,
    patient_id: int,
    start_date: datetime.date | None,
    end_date: datetime.date | None,
) -> list[Symptom]:
    """A patient's symptoms between two dates (both inclusive, both optional), newest first."""
    query = select(Symptom).where(Symptom.patient_id == patient_id)
    if start_date is not None:
        query = query.where(Symptom.date >= start_date)
    if end_date is not None:
        query = query.where(Symptom.date <= end_date)
    query = query.order_by(Symptom.date.desc(), Symptom.id.desc())
    return list(session.scalars(query))

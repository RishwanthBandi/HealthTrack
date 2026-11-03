"""SQLAlchemy tables."""

import datetime

from sqlalchemy import CheckConstraint, DateTime, Index, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all tables."""


def utc_now() -> datetime.datetime:
    """Current time in UTC, used for created_at."""
    return datetime.datetime.now(datetime.UTC)


class Symptom(Base):
    """One symptom a patient logged on a given day."""

    __tablename__ = "symptoms"
    __table_args__ = (
        CheckConstraint("severity BETWEEN 1 AND 5", name="ck_symptoms_severity_range"),
        Index("ix_symptoms_patient_id_date", "patient_id", "date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int]
    symptom: Mapped[str] = mapped_column(String(100))
    notes: Mapped[str | None] = mapped_column(String(2000))
    date: Mapped[datetime.date]
    severity: Mapped[int]
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

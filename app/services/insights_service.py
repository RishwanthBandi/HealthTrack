"""Business logic for insights: most frequent symptoms and average severity."""

from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.orm import Session

from app import repository
from app.models import Symptom
from app.schemas import DateRange, FrequentSymptom, Insights


def get_insights(session: Session, patient_id: int, date_range: DateRange) -> Insights:
    """Insights for a patient's symptoms within the date range."""
    entries = repository.list_symptoms(
        session,
        patient_id=patient_id,
        start_date=date_range.start_date,
        end_date=date_range.end_date,
    )
    severities = [entry.severity for entry in entries]
    return Insights(
        patient_id=patient_id,
        start_date=date_range.start_date,
        end_date=date_range.end_date,
        total_entries=len(entries),
        most_frequent_symptoms=most_frequent_symptoms(entries),
        overall_average_severity=rounded_average(severities) if severities else None,
    )


def most_frequent_symptoms(entries: list[Symptom]) -> list[FrequentSymptom]:
    """All symptoms with the highest count, each with its own average severity, sorted by name.

    Names are compared in lowercase with spaces trimmed, so "Headache" and " headache " match.
    """
    severities_by_symptom: dict[str, list[int]] = defaultdict(list)
    for entry in entries:
        severities_by_symptom[entry.symptom.strip().lower()].append(entry.severity)
    if not severities_by_symptom:
        return []
    highest = max(len(severities) for severities in severities_by_symptom.values())
    return [
        FrequentSymptom(
            symptom=name, count=len(severities), average_severity=rounded_average(severities)
        )
        for name, severities in sorted(severities_by_symptom.items())
        if len(severities) == highest
    ]


def rounded_average(severities: list[int]) -> float:
    """Average of a non-empty list, rounded to 2 decimals half up (2.125 becomes 2.13)."""
    average = Decimal(sum(severities)) / len(severities)
    return float(average.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

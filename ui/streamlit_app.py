"""HealthTrack Streamlit UI: screens for logging symptoms and viewing insights."""

import datetime
from typing import Any

import streamlit as st

import api_client

SEVERITY_LABELS = {
    1: "1 – very mild",
    2: "2 – mild",
    3: "3 – moderate",
    4: "4 – severe",
    5: "5 – very severe",
}
NOTES_PREVIEW_LENGTH = 60
# Widest possible range, so the date box never rejects or replaces a date; the API decides.
WIDEST_DATE_RANGE: dict[str, Any] = {
    "min_value": datetime.date.min,
    "max_value": datetime.date.max,
}


def show_api_error(error: api_client.ApiError) -> None:
    """Show the API's error message and each field problem."""
    st.error(error.message)
    for detail in error.details:
        st.markdown(f"- {detail}")


def show_log_symptom_screen() -> None:
    """Form to log one symptom; shows a success message or the API's error messages."""
    with st.form("log_symptom"):
        patient_id = st.text_input(
            "Patient ID", value="1", key="log_patient_id", help="A positive whole number."
        )
        symptom = st.text_input(
            "Symptom", placeholder="e.g. Headache", help="Short name, up to 100 characters."
        )
        notes = st.text_area(
            "Notes (optional)",
            placeholder="Describe the symptom in as much detail as you like.",
            help="Up to 2,000 characters.",
        )
        date = st.date_input(
            "Date",
            value="today",
            format="YYYY-MM-DD",
            help="The day the symptom happened. Cannot be in the future.",
            **WIDEST_DATE_RANGE,
        )
        severity = st.select_slider(
            "Severity",
            options=list(SEVERITY_LABELS),
            value=3,
            format_func=SEVERITY_LABELS.get,
        )
        submitted = st.form_submit_button("Save symptom")

    if submitted:
        try:
            saved = api_client.log_symptom(patient_id, symptom, notes, date, severity)
        except api_client.ApiError as error:
            show_api_error(error)
        else:
            st.success(
                f"Saved: **{saved['symptom']}** on {saved['date']} "
                f"(severity {saved['severity']}) for patient {saved['patient_id']}."
            )


def show_my_symptoms_screen() -> None:
    """Date-range filter and a table of the patient's symptoms, newest first."""
    with st.form("my_symptoms"):
        patient_id = st.text_input(
            "Patient ID", value="1", key="list_patient_id", help="A positive whole number."
        )
        start_column, end_column = st.columns(2)
        start_date = start_column.date_input(
            "From (optional)",
            value=None,
            format="YYYY-MM-DD",
            help="Leave empty to start from the first entry.",
            **WIDEST_DATE_RANGE,
        )
        end_date = end_column.date_input(
            "To (optional)",
            value=None,
            format="YYYY-MM-DD",
            help="Leave empty to include everything up to the latest entry.",
            **WIDEST_DATE_RANGE,
        )
        submitted = st.form_submit_button("Show symptoms")

    if not submitted:
        return
    try:
        entries = api_client.list_symptoms(patient_id, start_date, end_date)
    except api_client.ApiError as error:
        show_api_error(error)
        return
    if not entries:
        st.info(no_results_message(patient_id, start_date, end_date))
        return
    st.caption(f"{len(entries)} {'entry' if len(entries) == 1 else 'entries'}, newest first.")
    st.dataframe(symptom_table_rows(entries), hide_index=True, width="stretch")
    show_full_notes(entries)


def show_insights_screen() -> None:
    """Date-range filter and the patient's insights: top symptom(s) and average severity."""
    with st.form("insights"):
        patient_id = st.text_input(
            "Patient ID", value="1", key="insights_patient_id", help="A positive whole number."
        )
        start_column, end_column = st.columns(2)
        start_date = start_column.date_input(
            "From (optional)",
            value=None,
            format="YYYY-MM-DD",
            help="Leave empty to start from the first entry.",
            key="insights_start_date",
            **WIDEST_DATE_RANGE,
        )
        end_date = end_column.date_input(
            "To (optional)",
            value=None,
            format="YYYY-MM-DD",
            help="Leave empty to include everything up to the latest entry.",
            key="insights_end_date",
            **WIDEST_DATE_RANGE,
        )
        submitted = st.form_submit_button("Show insights")

    if not submitted:
        return
    try:
        insights = api_client.get_insights(patient_id, start_date, end_date)
    except api_client.ApiError as error:
        show_api_error(error)
        return
    if insights["total_entries"] == 0:
        st.info(no_results_message(patient_id, start_date, end_date))
        return
    show_insights(insights)


def show_insights(insights: dict[str, Any]) -> None:
    """Overall numbers, then the most frequent symptom(s) with their own averages."""
    total_entries = insights["total_entries"]
    st.caption(f"Period: {period_label(insights['start_date'], insights['end_date'])}")
    entries_column, average_column = st.columns(2)
    entries_column.metric("Entries", total_entries)
    average_column.metric(
        overall_average_label(total_entries),
        f"{insights['overall_average_severity']:.2f} / {max(SEVERITY_LABELS)}",
    )
    top_symptoms = insights["most_frequent_symptoms"]
    if len(top_symptoms) == 1:
        st.subheader("Most frequent symptom")
    else:
        st.subheader("Most frequent symptoms (tie)")
        times = top_symptoms[0]["count"]
        st.caption(
            f"These {len(top_symptoms)} symptoms were each logged "
            f"{'once' if times == 1 else f'{times} times'}."
        )
    st.dataframe(top_symptom_rows(top_symptoms), hide_index=True, width="stretch")


def overall_average_label(total_entries: int) -> str:
    """Label that makes clear the overall average covers every entry, not one symptom."""
    if total_entries == 1:
        return "Average severity (the only entry)"
    return f"Average severity (all {total_entries} entries)"


def top_symptom_rows(top_symptoms: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One table row per most frequent symptom, with that symptom's own average."""
    return [
        {
            "Symptom": item["symptom"],
            "Times logged": item["count"],
            "Average severity (this symptom)": f"{item['average_severity']:.2f}",
        }
        for item in top_symptoms
    ]


def period_label(start_date: str | None, end_date: str | None) -> str:
    """The searched period in words, e.g. '2026-11-01 to 2026-11-07' or 'all entries'."""
    if start_date and end_date:
        return f"{start_date} to {end_date}"
    if start_date:
        return f"from {start_date} onward"
    if end_date:
        return f"up to {end_date}"
    return "all entries"


def no_results_message(
    patient_id: str, start_date: datetime.date | None, end_date: datetime.date | None
) -> str:
    """Friendly message for an empty result that names what was searched."""
    if start_date is None and end_date is None:
        return f"Patient {patient_id.strip()} has not logged any symptoms yet."
    if start_date is not None and end_date is not None:
        message = f"No symptoms found between {start_date} and {end_date}."
    elif start_date is not None:
        message = f"No symptoms found from {start_date} onward."
    else:
        message = f"No symptoms found up to {end_date}."
    if start_date is not None and start_date > datetime.date.today():
        message += " Your start date is in the future, so there can't be any entries yet."
    return message


def symptom_table_rows(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One table row per entry; long notes are shortened for display only."""
    return [
        {
            "Date": entry["date"],
            "Symptom": entry["symptom"],
            "Severity": entry["severity"],
            "Notes": notes_preview(entry["notes"]),
        }
        for entry in entries
    ]


def notes_preview(notes: str | None) -> str:
    """The start of the notes, with '…' if they are longer than the preview."""
    if not notes:
        return ""
    if len(notes) <= NOTES_PREVIEW_LENGTH:
        return notes
    return notes[:NOTES_PREVIEW_LENGTH].rstrip() + "…"


def show_full_notes(entries: list[dict[str, Any]]) -> None:
    """Full text of every note that was shortened in the table."""
    shortened = [
        entry for entry in entries if entry["notes"] and len(entry["notes"]) > NOTES_PREVIEW_LENGTH
    ]
    if not shortened:
        return
    with st.expander(f"Full notes ({len(shortened)})"):
        for entry in shortened:
            st.markdown(f"**{entry['date']} · {entry['symptom']}**")
            st.text(entry["notes"])


st.set_page_config(page_title="HealthTrack", page_icon="🩺")
st.title("HealthTrack")
st.write("Track your daily symptoms and see simple insights.")
log_tab, list_tab, insights_tab = st.tabs(["Log a symptom", "My symptoms", "Insights"])
with log_tab:
    show_log_symptom_screen()
with list_tab:
    show_my_symptoms_screen()
with insights_tab:
    show_insights_screen()

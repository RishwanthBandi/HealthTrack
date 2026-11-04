"""HealthTrack Streamlit UI: screens for logging symptoms and viewing insights."""

import datetime
import logging
import re
from collections.abc import Callable
from typing import Any

import altair as alt
import pandas as pd
import streamlit as st

import api_client

logger = logging.getLogger(__name__)

SEVERITY_LABELS = {
    1: "1 – very mild",
    2: "2 – mild",
    3: "3 – moderate",
    4: "4 – severe",
    5: "5 – very severe",
}
MARKDOWN_SPECIAL_CHARACTER = re.compile(r"([!-/:-@\[-`{-~])")
CHART_HEIGHT = 300
BAR_HEIGHT = 36
# Medium grey: readable on both the light and the dark Streamlit theme.
CHART_LABEL_COLOR = "#808495"
UNEXPECTED_ERROR_MESSAGE = (
    "Something went wrong while showing this screen. Please try again. "
    "If it keeps happening, restart the app."
)
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


def show_screen_safely(show_screen: Callable[[str], None], patient_id: str) -> None:
    """Run one screen; if anything unexpected fails, show a friendly message, not a traceback.

    The real error is logged in the terminal running Streamlit, for debugging.
    """
    try:
        show_screen(patient_id)
    except Exception:
        logger.exception("Unexpected error in screen %s", show_screen.__name__)
        st.error(UNEXPECTED_ERROR_MESSAGE)


def show_log_symptom_screen(patient_id: str) -> None:
    """Form to log one symptom; shows a success message or the API's error messages."""
    with st.form("log_symptom"):
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
                f"Saved: **{escape_markdown(symptom_display_name(saved['symptom']))}** "
                f"on {saved['date']} "
                f"(severity {saved['severity']}) for patient {saved['patient_id']}."
            )


def show_my_symptoms_screen(patient_id: str) -> None:
    """Date-range filter and one card per symptom entry, newest first, with full notes."""
    with st.form("my_symptoms"):
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
    for entry in entries:
        show_entry_card(entry)


def show_entry_card(entry: dict[str, Any]) -> None:
    """One bordered card: symptom and severity, the date, and a "View notes" box if any."""
    with st.container(border=True):
        symptom_column, severity_column = st.columns(2)
        symptom_column.markdown(f"**{escape_markdown(symptom_display_name(entry['symptom']))}**")
        severity_column.markdown(
            f"Severity {SEVERITY_LABELS[entry['severity']]}", text_alignment="right"
        )
        st.caption(entry["date"])
        if entry["notes"]:
            with st.expander("View notes"):
                st.text(entry["notes"])


def symptom_display_name(symptom: str) -> str:
    """One display format everywhere, e.g. ' HEadAche ' -> 'Headache'. Stored data is unchanged."""
    return symptom.strip().capitalize()


def escape_markdown(text: str) -> str:
    """Show user text exactly as typed, e.g. '*' or '_' are not turned into formatting."""
    return MARKDOWN_SPECIAL_CHARACTER.sub(r"\\\1", text)


def show_insights_screen(patient_id: str) -> None:
    """Date-range filter, the patient's insights and charts of their entries."""
    with st.form("insights"):
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
        entries = api_client.list_symptoms(patient_id, start_date, end_date)
    except api_client.ApiError as error:
        show_api_error(error)
        return
    if insights["total_entries"] == 0:
        st.info(no_results_message(patient_id, start_date, end_date))
        return
    show_insights(insights)
    show_charts(entries)


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


def show_charts(entries: list[dict[str, Any]]) -> None:
    """Daily severity and how often each symptom was logged. Fixed charts: no zoom or pan."""
    st.subheader("Daily severity")
    st.caption("Average severity per day (1 = mild, 5 = severe)")
    st.altair_chart(daily_severity_chart(average_severity_per_day(entries)), width="stretch")
    st.subheader("Symptoms logged")
    st.altair_chart(symptoms_logged_chart(times_logged_per_symptom(entries)), width="stretch")


def daily_severity_chart(daily_severity: pd.DataFrame) -> alt.Chart:
    """Line with a dot for each day; severity axis fixed from 1 to 5, dates without times."""
    return (
        alt.Chart(daily_severity)
        .mark_line(point=alt.OverlayMarkDef(size=80))
        .encode(
            x=alt.X(
                "utcyearmonthdate(Date):T",
                title="Date",
                axis=alt.Axis(
                    format="%Y-%m-%d", tickCount={"interval": "day", "step": 1}, labelAngle=0
                ),
            ),
            y=alt.Y(
                "Average severity:Q",
                scale=alt.Scale(domain=[min(SEVERITY_LABELS), max(SEVERITY_LABELS)]),
                axis=alt.Axis(values=list(SEVERITY_LABELS), format="d"),
            ),
            tooltip=[
                alt.Tooltip("utcyearmonthdate(Date):T", title="Date", format="%Y-%m-%d"),
                alt.Tooltip("Average severity:Q", format=".2f"),
                alt.Tooltip("Entries:Q"),
            ],
        )
        .properties(height=CHART_HEIGHT)
    )


def symptoms_logged_chart(times_logged: pd.DataFrame) -> alt.LayerChart:
    """Horizontal bars, most logged first, starting at 0, with the count at the end of each bar.

    The axis goes one step past the highest count, so its label always fits.
    """
    axis_end = int(times_logged["Times logged"].max()) + 1
    bars = (
        alt.Chart(times_logged)
        .mark_bar()
        .encode(
            x=alt.X(
                "Times logged:Q",
                scale=alt.Scale(domain=[0, axis_end]),
                axis=alt.Axis(tickMinStep=1, format="d"),
            ),
            y=alt.Y("Symptom:N", sort="-x", title=None, axis=alt.Axis(labelLimit=200)),
            tooltip=["Symptom:N", "Times logged:Q"],
        )
    )
    counts = bars.mark_text(
        align="left", dx=6, fontSize=13, fontWeight="bold", color=CHART_LABEL_COLOR
    ).encode(text="Times logged:Q")
    return (bars + counts).properties(height=alt.Step(BAR_HEIGHT))


def average_severity_per_day(entries: list[dict[str, Any]]) -> pd.DataFrame:
    """Chart data: each day with entries, that day's average severity and entry count."""
    severities_per_day: dict[str, list[int]] = {}
    for entry in entries:
        severities_per_day.setdefault(entry["date"], []).append(entry["severity"])
    days = sorted(severities_per_day)
    return pd.DataFrame(
        {
            "Date": days,
            "Average severity": [
                sum(severities_per_day[day]) / len(severities_per_day[day]) for day in days
            ],
            "Entries": [len(severities_per_day[day]) for day in days],
        }
    )


def times_logged_per_symptom(entries: list[dict[str, Any]]) -> pd.DataFrame:
    """Chart data: how often each symptom was logged, grouped like the insights."""
    counts: dict[str, int] = {}
    for entry in entries:
        name = symptom_display_name(entry["symptom"])
        counts[name] = counts.get(name, 0) + 1
    return pd.DataFrame({"Symptom": list(counts), "Times logged": list(counts.values())})


def overall_average_label(total_entries: int) -> str:
    """Label that makes clear the overall average covers every entry, not one symptom."""
    if total_entries == 1:
        return "Average severity (the only entry)"
    return f"Average severity (all {total_entries} entries)"


def top_symptom_rows(top_symptoms: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One table row per most frequent symptom, with that symptom's own average."""
    return [
        {
            "Symptom": symptom_display_name(item["symptom"]),
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


st.set_page_config(page_title="HealthTrack", page_icon="🩺")
st.title("HealthTrack")
st.write("Track your daily symptoms and see simple insights.")
selected_patient_id = st.sidebar.text_input(
    "Patient ID", value="1", key="patient_id", help="A positive whole number."
)
st.sidebar.caption("All three tabs use this patient.")
log_tab, list_tab, insights_tab = st.tabs(["Log a symptom", "My symptoms", "Insights"])
with log_tab:
    show_screen_safely(show_log_symptom_screen, selected_patient_id)
with list_tab:
    show_screen_safely(show_my_symptoms_screen, selected_patient_id)
with insights_tab:
    show_screen_safely(show_insights_screen, selected_patient_id)

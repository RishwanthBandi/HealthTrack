"""HealthTrack Streamlit UI: screens for logging symptoms and viewing insights."""

import datetime

import streamlit as st

import api_client

SEVERITY_LABELS = {
    1: "1 – very mild",
    2: "2 – mild",
    3: "3 – moderate",
    4: "4 – severe",
    5: "5 – very severe",
}


def show_log_symptom_screen() -> None:
    """Form to log one symptom; shows a success message or the API's error messages."""
    st.header("Log a symptom")
    with st.form("log_symptom"):
        patient_id = st.text_input("Patient ID", value="1", help="A positive whole number.")
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
            min_value=datetime.date.min,
            max_value=datetime.date.max,
            format="YYYY-MM-DD",
            help="The day the symptom happened. Cannot be in the future.",
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
            st.error(error.message)
            for detail in error.details:
                st.markdown(f"- {detail}")
        else:
            st.success(
                f"Saved: **{saved['symptom']}** on {saved['date']} "
                f"(severity {saved['severity']}) for patient {saved['patient_id']}."
            )


st.set_page_config(page_title="HealthTrack", page_icon="🩺")
st.title("HealthTrack")
st.write("Track your daily symptoms and see simple insights.")
show_log_symptom_screen()

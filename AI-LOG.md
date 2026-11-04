# 🤖 AI Log – How AI was used in this project

A running record of what AI tools produced and what I checked, changed or rejected.
The README's **AI usage** section is written from this file.

> **When to add an entry:** whenever I change, fix or reject something the AI produced,
> or verify something important (tests, edge cases, the brief).

---

## 🛠️ Tools used

| Tool | Used for |
|---|---|
| **Claude Code** (VS Code extension) | Writing code and tests slice by slice, following the rules in `CLAUDE.md` |

---

## ✅ How I verify AI-generated work (every slice)

- Read Claude's summary and its decisions before approving; accept or change each one
- Check that tests were written first and failed before the code existed
- Run `pytest`, `ruff check .` and `ruff format --check .`; a pre-commit hook also runs them and blocks any failing commit
- Try every new endpoint in `/docs`, including invalid input
- Test the UI by hand, including edge cases (empty fields, future dates, API stopped)
- Ask Claude to explain any file I don't fully understand

---

## 📝 Log

### 1. Patients had no room to describe their symptoms
**📅 2 Nov · Area: Requirements / data model (FR-01, FR-03, FR-04)**

- **Problem:** The AI's first requirements draft had only one short text field, `symptoms` (max 200 characters). It was both the symptom's name and the only place to write anything about it.
- **How I found it:** While reviewing the first requirements draft. A patient usually wants to explain more than one word: when it started, how it feels, what makes it better or worse. That detail is also what a doctor needs.
- **Why not just make the field longer:** The same field is used to find the "most frequent symptom". If patients wrote full sentences there, "Headache since morning" and "Headache" would count as two different symptoms, and the insights would break.
- **Fix:** Split it into two fields:
  - `symptom`: required, short (max 100 characters), e.g. "Headache". Used for insights.
  - `notes`: optional, up to 2,000 characters. The patient's full description.
- **How I checked it:** Tests for both limits (`test_fr03_rejects_symptom_longer_than_100_characters`, `test_fr01_rejects_notes_longer_than_2000_characters`) and a test that insights count only the `symptom` field, never the notes (`test_fr04_counts_frequency_on_symptom_field_not_notes`).
- **Why it matters:** Patients can describe their problem properly for the doctor, and the insights stay accurate. The 2,000-character limit only protects against oversized input.

---

### 2. A future date was silently saved as today
**📅 3 Nov · Area: UI – Log a symptom form (FR-06)**

- **Problem:** If I picked a date after today, the form still said "Saved", but it stored **today's date** instead of the date I picked.
- **How I found it:** While testing the form by hand. The date box turned red, yet the success message showed a different date than the one I entered.
- **Cause:** The AI had limited the date picker to today. When a date is outside that limit, Streamlit quietly keeps the last valid date instead of blocking the form.
- **Fix:** Replaced the limit with the widest possible date range (without one, Streamlit applies its own ±10-year limit and the bug returns for far-off dates). The form now always sends the date the patient picked, and the API decides. I also had the other fields checked for the same problem: Patient ID became a text box and the character limits on Symptom and Notes were removed, because pasted text was being cut off silently.
- **How I checked it:** Retested the form. A future date now shows *"date cannot be in the future"* and nothing is saved; a past date is saved exactly as picked.
- **Why it matters:** A health app must never store different data than the patient entered. Keeping the date check in the API also means the rule exists in one place only.

---

### 3. A very large patient ID crashed the API

📅 3 Nov · Area: Validation (FR-01, FR-02)

- **Problem:** A patient ID like `100000000000000000000` made the API crash with a plain "Internal Server Error" instead of returning a clear validation message.
- **How I found it:** While testing the API with different patient ID values, I tried an extremely large number (`100000000000000000000`). Instead of returning a proper validation error, the API crashed. This helped me identify an edge case in the patient ID validation.
- **Cause:** The ID was only checked as a positive whole number. A huge number passes that check, but it is too large for the database's INTEGER type to store.
- **Fix:** I introduced a maximum patient ID limit of `2,147,483,647`. IDs exceeding this limit now return a clear `422` error: `patient_id must be at most 2147483647`.
- **How I verified it:** Added 4 tests covering saving and reading patients with IDs exceeding the limit and IDs exactly at the limit. The oversized ID tests reproduced the actual crash before the fix, and all 4 tests passed after the fix.
- **Why it matters:** Invalid input should always produce a clear validation error rather than an unexpected server crash. This limit also ensures compatibility with the standard 32-bit signed INTEGER range used by many databases.

---

### 4. The "no results" message was misleading
**📅 3 Nov · Area: UI – My symptoms screen (FR-06)**

- **Problem:** The screen always said *"No symptoms found for this period."*, even when I hadn't chosen any dates and the patient had simply never logged anything.
- **How I found it:** While testing the screen with a new patient ID.
- **Fix:** The message now describes what was actually searched:
  - no dates chosen: *"Patient 42 has not logged any symptoms yet."*
  - dates chosen: *"No symptoms found between 2026-09-01 and 2026-09-30."*
- **How I checked it:** Retested with a new patient ID, with and without dates, and confirmed the right message appears each time.
- **Why it matters:** FR-06 requires that patients can use the app *"without confusion"*. A message about a "period" when no period was chosen doesn't tell the patient what happened.

---

### 5. The overall average looked like it belonged to tied symptoms
**📅 3 Nov · Area: Insights (FR-04)**

- **Problem:** With a tie (fever ×2, headache ×2), the response showed one average severity right after both symptoms, so it looked like their shared average.
- **How I found it:** While testing the insights endpoint in `/docs`.
- **Cause:** Not a bug: the value is the overall average for the period, as FR-04 requires. But the response didn't make that clear.
- **Fix:** Kept the overall average and added each symptom's own average to the list. The UI now labels the overall value "Average severity (all entries)".
- **How I checked it:** New tests for per-symptom averages; retested the tie case in `/docs` and the UI.
- **Why it matters:** Patients and doctors must not misread health data. Seeing which symptom is more severe is also more useful.

---

### 6. One shared Patient ID instead of one per tab
**📅 3 Nov · Area: UI – all screens (FR-06)**

- **Problem:** Each tab (Log a symptom, My symptoms, Insights) had its own Patient ID box. I had to type the same ID three times, and the tabs could easily show different patients by mistake.
- **How I found it:** While using the app across the three tabs.
- **Fix:** I asked Claude to replace the three boxes with **one Patient ID in the sidebar**, used by all three tabs, with the hint *"All three tabs use this patient."* Changing the patient clears the results on screen, so one patient's data is never shown under another patient's ID.
- **How I checked it:** Logged a symptom, listed symptoms and opened insights with the sidebar ID; all three used the same patient. An invalid ID (`abc`) still shows the API's error message.
- **Why it matters:** Less typing and no risk of mixing up patients between tabs, which matters in a health app.

---

### 7. Charts zoomed, moved and showed impossible values
**📅 3 Nov · Area: UI – Insights charts (FR-06)**

- **Problem:** The charts zoomed and moved when scrolled or dragged, cutting off axis labels and showing impossible values like −2. The date axis showed hours, even though symptoms are logged per day.
- **How I found it:** While testing the charts and resizing the window.
- **Fix:** Turned off zoom/pan, fixed the severity axis to 1–5, made counts start at 0 with whole numbers, and showed dates only on the date axis.
- **How I checked it:** Scrolled, dragged and resized the window; the charts stayed readable and the values stayed realistic.
- **Why it matters:** A chart that can show a negative severity is misleading in a health app.

---

### 8. Long notes were cut off and hard to read
**📅 4 Nov · Area: UI – My symptoms screen (FR-06)**

- **Problem:** The My symptoms table cut every note to 60 characters, and the column couldn't be scrolled, so long notes were impossible to read. A separate "Full notes" section below repeated each entry that had notes, which made the page long and repetitive.
- **How I found it:** While testing the screen with a long, realistic note.
- **Options I compared:**
  - Click a row to see its full note below the table
  - Show the full note wrapped inside the table
  - Replace the table with one card per entry
  - Keep the table and list only entries that have notes
- **First choice, and why I changed it:** I first chose click-a-row, to keep the table. When I tested it, rows could only be selected with a checkbox: clicking the row itself did nothing, so the hint "Click a row" was misleading, and the checkboxes made the table look like a form.
- **Final choice:** One card per entry with a collapsed **"View notes"** section. The list stays short and easy to scan, and the full note opens only when the patient wants it.
- **Fix:** Replaced the table with entry cards (symptom, severity and date, newest first). Entries with notes have a collapsed "View notes" section that shows the full text when clicked; entries without notes show none. Removed the separate "Full notes" section and the checkbox table.
- **How I checked it:** Opened "View notes" on an entry with a 2,000-character note and saw the full text, exactly as stored; entries without notes show no "View notes".
- **Why it matters:** Notes are where patients describe their problem for the doctor, so they must be fully readable, but they shouldn't clutter the list.

---

### 9. Symptom names were shown inconsistently between screens
**📅 4 Nov · Area: UI – My symptoms and Insights (FR-04, FR-06)**

- **Problem:** Insights grouped different spellings of the same symptom ("Headache", "HEadAche", "headache") as one, but showed the name in lowercase. My symptoms showed each name exactly as typed. The same symptom looked different on different screens.
- **How I found it:** While comparing the My symptoms list with the Insights tab for the same patient.
- **Decision:** Change only how names are **displayed**, never what's **stored**. The database keeps exactly what the patient typed, and the UI shows every name in one tidy format.
- **Fix:** All screens (My symptoms cards, the Insights table, the "Symptoms logged" chart and the "Saved" message after logging) now show symptom names trimmed, with a capital first letter and the rest lowercase, e.g. "Headache".
- **How I checked it:** Logged "  HEadAche " for a patient who already had "HEADACHE", "headache" and "Headache". Every screen shows "Headache", and the API still returns the original text for each entry.
- **Why it matters:** A patient should see the same symptom the same way everywhere. Keeping the stored text unchanged means no patient data is altered.

---

### 10. The daily severity chart was hard to understand
**📅 4 Nov · Area: UI – Insights charts (FR-06)**

- **Problem:** The chart's date axis was spread evenly across calendar time. One old entry from 2019 pushed all the recent entries into a thin spike on the far right, so the newest dates couldn't be read. The axis also showed dates with no data, like "2022-09-23", and it wasn't clear what the chart was showing.
- **How I found it:** While looking at the Insights tab for a patient with an old entry, from the patient's point of view.
- **Fix:** Redesigned it with the title "How severe were your symptoms each day?". Each day with entries is one evenly spaced point labelled with its date, oldest left and newest right; only the most recent 14 entry-days are shown, with a caption saying so. The severity axis is fixed at 1–5.
- **How I checked it:** With a 2019 entry and 18 recent days, the chart shows the 14 newest days, each with a readable date, plus the caption "Showing the most recent 14 of 19 days with entries." Hovering over a point shows its date, average severity and number of entries, matching the stored data.
- **Why it matters:** A chart in a health app should be understood at a glance. One that needs explaining, or hides the newest data, does more harm than good.

---

<!--
Template for new entries (copy, paste above this comment and fill in):

### N. Short title of what happened
**📅 Date · Area: ...**

- **Problem:**
- **How I found it:**
- **Cause:** (optional)
- **Fix:**
- **How I checked it:**
- **Why it matters:**

---
-->

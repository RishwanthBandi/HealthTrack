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

### 1. A future date was silently saved as today
**📅 3 Nov · Area: UI – Log a symptom form (FR-06)**

- **Problem:** If I picked a date after today, the form still said "Saved", but it stored **today's date** instead of the date I picked.
- **How I found it:** While testing the form by hand. The date box turned red, yet the success message showed a different date than the one I entered.
- **Cause:** The AI had limited the date picker to today. When a date is outside that limit, Streamlit quietly keeps the last valid date instead of blocking the form.
- **Fix:** Replaced the limit with the widest possible date range (without one, Streamlit applies its own ±10-year limit and the bug returns for far-off dates). The form now always sends the date the patient picked, and the API decides. I also had the other fields checked for the same problem: Patient ID became a text box and the character limits on Symptom and Notes were removed, because pasted text was being cut off silently.
- **How I checked it:** Retested the form. A future date now shows *"date cannot be in the future"* and nothing is saved; a past date is saved exactly as picked.
- **Why it matters:** A health app must never store different data than the patient entered. Keeping the date check in the API also means the rule exists in one place only.

---

### 2. A very large patient ID crashed the API
**📅 3 Nov · Area: Validation (FR-01, FR-02)**

- **Problem:** A patient ID like `100000000000000000000` made the API crash with a plain *"Internal Server Error"* instead of a clear message.
- **How I found it:** I asked Claude to review the slice for edge cases, and it found this crash.
- **Cause:** The ID was only checked as "a positive whole number". A huge number passes that check, but it's too big for the database to store, so the database crashed.
- **Fix:** I decided on a maximum patient ID of **2,147,483,647**. Bigger IDs now get a clear `422` error: *"patient_id must be at most 2147483647"*.
- **How I checked it:** 4 new tests for saving and reading: too-big IDs and exactly at the limit. The too-big tests failed with the real crash before the fix; all pass after it.
- **Why it matters:** Bad input should always get a clear error, never a crash. 2,147,483,647 is the limit of the standard INTEGER type in most databases, so it keeps working if SQLite is replaced later.

---

### 3. The "no results" message was misleading
**📅 3 Nov · Area: UI – My symptoms screen (FR-06)**

- **Problem:** The screen always said *"No symptoms found for this period."*, even when I hadn't chosen any dates and the patient had simply never logged anything.
- **How I found it:** While testing the screen with a new patient ID.
- **Fix:** The message now describes what was actually searched:
  - no dates chosen: *"Patient 42 has not logged any symptoms yet."*
  - dates chosen: *"No symptoms found between 2026-09-01 and 2026-09-30."*
- **How I checked it:** Retested with a new patient ID, with and without dates, and confirmed the right message appears each time.
- **Why it matters:** FR-06 requires that patients can use the app *"without confusion"*. A message about a "period" when no period was chosen doesn't tell the patient what happened.

---

### 4. The overall average looked like it belonged to tied symptoms
**📅 3 Nov · Area: Insights (FR-04)**

- **Problem:** With a tie (fever ×2, headache ×2), the response showed one average severity right after both symptoms, so it looked like their shared average.
- **How I found it:** While testing the insights endpoint in `/docs`.
- **Cause:** Not a bug: the value is the overall average for the period, as FR-04 requires. But the response didn't make that clear.
- **Fix:** Kept the overall average and added each symptom's own average to the list. The UI now labels the overall value "Average severity (all entries)".
- **How I checked it:** New tests for per-symptom averages; retested the tie case in `/docs` and the UI.
- **Why it matters:** Patients and doctors must not misread health data. Seeing which symptom is more severe is also more useful.

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

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

## 📝 Log

### 1. Future date silently saved as today
**📅 3 Nov · Area: UI (FR-06)**

- **What the AI produced:** The date picker was limited to today. If a future date was typed, the box turned red but the form still submitted, silently replacing it with **today's date** and saving it.
- **What I found / changed:** Found it while testing the form. Had the limit removed, so the selected date is always sent to the API, which rejects future dates; the UI now shows the API's error and saves nothing.
- **Why:** The app must never save different data than the patient entered, and validation should live in one place (the API).

---

### 2. Very large patient ID crashed the API
**📅 3 Nov · Area: Validation (FR-01, FR-02)**

- **What the AI produced:** `patient_id` was only checked as "a positive whole number", so a huge ID passed validation and crashed the database with a plain 500 error.
- **What I found / changed:** Asked Claude to review edge cases; it found the crash. I chose a maximum of 2,147,483,647 so too-big IDs get a clear 422 error, and had tests added for GET and POST.
- **Why:** Invalid input must get a clear 422, never a crash. 2,147,483,647 is the standard integer limit, so it also works if the database changes later.

---

### 3. Misleading "no results" message in My symptoms
**📅 3 Nov · Area: UI (FR-06)**

- **What the AI produced:** The My symptoms screen always said "No symptoms found for this period." when nothing came back, even when no dates were set and the patient had simply never logged anything.
- **What I found / changed:** Noticed it while testing with a new patient ID. Had the message changed to name what was searched: "Patient 42 has not logged any symptoms yet." with no dates, or the actual period (e.g. "No symptoms found between 2026-09-01 and 2026-09-30.") when dates are set.
- **Why:** FR-06 says patients must use the UI "without confusion"; a message about a "period" when no period was chosen does not tell the patient what actually happened.

---

<!--
Template for new entries (copy, paste above this comment and fill in):

### N. Short title of what happened
**📅 Date · Area: ...**

- **What the AI produced:**
- **What I found / changed:**
- **Why:**

---
-->
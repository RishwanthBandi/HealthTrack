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

<!--
Template for new entries (copy, paste above this comment and fill in):

### N. Short title of what happened
**📅 Date · Area: ...**

- **What the AI produced:**
- **What I found / changed:**
- **Why:**

---
-->
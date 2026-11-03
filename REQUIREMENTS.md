# HealthTrack – Requirements

> Patient Symptom Tracker. A web application where patients log daily symptoms
> and get insights from their entries.
>
> This file is the single source of truth for **what** we build.
> Every requirement has an ID (FR = functional, NFR = non-functional) that is
> used in commits and tests.

**Status legend:** ⬜ Not started · 🟨 In progress · ✅ Done (tested)

---

## 1. Users and goal

- **Primary user:** a patient who wants to track their health condition over time.
- **Goal:** record symptoms quickly and correctly, retrieve them by date, and see simple insights (most frequent symptom, average severity).

---

## 2. Functional requirements

### FR-01 (Must): Log a symptom

A patient can log a symptom with a **symptom name**, optional **notes**, a **date**, and a **severity level (1–5)**.

**Endpoint:** `POST /patients/{patient_id}/symptoms`

**Fields**
| Field | Required | Rules | Purpose |
|---|---|---|---|
| `symptom` | Yes | Not empty after trimming, max 100 characters | Short name, e.g. "Headache". Used for insights |
| `notes` | No | Max 2,000 characters | Detailed description for the patient/doctor |
| `date` | Yes | YYYY-MM-DD, not in the future | Day the symptom happened |
| `severity` | Yes | Whole number 1–5 | How bad it was |

**Request example**
```json
{
  "symptom": "Headache",
  "notes": "Started in the morning, worse after lunch, eased after rest.",
  "date": "2026-11-02",
  "severity": 3
}
```

**Success response:** `201 Created`
```json
{ "id": 1, "patient_id": 1, "symptom": "Headache",
  "notes": "Started in the morning, worse after lunch, eased after rest.",
  "date": "2026-11-02", "severity": 3, "created_at": "2026-11-02T14:05:00Z" }
```

**Acceptance criteria (from the brief)**
- Given a patient logs a symptom, when they submit, then the symptom is **saved in the database with the correct date and severity**.
- The saved record can be read back with exactly the same values.
- Leading/trailing spaces in `symptom` and `notes` are removed before saving.
- Empty or whitespace-only `notes` are stored as no notes (`null`).

**Edge cases**
| Input | Expected |
|---|---|
| `date` missing | 422 error: "date is required" |
| `date` not a real date (`"2026-13-45"`, `"yesterday"`) | 422 error: invalid date, use YYYY-MM-DD |
| `date` in the future | 422 error: date cannot be in the future |
| `notes` missing | Accepted (notes are optional) |
| `notes` longer than 2,000 characters | 422 error: notes too long |
| `patient_id` is 0, negative or not a number | 422 error |
| `patient_id` larger than 2,147,483,647 | 422 error: "patient_id must be at most 2147483647" |
| Extra unknown fields in the body | Ignored |

**Status:** ✅ (API; UI form follows in FR-06)

---

### FR-02 (Must): Retrieve a patient's symptoms with a date-range filter

**Endpoint:** `GET /patients/{patient_id}/symptoms?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD`

**Success response:** `200 OK`, a list of that patient's symptoms, newest first.

**Acceptance criteria (from the brief)**
- Given a valid patient ID and date range, when the API is called, then it returns **only the symptoms logged within that range**.
- Only the requested patient's symptoms are returned, never another patient's.
- The range is **inclusive**: entries on `start_date` and on `end_date` are included.
- Results are sorted by date, newest first.

**Edge cases**
| Input | Expected |
|---|---|
| No symptoms in the range | `200` with an empty list `[]` (not an error) |
| Patient has never logged anything | `200` with `[]` |
| Only `start_date` given | Everything from that date onward |
| Only `end_date` given | Everything up to that date |
| Neither given | All of the patient's symptoms |
| `start_date` after `end_date` | 422 error: "start_date must be on or before end_date" |
| Invalid date format | 422 error |
| `patient_id` is 0, negative or not a number | 422 error |
| `patient_id` larger than 2,147,483,647 | 422 error: "patient_id must be at most 2147483647" |

**Status:** ✅ (API; UI table follows in FR-06)

---

### FR-03 (Must): Input validation

Severity must be between **1 and 5**, and the symptom must **not be empty**.
(The brief's "symptom description" is the `symptom` field.)

**Acceptance criteria (from the brief)**
- Given an input form, when a patient submits an **empty symptom** or an **invalid severity**, then the application returns a **clear error message** and **nothing is saved**.

**Rules**
- `severity`: whole number, 1 ≤ severity ≤ 5.
- `symptom`: required, not empty after trimming spaces, max 100 characters.
- Error responses say **which field** is wrong and **why**, in plain language.

**Edge cases**
| Input | Expected |
|---|---|
| severity `0`, `6`, `-1` | 422: "severity must be between 1 and 5" |
| severity `2.5` | 422: must be a whole number |
| severity `"abc"`, `null`, missing | 422 |
| severity `1` and `5` (boundaries) | Accepted |
| symptom `""` | 422: "symptom must not be empty" |
| symptom `"    "` (only spaces) | 422: "symptom must not be empty" |
| symptom missing | 422: "symptom is required" |
| symptom longer than 100 characters | 422: too long (use `notes` for details) |
| Several fields wrong at once | 422 listing all problems |

**Status:** ✅

---

### FR-04 (Should): Insights for a period

Show the **most frequent symptom(s)** and the **average severity** for a period.

**Endpoint:** `GET /patients/{patient_id}/insights?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD`

**Success response:** `200 OK`
```json
{
  "patient_id": 1,
  "start_date": "2026-11-01",
  "end_date": "2026-11-07",
  "total_entries": 5,
  "most_frequent_symptoms": [ { "symptom": "headache", "count": 3, "average_severity": 3.0 } ],
  "overall_average_severity": 3.4
}
```

**Acceptance criteria (from the brief)**
- Given a date range, when insights are requested, then the response contains the **most frequent symptom** and the **average severity** for that period.
- Date-range rules are the same as FR-02 (inclusive, both optional, start ≤ end).
- Frequency is counted on the `symptom` field only (not `notes`).
- `overall_average_severity` is the average of **all** entries in the period (not only the most frequent symptoms).
- Each item in `most_frequent_symptoms` also has its **own** `average_severity`: the average of that symptom's entries only.
- All averages are rounded to 2 decimal places (half up: 2.125 → 2.13).

**Edge cases**
| Situation | Expected |
|---|---|
| No entries in the period | `200` with `total_entries: 0`, `most_frequent_symptoms: []`, `overall_average_severity: null` |
| Tie (e.g. Headache ×2, Fever ×2) | Both are returned in `most_frequent_symptoms`, each with its own `average_severity`; `overall_average_severity` stays the average of all entries |
| `"Headache"`, `"headache"`, `" HEADACHE "` | Counted as the **same** symptom (compared in lowercase, trimmed) |
| Only one entry | That entry is the most frequent; its own average and `overall_average_severity` both equal its severity |
| `start_date` after `end_date` | 422 error |

**Status:** ✅ (API; UI insights section follows in FR-06)

---

### FR-05 (Should): Error handling

The API handles failures gracefully, with one consistent error format.

**Acceptance criteria (from the brief)**
- Given a **database error**, when an API request is made, then the app returns **HTTP 500** with an appropriate error message.

**Standard error format (used by every error)**
```json
{ "error": { "code": "database_error", "message": "The service could not reach the database. Please try again later." } }
```
Validation errors also include field details:
```json
{ "error": { "code": "validation_error", "message": "Invalid input.",
  "details": [ { "field": "severity", "message": "severity must be between 1 and 5" } ] } }
```

**Cases**
| Situation | Status | `code` |
|---|---|---|
| Database unavailable / query fails | 500 | `database_error` |
| Invalid input (body, path or query) | 422 | `validation_error` |
| Malformed JSON body | 422 | `validation_error` |
| Unknown URL | 404 | `not_found` |
| Wrong HTTP method | 405 | `method_not_allowed` |
| Any other unexpected error | 500 | `internal_error` |

**Rules**
- Never show stack traces, SQL or internal details to the user.
- Log the real error on the server side for debugging.
- A failed request never leaves half-saved data.

**Status:** ✅ (API; UI error messages follow in FR-06)

---

### FR-06 (Could): Simple front end (Python)

A user-friendly interface built with **Streamlit** to log symptoms and view insights.

**Acceptance criteria (from the brief)**
- Given the front end, when a patient uses it, then they can **easily log symptoms and view insights without confusion**.

**Screens / sections**
1. **Log a symptom:** patient ID, symptom name, notes (multi-line text box), date picker (defaults to today), severity slider 1–5, Submit button. Shows a success message or the API's error message.
2. **My symptoms:** patient ID, date range, table of results (newest first). Friendly message when there are no results.
3. **Insights:** date range → most frequent symptom(s), average severity, number of entries.

**Rules**
- The UI talks **only to the API** (never directly to the database), so the same validation applies everywhere.
- If the API is not running, show a friendly message ("Cannot reach the HealthTrack API. Is it running?") instead of crashing.

**Status:** 🟨 (Log a symptom, My symptoms and Insights screens done; error handling follows in Slice 4)

---

## 3. Non-functional requirements

| ID | Requirement |
|---|---|
| NFR-01 | **Clean code structure**: layered design: API routes → services (logic) → repository (database queries); schemas hold validation; one job per file. |
| NFR-02 | **Well-documented API**: every endpoint has a description, request/response examples and its error responses, visible in the auto-generated docs at `/docs`. |
| NFR-03 | **Automated tests** for every FR and every edge case listed above, using a separate test database. A database failure is simulated in a test. |
| NFR-04 | **Security**: every input validated; database access only through the ORM (no SQL built from strings); no secrets in code; settings from environment variables, with a `.env.example`. |
| NFR-05 | **Git hygiene**: small, meaningful commits per feature/fix; `.env`, database files, `__pycache__/` and `.venv/` are never committed. |

---

## 4. Out of scope (the brief says these are not needed)

- User authentication and authorization (login). The `patient_id` in the URL identifies the patient.
- Deployment to a live server. The app runs locally.
- Advanced machine-learning model integration. Insights are simple statistics.

---

## 5. Assumptions and decisions

| # | Assumption / decision | Why |
|---|---|---|
| A1 | A patient is identified only by a positive whole-number `patient_id` (1 to 2,147,483,647, the standard 32-bit integer limit, so it works with any database); there is no separate "create patient" step | No auth or patient management is asked for |
| A2 | `date` is the day the symptom happened; `created_at` records entry time automatically | "Daily symptoms" in the brief |
| A3 | Future dates are rejected | You can't experience a symptom in the future |
| A4 | `date` is required in the API (the UI pre-fills today) | The brief says patients input the date |
| A5 | One symptom per entry; two symptoms on one day = two entries | Keeps frequency counting correct |
| A6 | Symptom name and detailed notes are **separate fields** (`symptom` max 100, `notes` max 2,000) | Patients can describe the problem in detail without breaking "most frequent symptom" counting. The upper limits only protect against oversized input |
| A7 | Symptoms are matched for insights by lowercase + trimmed text (no spelling correction or synonyms) | Simple and predictable; ML is out of scope |
| A8 | Ties for "most frequent" return all tied symptoms | Fairer than picking one at random |
| A9 | Database errors return 500 | The brief's check explicitly says 500 |
| A10 | SQLite is the database | No setup; enough for a local exercise |

---

## 6. Traceability (filled in while building)

| FR | Endpoint / component | Tests | Status |
|---|---|---|---|
| FR-01 | `POST /patients/{patient_id}/symptoms` | `tests/test_symptoms.py`: `test_fr01_logs_symptom_and_returns_201_with_saved_record`, `test_fr01_saves_symptom_in_database_with_correct_date_and_severity`, `test_fr01_trims_symptom_and_notes_before_saving`, `test_fr01_stores_empty_or_whitespace_only_notes_as_null`, `test_fr01_accepts_missing_notes`, `test_fr01_accepts_notes_of_exactly_2000_characters`, `test_fr01_rejects_notes_longer_than_2000_characters`, `test_fr01_rejects_missing_date`, `test_fr01_rejects_date_that_is_not_a_real_yyyy_mm_dd_date`, `test_fr01_rejects_future_date`, `test_fr01_accepts_today_as_date`, `test_fr01_rejects_patient_id_that_is_not_a_positive_whole_number`, `test_fr01_rejects_patient_id_larger_than_2147483647`, `test_fr01_accepts_largest_patient_id_2147483647`, `test_fr01_ignores_extra_unknown_fields` | ✅ |
| FR-02 | `GET /patients/{patient_id}/symptoms` | `tests/test_symptoms.py`: `test_fr02_returns_only_symptoms_within_date_range`, `test_fr02_includes_entries_on_start_date_and_end_date`, `test_fr02_accepts_same_start_and_end_date`, `test_fr02_returns_only_the_requested_patients_symptoms`, `test_fr02_sorts_symptoms_newest_first`, `test_fr02_returns_all_fields_of_each_symptom`, `test_fr02_returns_empty_list_when_no_symptoms_in_range`, `test_fr02_returns_empty_list_for_patient_who_never_logged`, `test_fr02_only_start_date_returns_everything_from_that_date`, `test_fr02_only_end_date_returns_everything_up_to_that_date`, `test_fr02_no_dates_returns_all_of_the_patients_symptoms`, `test_fr02_rejects_start_date_after_end_date`, `test_fr02_rejects_invalid_date_format`, `test_fr02_rejects_patient_id_that_is_not_a_positive_whole_number`, `test_fr02_rejects_patient_id_larger_than_2147483647`, `test_fr02_accepts_largest_patient_id_2147483647` | ✅ |
| FR-03 | Schemas (validation) | `tests/test_validation.py`: `test_fr03_validation_error_uses_standard_error_format`, `test_fr03_rejects_severity_outside_1_to_5`, `test_fr03_rejects_severity_that_is_not_a_whole_number`, `test_fr03_rejects_missing_severity`, `test_fr03_accepts_severity_boundaries_1_and_5`, `test_fr03_rejects_empty_or_whitespace_only_symptom`, `test_fr03_rejects_missing_symptom`, `test_fr03_rejects_symptom_that_is_not_text`, `test_fr03_rejects_symptom_longer_than_100_characters`, `test_fr03_accepts_symptom_of_exactly_100_characters`, `test_fr03_lists_all_problems_when_several_fields_are_wrong` | ✅ |
| FR-04 | `GET /patients/{patient_id}/insights` | `tests/test_insights.py`: `test_fr04_returns_most_frequent_symptom_and_overall_average_severity`, `test_fr04_includes_entries_on_start_date_and_end_date`, `test_fr04_only_uses_the_requested_patients_entries`, `test_fr04_returns_all_tied_symptoms`, `test_fr04_gives_each_frequent_symptom_its_own_average_and_keeps_overall_average`, `test_fr04_rounds_each_symptoms_average_severity_to_2_decimals_half_up`, `test_fr04_counts_different_capitalisation_and_spaces_as_same_symptom`, `test_fr04_counts_frequency_on_symptom_field_not_notes`, `test_fr04_rounds_overall_average_severity_to_2_decimals`, `test_fr04_rounds_overall_average_severity_half_up`, `test_fr04_returns_empty_insights_when_no_entries_in_period`, `test_fr04_returns_empty_insights_for_patient_who_never_logged`, `test_fr04_single_entry_is_most_frequent_and_its_severity_is_the_average`, `test_fr04_only_start_date_uses_everything_from_that_date`, `test_fr04_only_end_date_uses_everything_up_to_that_date`, `test_fr04_no_dates_uses_all_of_the_patients_entries`, `test_fr04_rejects_start_date_after_end_date`, `test_fr04_rejects_invalid_date_format`, `test_fr04_rejects_invalid_patient_id` | ✅ |
| FR-05 | Error handlers | `tests/test_errors.py`: `test_fr05_database_error_returns_500_with_standard_error_format`, `test_fr05_database_error_does_not_reveal_sql_or_internal_details`, `test_fr05_database_error_is_logged_on_the_server`, `test_fr05_failed_save_leaves_no_half_saved_data`, `test_fr05_unexpected_error_returns_500_internal_error_without_details`, `test_fr05_unknown_url_returns_404_not_found`, `test_fr05_wrong_http_method_returns_405_method_not_allowed`, `test_fr05_malformed_json_body_returns_422_validation_error`, `test_fr05_every_endpoint_documents_the_500_database_error` | ✅ |
| FR-06 | Streamlit UI | Checked by hand: Log a symptom form (success, field errors, API down); My symptoms table (date filters, newest first, no-results message and future-start hint, field errors, long-notes preview); Insights section (top symptom, ties with each symptom's own average, overall average labelled "all N entries", no-results messages, field errors, API down) | 🟨 |

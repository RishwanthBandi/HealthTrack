# CLAUDE.md – Project rules for HealthTrack

You are helping build **HealthTrack**, a patient symptom tracker (FastAPI API + optional Streamlit UI).
Follow these rules in every task.

## Source of truth

- **REQUIREMENTS.md** defines *what* to build (FR-01 … FR-06, NFR-01 … NFR-05, edge cases, decisions).
- **PLAN.md** defines *how* it is designed (architecture, endpoints, data model, slices).
- If a task conflicts with these files, or something is unclear, **stop and ask me**. Never change a requirement or decision silently.

## Tech stack

- Python 3.11+
- FastAPI (API) + Pydantic v2 (validation)
- SQLAlchemy 2.x + SQLite (database)
- pytest + FastAPI `TestClient` (tests)
- ruff (formatting and linting)
- Streamlit + `requests` (UI, FR-06 only)

**Ask me before adding any other library.**

## Folder structure

```
app/
  main.py              # creates the FastAPI app, registers routers and error handlers
  config.py            # settings read from environment variables (e.g. DATABASE_URL)
  db.py                # engine, session, get_db dependency
  models.py            # SQLAlchemy tables
  schemas.py           # Pydantic request/response models (all validation lives here)
  errors.py            # standard error format + exception handlers
  repository.py        # database queries only
  services/
    symptom_service.py   # logic for logging and retrieving symptoms
    insights_service.py  # logic for insights (frequency, average severity)
  api/
    symptoms.py        # symptom endpoints
    insights.py        # insights endpoint
ui/
  streamlit_app.py     # Streamlit screens (forms, tables, insights)
  api_client.py        # all HTTP calls to the API + friendly error messages
tests/
  conftest.py          # test app, separate test database, fixtures
  test_symptoms.py
  test_validation.py
  test_insights.py
  test_errors.py
```

## Layer rules (separation of concerns)

Request flow: **API route → schema validation → service → repository → database**

- **api/**: receive the request, call a service, return the response. No business logic, no queries.
- **schemas.py**: input/output shapes and all validation rules.
- **services/**: business logic (e.g. insights calculation). No HTTP details, no raw queries.
- **repository.py**: database reads/writes only. No business logic.
- **ui/**: talks to the API over HTTP only. Never imports from `app/` and never touches the database. Screens call `api_client.py`; only `api_client.py` makes HTTP requests.
- One clear job per file and per function. Keep functions short.

## Coding rules

- Use type hints everywhere.
- Clear, descriptive names. No abbreviations like `s`, `tmp`, `data2`.
- Short docstrings on public functions and on every endpoint (they show up in `/docs`).
- No dead code, commented-out code or unused imports.
- Don't over-engineer: build only what the current task needs.

## Validation and errors

- Every input (body, path and query parameters) is validated with Pydantic, following the rules in REQUIREMENTS.md.
- `severity` must be a whole number 1–5 (reject `2.5`, `"abc"`, `true`).
- Trim `symptom` and `notes` before validating and saving.
- Every error uses the standard format from FR-05:
  `{"error": {"code": "...", "message": "...", "details": [...]}}`
- Database errors → **500** with code `database_error`. Validation errors → **422** with code `validation_error`.
- Never return stack traces, SQL or internal details. Log them on the server instead.

## API documentation

- Every endpoint has a `summary`, a description, a response model, request/response examples, and its documented error responses, so `/docs` is complete on its own.

## Testing

- Write the tests for a requirement **first**, then the code that makes them pass.
- Every FR and every edge case in REQUIREMENTS.md has at least one test.
- Test names say what they check, e.g. `test_fr03_rejects_whitespace_only_symptom`.
- Tests use a **separate test database** and never touch the real one.
- Simulate the database failure (FR-05) by overriding the database dependency so it raises an error.
- Run `pytest` and `ruff check .` before every commit. Both must pass.

## Security

- No secrets, passwords or keys in code. Settings come from environment variables; keep a `.env.example` with safe example values.
- Database access only through SQLAlchemy. Never build SQL from strings.
- Enforce the length limits from REQUIREMENTS.md (`symptom` max 100, `notes` max 2,000).

## Git

- Small commits: one per feature, test set or fix. Never one giant commit.
- Message format: `type(scope): short description`. Examples:
  - `feat(FR-01): log a symptom with date and severity`
  - `test(FR-03): reject empty and whitespace-only symptoms`
  - `fix(FR-02): reject start_date after end_date`
  - `docs: add API section to README`
  - `chore: set up project structure and tooling`
- `.gitignore` must exclude: `.env`, `*.db`, `__pycache__/`, `.venv/`, `.pytest_cache/`, `.ruff_cache/`.
- **Don't commit until I've seen the changes and said OK.**

## How we work

1. Work on **one slice at a time**, as listed in PLAN.md. Don't start the next slice unless I ask.
2. Each slice has two parts, **API first, then UI**:
   - API part: write the tests → write the code → run `pytest` and `ruff` → show me a short summary → wait for my OK → commit.
   - UI part: build the screen for that feature → tell me how to check it in the browser → wait for my OK → commit.
3. When a requirement is done and tested, update its **Status** and the **Traceability** table in REQUIREMENTS.md (test names included).
4. After each slice, remind me to add a line to **AI-LOG.md** if I changed or rejected anything you produced.
5. Explain your code in simple terms when I ask. I need to understand it well enough to present it myself.

## Commands

```bash
# install
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# run the API (docs at http://localhost:8000/docs)
uvicorn app.main:app --reload

# run the UI
streamlit run ui/streamlit_app.py

# test and lint
pytest
ruff check .
ruff format .
```

# Volunteer Hours Site Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A Flask + PostgreSQL site where students from the school list log in by a one-time email code, record volunteer hours, and an admin confirms or rejects them.

**Architecture:** One Flask app with server-rendered Jinja pages. SQLAlchemy models on PostgreSQL (SQLite locally for tests). Login codes are sent via SMTP; the sender account and password come from environment variables. The admin account is created from environment variables at startup. The student list is imported with a CLI command that keeps only class, full name, and email.

**Tech Stack:** Python 3.12, Flask, Flask-SQLAlchemy, Flask-Migrate, psycopg (PostgreSQL driver), gunicorn, bcrypt, pytest, openpyxl (import only), Render (web service + Postgres).

**Spec:** `C:\Users\monya\volunteer-hours\DESIGN.md`

## Global Constraints

- Only school email is a login identifier. Students never set a password.
- Stored student fields: `class_name`, `full_name`, `email`. The "Логин" column (ID-like number) is never imported or stored.
- Login code: 6 digits, expires after 10 minutes, max 5 attempts, stored as a bcrypt hash.
- Volunteer entry: date not later than today; hours from 0.5 to 12 in steps of 0.5; status `pending` / `approved` / `rejected`.
- A student may edit or delete an entry only while it is `pending`. Approved entries are never changed by anyone.
- Secrets (`SMTP_PASSWORD`, `ADMIN_PASSWORD`, `SECRET_KEY`, `DATABASE_URL`) are read only from environment variables, never from files in the repo.
- Interface language: Russian.

## Review Focus

1. **Email with different letter case or spaces** (`Ivanov@UKK.nis.edu.kz `) must match the list; expected: normalized (trimmed, lowercased) before lookup.
2. **Email not in list** must not send a code and must show a clear message; expected: no email sent, no account created.
3. **Expired or reused code** must be rejected; expected: "код недействителен", no session.
4. **Hours outside allowed values** (0, 0.3, 13, 2.25) must be rejected; expected: validation error, nothing saved.
5. **Admin tries to change an approved entry** must be refused; expected: 409 or error message, status unchanged.

Each line gets its test in the task that owns the code (Tasks 3, 4, 5, 6).

---

### Task 1: Project skeleton and configuration

**Files:**
- Create: `volunteer-hours/app/__init__.py` (app factory `create_app(config: dict | None = None) -> Flask`)
- Create: `volunteer-hours/app/config.py` (class `Config` reading env vars: `DATABASE_URL`, `SECRET_KEY`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `ADMIN_LOGIN`, `ADMIN_PASSWORD`)
- Create: `volunteer-hours/requirements.txt`
- Create: `volunteer-hours/tests/conftest.py` (fixture `app` with SQLite in-memory DB, fixture `client`)
- Create: `volunteer-hours/tests/test_config.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `create_app(config) -> Flask`; `db` (Flask-SQLAlchemy instance) in `app/__init__.py`; `Config` class.

- [ ] **Step 1: Write the failing test** in `tests/test_config.py`: `create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite://"})` returns a Flask app and `app.config["TESTING"] is True`.
- [ ] **Step 2: Run** `pytest tests/test_config.py -v`. Expected: FAIL, module not found.
- [ ] **Step 3: Implement** the app factory, `Config`, and `requirements.txt`. Read `DATABASE_URL` from env, fall back to `sqlite:///dev.db`. Render provides `postgres://` URLs; rewrite the prefix to `postgresql+psycopg://`.
- [ ] **Step 4: Run** `pytest -v`. Expected: PASS.
- [ ] **Step 5: Initialize git and commit**: `git init`, then `git add -A && git commit -m "feat: app skeleton and config"`.

---

### Task 2: Data models and migrations

**Files:**
- Create: `volunteer-hours/app/models.py` with `Student`, `Admin`, `VolunteerEntry`, `LoginCode`
- Create: `volunteer-hours/tests/test_models.py`

**Interfaces:**
- Consumes: `db` from Task 1.
- Produces:
  - `Student(id, full_name: str, class_name: str, email: str unique)`
  - `Admin(id, login: str unique, password_hash: str)`
  - `VolunteerEntry(id, student_id FK, date: date, description: str, hours: Decimal(4,1), status: str, admin_comment: str | None, created_at, decided_at)`
  - `LoginCode(id, email: str, code_hash: str, expires_at: datetime, attempts: int, used: bool)`

- [ ] **Step 1: Write failing tests**: create a Student, a VolunteerEntry with default `status == "pending"`, and confirm `email` is unique (second insert raises `IntegrityError`).
- [ ] **Step 2: Run** `pytest tests/test_models.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement** the four models. Add Flask-Migrate (`flask db init` / `migrate` / `upgrade`) and commit the generated migration.
- [ ] **Step 4: Run** `pytest -v`. Expected: PASS.
- [ ] **Step 5: Commit**: `git add -A && git commit -m "feat: data models and migrations"`.

---

### Task 3: Student list import (CLI)

**Files:**
- Create: `volunteer-hours/app/importer.py` with `import_students(path: str) -> ImportResult`
- Create: `volunteer-hours/app/cli.py` registering `flask import-students <path>`
- Create: `volunteer-hours/tests/test_importer.py`, `volunteer-hours/tests/fixtures/students_sample.xlsx`

**Interfaces:**
- Consumes: models from Task 2.
- Produces: `ImportResult(created: int, updated: int, skipped: int)`.

Input format: the sheet has class header rows (e.g. `10A`) followed by name rows; the name row has full name in column B, the ID-like value in column C (ignored), and email in column D. The importer reads only class, name and email. Rows with blank email are skipped.

- [ ] **Step 1: Write failing tests**: importing the sample file creates the expected number of students; `class_name` is taken from the nearest class header above; the ID column is not present on the `Student` model; importing twice does not duplicate rows (`updated` counts changes); a row with no email is counted in `skipped`.
- [ ] **Step 2: Run** `pytest tests/test_importer.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement** `import_students` with `openpyxl`, matching on lowercased email; register the CLI command.
- [ ] **Step 4: Run** `pytest -v`. Expected: PASS. Then run `flask import-students "<path to Оқушылар тізімі.xlsx>"` once locally and check the counts.
- [ ] **Step 5: Commit**: `git add -A && git commit -m "feat: import student list from xlsx"`.

---

### Task 4: Student login by one-time email code

**Files:**
- Create: `volunteer-hours/app/auth.py` (routes `/login` GET/POST, `/login/code` GET/POST, `/logout`; functions `issue_code(email) -> None`, `verify_code(email, code) -> bool`)
- Create: `volunteer-hours/app/mailer.py` with `send_code_email(to: str, code: str) -> None` using `smtplib` + STARTTLS on `SMTP_HOST:SMTP_PORT`
- Create: `volunteer-hours/templates/login.html`, `volunteer-hours/templates/login_code.html`
- Create: `volunteer-hours/tests/test_auth.py`

**Interfaces:**
- Consumes: `Student`, `LoginCode` (Task 2); config (Task 1).
- Produces: session key `student_id` set on success; `login_required` decorator `student_required` in `app/auth.py`.

Rules: email is trimmed and lowercased; if no `Student` matches, respond with "вас нет в списке, обратитесь к координатору" and send nothing. Code is `secrets.randbelow(10**6)` zero-padded to 6 digits. Stored as bcrypt hash. Expired, used, or 5-attempt codes are rejected. A new code invalidates older unused ones for that email.

- [ ] **Step 1: Write failing tests** (mailer mocked): unknown email sends no mail; known email sends one mail and creates a `LoginCode`; wrong code increments `attempts`; the 6th attempt is refused; an expired code is refused; a correct code sets `student_id` in session and marks the code used; reusing the code fails; email with spaces and uppercase matches the list.
- [ ] **Step 2: Run** `pytest tests/test_auth.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement** `issue_code`, `verify_code`, the routes, and `send_code_email`. The mailer reads `SMTP_*` from config.
- [ ] **Step 4: Run** `pytest -v`. Expected: PASS.
- [ ] **Step 5: Commit**: `git add -A && git commit -m "feat: student login by email code"`.

---

### Task 5: Student cabinet and volunteer entries

**Files:**
- Create: `volunteer-hours/app/student.py` (routes `/cabinet` GET, `/entries/new` GET/POST, `/entries/<id>/edit` GET/POST, `/entries/<id>/delete` POST)
- Create: `volunteer-hours/app/validation.py` with `validate_entry(date_str, description, hours_str, today) -> (cleaned: dict, errors: dict)`
- Create: `volunteer-hours/templates/cabinet.html`, `volunteer-hours/templates/entry_form.html`
- Create: `volunteer-hours/tests/test_student.py`, `volunteer-hours/tests/test_validation.py`

**Interfaces:**
- Consumes: `student_required` (Task 4); `VolunteerEntry` (Task 2).
- Produces: `cabinet` shows `total_approved_hours: Decimal` (sum of `approved`) and the student's entries with status.

Validation: date ≤ today; description non-empty, ≤ 500 characters; hours in `{0.5, 1.0, 1.5, ..., 12.0}`.

- [ ] **Step 1: Write failing tests**: `validate_entry` rejects hours `0`, `0.3`, `13`, `2.25`, a future date, and empty description, and accepts `0.5` and `12`. Student A cannot see or edit student B's entry (404). Editing a `pending` entry works; editing or deleting an `approved` entry is refused. The cabinet total equals the sum of approved hours only.
- [ ] **Step 2: Run** `pytest tests/test_validation.py tests/test_student.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement** the validator and routes, scoping every query by `session["student_id"]`.
- [ ] **Step 4: Run** `pytest -v`. Expected: PASS.
- [ ] **Step 5: Commit**: `git add -A && git commit -m "feat: student cabinet and volunteer entries"`.

---

### Task 6: Admin login and review

**Files:**
- Create: `volunteer-hours/app/admin.py` (routes `/admin/login` GET/POST, `/admin` GET, `/admin/entries/<id>/decide` POST, `/admin/logout`; decorator `admin_required`)
- Create: `volunteer-hours/app/bootstrap.py` with `ensure_admin(login: str, password: str) -> None` (creates or updates the `Admin` row with bcrypt hash); called from `create_app` when `ADMIN_LOGIN` and `ADMIN_PASSWORD` are set.
- Create: `volunteer-hours/templates/admin_login.html`, `volunteer-hours/templates/admin.html`
- Create: `volunteer-hours/tests/test_admin.py`

**Interfaces:**
- Consumes: `Admin`, `VolunteerEntry` (Task 2); `db`.
- Produces: `decide(entry_id, decision: "approved" | "rejected", comment: str | None, admin_id) -> VolunteerEntry`, which raises `ValueError` if the entry is not `pending`.

- [ ] **Step 1: Write failing tests**: wrong admin password is refused; correct one opens `/admin`; approving sets `status="approved"` and `decided_at`; rejecting with a comment stores it; deciding an already-approved entry raises `ValueError` and leaves status unchanged; a student session cannot open `/admin`; `ensure_admin` called twice does not duplicate the admin.
- [ ] **Step 2: Run** `pytest tests/test_admin.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement** the admin module and `ensure_admin`. The admin list is filterable by `class_name` via query string `?class=`.
- [ ] **Step 4: Run** `pytest -v`. Expected: PASS.
- [ ] **Step 5: Commit**: `git add -A && git commit -m "feat: admin login and review"`.

---

### Task 7: Render deployment

**Files:**
- Create: `volunteer-hours/render.yaml` (web service with `gunicorn "app:create_app()"`, Postgres database, env var keys without values)
- Create: `volunteer-hours/.gitignore` (excludes `.env`, `dev.db`, `__pycache__/`)
- Modify: `volunteer-hours/README.md` with deploy steps: set `SMTP_USER`, `SMTP_PASSWORD`, `ADMIN_LOGIN`, `ADMIN_PASSWORD`, `SECRET_KEY` in Render Environment; run `flask db upgrade` and `flask import-students` in the Render shell.

**Interfaces:**
- Consumes: everything above.
- Produces: a live URL.

- [ ] **Step 1: Write a smoke test**: `create_app` with production-like config (`SECRET_KEY` from env, Postgres URL rewritten) imports without error; `GET /login` returns 200.
- [ ] **Step 2: Run** `pytest -v`. Expected: PASS.
- [ ] **Step 3: Create** `render.yaml`, `.gitignore`, README. Push the repo to GitHub, connect it in Render, set env vars.
- [ ] **Step 4: Verify on Render**: open `/login`, request a code for your own school address, log in, add an entry, log in as admin, approve it. Expected: each step works and the cabinet total updates.
- [ ] **Step 5: Commit**: `git add -A && git commit -m "chore: render deployment config"`.

---

**Open items (user):** Gmail sender account and App Password (set on Render as `SMTP_USER` / `SMTP_PASSWORD`); admin login and password (set on Render as `ADMIN_LOGIN` / `ADMIN_PASSWORD`); `SECRET_KEY` generated on Render.

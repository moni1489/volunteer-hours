import re
import secrets
from datetime import timedelta
from functools import wraps

import bcrypt
from flask import Blueprint, redirect, render_template, request, session, url_for
from sqlalchemy import func, select

from app import db, mailer
from app.i18n import translate as _
from app.models import LoginCode, Student, _utcnow

bp = Blueprint("auth", __name__)

CODE_TTL = timedelta(minutes=10)
MAX_ATTEMPTS = 5
PENDING_KEY = "login_email"


def normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def find_student(email: str) -> Student | None:
    email = normalize_email(email)
    if not email:
        return None
    return db.session.scalar(select(Student).where(func.lower(Student.email) == email))


def issue_code(email: str) -> None:
    """Create a new one-time code for a student on the list and email it.

    Does nothing if the email is not on the student list.
    """
    student = find_student(email)
    if student is None:
        return
    email = normalize_email(email)

    LoginCode.query.filter_by(email=email, used=False).update({"used": True})
    code = f"{secrets.randbelow(10**6):06d}"
    db.session.add(
        LoginCode(
            email=email,
            code_hash=bcrypt.hashpw(code.encode(), bcrypt.gensalt()).decode(),
            expires_at=_utcnow() + CODE_TTL,
        )
    )
    db.session.commit()
    mailer.send_code_email(student.email, code)


def verify_code(email: str, code: str) -> bool:
    """Check a code for an email. A correct code is marked used; a wrong one counts an attempt."""
    email = normalize_email(email)
    row = db.session.scalar(
        select(LoginCode)
        .where(LoginCode.email == email, LoginCode.used.is_(False), LoginCode.expires_at > _utcnow())
        .order_by(LoginCode.id.desc())
    )
    if row is None or row.attempts >= MAX_ATTEMPTS:
        return False
    if not bcrypt.checkpw((code or "").encode(), row.code_hash.encode()):
        row.attempts += 1
        db.session.commit()
        return False
    row.used = True
    db.session.commit()
    return True


def student_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if "student_id" not in session:
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)

    return wrapper


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html", error=None)

    email = normalize_email(request.form.get("email", ""))
    if find_student(email) is None:
        session.pop(PENDING_KEY, None)
        return render_template("login.html", error=_("login.not_on_list"))

    issue_code(email)
    session[PENDING_KEY] = email
    return redirect(url_for("auth.login_code"))


@bp.route("/login/code", methods=["GET", "POST"])
def login_code():
    email = session.get(PENDING_KEY)
    if not email:
        return redirect(url_for("auth.login"))

    if request.method == "GET":
        return render_template("login_code.html", error=None, email=email)

    code = request.form.get("code", "").strip()
    student = find_student(email)
    if not re.fullmatch(r"\d{6}", code) or student is None or not verify_code(email, code):
        return render_template("login_code.html", error=_("code.bad"), email=email)

    # Keep the chosen interface language across the session reset.
    lang = session.get("lang")
    session.clear()
    if lang:
        session["lang"] = lang
    session["student_id"] = student.id
    return redirect("/")


@bp.route("/logout")
def logout():
    session.pop("student_id", None)
    session.pop(PENDING_KEY, None)
    return redirect(url_for("auth.login"))

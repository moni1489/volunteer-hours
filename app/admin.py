from functools import wraps

import bcrypt
from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for
from sqlalchemy import select

from app import db
from app.i18n import translate as _
from app.models import Admin, Student, VolunteerEntry, _utcnow

bp = Blueprint("admin", __name__, url_prefix="/admin")

ADMIN_KEY = "admin_id"
DECISIONS = ("approved", "rejected")


def admin_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if ADMIN_KEY not in session:
            return redirect(url_for("admin.login"))
        return view(*args, **kwargs)

    return wrapper


def decide(entry_id: int, decision: str, comment: str | None, admin_id: int) -> VolunteerEntry:
    """Approve or reject a pending entry.

    Raises LookupError if the entry does not exist and ValueError if the decision is unknown
    or the entry is not pending. The ValueError message is a translation key.
    """
    if decision not in DECISIONS:
        raise ValueError("err.bad_decision")
    entry = db.session.get(VolunteerEntry, entry_id)
    if entry is None:
        raise LookupError(f"volunteer entry {entry_id} not found")
    if entry.status != "pending":
        raise ValueError("err.not_pending")
    entry.status = decision
    entry.admin_comment = (comment or "").strip() or None
    entry.decided_at = _utcnow()
    db.session.commit()
    return entry


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("admin_login.html", error=None)

    login_value = (request.form.get("login") or "").strip()
    password = request.form.get("password") or ""
    admin = db.session.scalar(select(Admin).where(Admin.login == login_value)) if login_value else None
    if admin is None or not bcrypt.checkpw(password.encode(), admin.password_hash.encode()):
        return render_template("admin_login.html", error=_("admin_login.bad"))

    # Keep the student session (if any) untouched; admin access is a separate key.
    session[ADMIN_KEY] = admin.id
    return redirect(url_for("admin.index"))


@bp.route("/logout")
def logout():
    session.pop(ADMIN_KEY, None)
    return redirect(url_for("admin.login"))


@bp.route("")
@admin_required
def index():
    class_name = (request.args.get("class") or "").strip()
    query = (
        select(VolunteerEntry, Student)
        .join(Student, VolunteerEntry.student_id == Student.id)
        .order_by(VolunteerEntry.date_start.desc(), VolunteerEntry.id.desc())
    )
    if class_name:
        query = query.where(Student.class_name == class_name)
    rows = db.session.execute(query).all()
    return render_template("admin.html", rows=rows, class_name=class_name)


@bp.route("/entries/<int:entry_id>/decide", methods=["POST"])
@admin_required
def decide_entry(entry_id: int):
    if db.session.get(VolunteerEntry, entry_id) is None:
        abort(404)
    try:
        decide(
            entry_id,
            request.form.get("decision", ""),
            request.form.get("comment"),
            session[ADMIN_KEY],
        )
    except ValueError as exc:
        flash(f"{_('flash.error')}: {_(str(exc))}")
    else:
        flash(_("flash.decision_saved"))
    class_name = (request.form.get("class") or "").strip()
    return redirect(url_for("admin.index", **({"class": class_name} if class_name else {})))

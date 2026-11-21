from datetime import date
from decimal import Decimal

from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for
from sqlalchemy import select

from app import db
from app.auth import student_required
from app.models import Student, VolunteerEntry
from app.validation import validate_entry

bp = Blueprint("student", __name__)

NOT_EDITABLE = "Эту запись нельзя изменить или удалить: изменять можно только записи на проверке."
NOT_EDITABLE_APPROVED = "Подтверждённую запись нельзя изменить или удалить."
TENTH = Decimal("0.1")


def _own_entry(entry_id: int) -> VolunteerEntry:
    """Fetch an entry only if it belongs to the logged-in student; otherwise 404."""
    entry = db.session.scalar(
        select(VolunteerEntry).where(
            VolunteerEntry.id == entry_id,
            VolunteerEntry.student_id == session["student_id"],
        )
    )
    if entry is None:
        abort(404)
    return entry


def _form_values(form) -> dict:
    return {
        "date_start": form.get("date_start", ""),
        "date_end": form.get("date_end", ""),
        "description": form.get("description", ""),
        "hours": form.get("hours", ""),
    }


def _not_editable_message(entry: VolunteerEntry) -> str:
    return NOT_EDITABLE_APPROVED if entry.status == "approved" else NOT_EDITABLE


@bp.route("/")
def index():
    if "student_id" in session:
        return redirect(url_for("student.cabinet"))
    return redirect(url_for("auth.login"))


@bp.route("/cabinet")
@student_required
def cabinet():
    entries = db.session.scalars(
        select(VolunteerEntry)
        .where(VolunteerEntry.student_id == session["student_id"])
        .order_by(VolunteerEntry.date_start.desc(), VolunteerEntry.id.desc())
    ).all()
    total_approved_hours = sum(
        (e.hours for e in entries if e.status == "approved"), Decimal("0")
    )
    return render_template(
        "cabinet.html",
        student=db.session.get(Student, session["student_id"]),
        entries=entries,
        total_approved_hours=total_approved_hours,
    )


@bp.route("/entries/new", methods=["GET", "POST"])
@student_required
def new_entry():
    today = date.today().isoformat()
    values = {"date_start": today, "date_end": today, "description": "", "hours": ""}
    errors: dict = {}
    if request.method == "POST":
        values = _form_values(request.form)
        cleaned, errors = validate_entry(
            values["date_start"], values["date_end"], values["description"], values["hours"], date.today()
        )
        if not errors:
            db.session.add(
                VolunteerEntry(
                    student_id=session["student_id"],
                    date_start=cleaned["date_start"],
                    date_end=cleaned["date_end"],
                    description=cleaned["description"],
                    hours=cleaned["hours"].quantize(TENTH),
                    status="pending",
                )
            )
            db.session.commit()
            flash("Запись добавлена и отправлена на проверку.")
            return redirect(url_for("student.cabinet"))
    return render_template(
        "entry_form.html",
        values=values,
        errors=errors,
        entry=None,
        action=url_for("student.new_entry"),
    )


@bp.route("/entries/<int:entry_id>/edit", methods=["GET", "POST"])
@student_required
def edit_entry(entry_id: int):
    entry = _own_entry(entry_id)
    if entry.status != "pending":
        flash(_not_editable_message(entry))
        return redirect(url_for("student.cabinet"))

    values = {
        "date_start": entry.date_start.isoformat(),
        "date_end": entry.date_end.isoformat(),
        "description": entry.description,
        "hours": str(entry.hours),
    }
    errors: dict = {}
    if request.method == "POST":
        values = _form_values(request.form)
        cleaned, errors = validate_entry(
            values["date_start"], values["date_end"], values["description"], values["hours"], date.today()
        )
        if not errors:
            entry.date_start = cleaned["date_start"]
            entry.date_end = cleaned["date_end"]
            entry.description = cleaned["description"]
            entry.hours = cleaned["hours"].quantize(TENTH)
            db.session.commit()
            flash("Запись обновлена.")
            return redirect(url_for("student.cabinet"))
    return render_template(
        "entry_form.html",
        values=values,
        errors=errors,
        entry=entry,
        action=url_for("student.edit_entry", entry_id=entry.id),
    )


@bp.route("/entries/<int:entry_id>/delete", methods=["POST"])
@student_required
def delete_entry(entry_id: int):
    entry = _own_entry(entry_id)
    if entry.status != "pending":
        flash(_not_editable_message(entry))
        return redirect(url_for("student.cabinet"))
    db.session.delete(entry)
    db.session.commit()
    flash("Запись удалена.")
    return redirect(url_for("student.cabinet"))

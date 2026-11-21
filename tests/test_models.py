from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app import db
from app.models import Student, VolunteerEntry


def test_create_student_and_pending_entry_defaults(app):
    student = Student(full_name="Test Student", class_name="10A", email="student@example.test")
    db.session.add(student)
    db.session.flush()

    entry = VolunteerEntry(
        student_id=student.id,
        date_start=date(2026, 11, 20),
        date_end=date(2026, 11, 20),
        description="Library helper",
        hours=Decimal("2.5"),
    )
    db.session.add(entry)
    db.session.commit()

    assert entry.id is not None
    assert entry.status == "pending"
    assert entry.admin_comment is None
    assert entry.decided_at is None
    assert entry.created_at is not None
    assert entry.hours == Decimal("2.5")


def test_student_email_is_unique(app):
    db.session.add(Student(full_name="First", class_name="10A", email="dup@example.test"))
    db.session.commit()

    db.session.add(Student(full_name="Second", class_name="11B", email="dup@example.test"))
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()

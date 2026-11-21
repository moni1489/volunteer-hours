from datetime import date
from decimal import Decimal
from unittest import mock

import pytest
from sqlalchemy import select

from app import db
from app.models import Student, VolunteerEntry


@pytest.fixture(autouse=True)
def mail():
    with mock.patch("app.mailer.send_code_email") as send, mock.patch(
        "app.mailer.smtplib.SMTP", side_effect=AssertionError("real SMTP must not be used in tests")
    ):
        yield send


@pytest.fixture
def student_a(app):
    s = Student(full_name="Ученик Аа", class_name="10A", email="a@example.com")
    db.session.add(s)
    db.session.commit()
    return s


@pytest.fixture
def student_b(app):
    s = Student(full_name="Ученик Бб", class_name="10B", email="b@example.com")
    db.session.add(s)
    db.session.commit()
    return s


def _entry(student, status="pending", hours="1.0", description="Тестовая запись"):
    e = VolunteerEntry(
        student_id=student.id,
        date=date(2026, 11, 1),
        description=description,
        hours=Decimal(hours),
        status=status,
    )
    db.session.add(e)
    db.session.commit()
    return e


def _login(client, student):
    with client.session_transaction() as sess:
        sess["student_id"] = student.id


def _valid_form(**overrides):
    data = {"date": "2026-11-20", "description": "Уборка двора", "hours": "2.5"}
    data.update(overrides)
    return data


def test_root_redirects_guest_to_login(client):
    resp = client.get("/")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/login")


def test_root_redirects_student_to_cabinet(client, student_a):
    _login(client, student_a)
    resp = client.get("/")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/cabinet")


def test_cabinet_requires_login(client):
    resp = client.get("/cabinet")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/login")


def test_cabinet_total_is_sum_of_approved_only(client, student_a):
    _entry(student_a, "approved", "2.5", "одобрено 1")
    _entry(student_a, "approved", "1.5", "одобрено 2")
    _entry(student_a, "pending", "4.0", "на проверке")
    _entry(student_a, "rejected", "3.0", "отклонено")
    _login(client, student_a)
    resp = client.get("/cabinet")
    assert resp.status_code == 200
    assert "4.0" in resp.get_data(as_text=True)
    assert "на проверке" in resp.get_data(as_text=True)


def test_cabinet_shows_only_own_entries(client, student_a, student_b):
    _entry(student_a, description="запись студента A")
    _entry(student_b, description="запись студента B")
    _login(client, student_a)
    body = client.get("/cabinet").get_data(as_text=True)
    assert "запись студента A" in body
    assert "запись студента B" not in body


def test_new_entry_is_created_pending_for_session_student(client, student_a):
    _login(client, student_a)
    resp = client.post("/entries/new", data=_valid_form())
    assert resp.status_code == 302
    entries = db.session.scalars(select(VolunteerEntry)).all()
    assert len(entries) == 1
    e = entries[0]
    assert e.student_id == student_a.id
    assert e.status == "pending"
    assert e.hours == Decimal("2.5")
    assert e.date == date(2026, 11, 20)


def test_new_entry_with_invalid_hours_is_not_saved(client, student_a):
    _login(client, student_a)
    resp = client.post("/entries/new", data=_valid_form(hours="13"))
    assert resp.status_code == 200
    assert db.session.scalars(select(VolunteerEntry)).all() == []


def test_student_cannot_see_others_entry_form(client, student_a, student_b):
    other = _entry(student_b)
    _login(client, student_a)
    assert client.get(f"/entries/{other.id}/edit").status_code == 404


def test_student_cannot_edit_others_entry(client, student_a, student_b):
    other = _entry(student_b, description="чужая")
    _login(client, student_a)
    resp = client.post(f"/entries/{other.id}/edit", data=_valid_form(description="взломано"))
    assert resp.status_code == 404
    db.session.refresh(other)
    assert other.description == "чужая"


def test_student_cannot_delete_others_entry(client, student_a, student_b):
    other = _entry(student_b)
    _login(client, student_a)
    resp = client.post(f"/entries/{other.id}/delete")
    assert resp.status_code == 404
    assert db.session.get(VolunteerEntry, other.id) is not None


def test_edit_pending_entry_works(client, student_a):
    e = _entry(student_a)
    _login(client, student_a)
    resp = client.post(f"/entries/{e.id}/edit", data=_valid_form(description="обновлено", hours="3"))
    assert resp.status_code == 302
    db.session.refresh(e)
    assert e.description == "обновлено"
    assert e.hours == Decimal("3")
    assert e.status == "pending"


def test_edit_approved_entry_is_refused_and_unchanged(client, student_a):
    e = _entry(student_a, "approved", "2.0", "подтверждено")
    _login(client, student_a)
    resp = client.post(f"/entries/{e.id}/edit", data=_valid_form(description="меняю", hours="5"), follow_redirects=True)
    assert "нельзя" in resp.get_data(as_text=True).lower()
    db.session.refresh(e)
    assert e.description == "подтверждено"
    assert e.hours == Decimal("2.0")
    assert e.status == "approved"


def test_delete_approved_entry_is_refused(client, student_a):
    e = _entry(student_a, "approved")
    _login(client, student_a)
    resp = client.post(f"/entries/{e.id}/delete", follow_redirects=True)
    assert "нельзя" in resp.get_data(as_text=True).lower()
    assert db.session.get(VolunteerEntry, e.id) is not None


def test_delete_pending_entry_works(client, student_a):
    e = _entry(student_a)
    _login(client, student_a)
    resp = client.post(f"/entries/{e.id}/delete")
    assert resp.status_code == 302
    assert db.session.get(VolunteerEntry, e.id) is None

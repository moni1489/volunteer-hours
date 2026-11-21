from datetime import date
from decimal import Decimal

import bcrypt
import pytest
from sqlalchemy import func, select

from app import create_app, db
from app.admin import decide
from app.bootstrap import ensure_admin
from app.models import Admin, Student, VolunteerEntry

ADMIN_LOGIN = "admin-test"
ADMIN_PASSWORD = "test-pass-123"


@pytest.fixture
def admin(app):
    ensure_admin(ADMIN_LOGIN, ADMIN_PASSWORD)
    return db.session.scalar(select(Admin).where(Admin.login == ADMIN_LOGIN))


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
        date_start=date(2026, 11, 1),
        date_end=date(2026, 11, 1),
        description=description,
        hours=Decimal(hours),
        status=status,
    )
    db.session.add(e)
    db.session.commit()
    return e


def _admin_login(client, login=ADMIN_LOGIN, password=ADMIN_PASSWORD):
    return client.post("/admin/login", data={"login": login, "password": password})


def _student_login(client, student):
    with client.session_transaction() as sess:
        sess["student_id"] = student.id


def test_wrong_admin_password_is_refused(client, admin):
    resp = _admin_login(client, password="wrong-password")

    assert resp.status_code == 200
    with client.session_transaction() as sess:
        assert "admin_id" not in sess
    assert client.get("/admin").status_code == 302


def test_correct_admin_password_opens_admin(client, admin):
    resp = _admin_login(client)

    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/admin")
    assert client.get("/admin").status_code == 200


def test_admin_page_forms_include_csrf_token(app, client, admin, student_a):
    _entry(student_a)
    _admin_login(client)

    html = client.get("/admin").get_data(as_text=True)

    assert 'name="csrf_token"' in html


def test_approve_sets_status_and_decided_at(client, admin, student_a):
    entry = _entry(student_a)
    _admin_login(client)

    resp = client.post(f"/admin/entries/{entry.id}/decide", data={"decision": "approved"})

    assert resp.status_code == 302
    db.session.refresh(entry)
    assert entry.status == "approved"
    assert entry.decided_at is not None


def test_reject_with_comment_stores_comment(client, admin, student_a):
    entry = _entry(student_a)
    _admin_login(client)

    client.post(
        f"/admin/entries/{entry.id}/decide",
        data={"decision": "rejected", "comment": "Не подтверждено координатором"},
    )

    db.session.refresh(entry)
    assert entry.status == "rejected"
    assert entry.admin_comment == "Не подтверждено координатором"
    assert entry.decided_at is not None


def test_deciding_non_pending_entry_raises_value_error(app, admin, student_a):
    entry = _entry(student_a, status="approved")

    with pytest.raises(ValueError):
        decide(entry.id, "rejected", None, admin.id)

    db.session.refresh(entry)
    assert entry.status == "approved"


def test_deciding_non_pending_entry_via_route_shows_error_not_500(client, admin, student_a):
    entry = _entry(student_a, status="approved")
    _admin_login(client)

    resp = client.post(f"/admin/entries/{entry.id}/decide", data={"decision": "rejected"}, follow_redirects=True)

    assert resp.status_code == 200
    assert "Ошибка" in resp.get_data(as_text=True)
    db.session.refresh(entry)
    assert entry.status == "approved"


def test_missing_entry_returns_404(client, admin):
    _admin_login(client)

    resp = client.post("/admin/entries/9999/decide", data={"decision": "approved"})

    assert resp.status_code == 404


def test_student_session_cannot_open_admin(client, admin, student_a):
    entry = _entry(student_a)
    _student_login(client, student_a)

    assert client.get("/admin").status_code == 302
    assert client.get("/admin").headers["Location"].endswith("/admin/login")
    client.post(f"/admin/entries/{entry.id}/decide", data={"decision": "approved"})

    db.session.refresh(entry)
    assert entry.status == "pending"


def test_admin_list_filters_by_class(client, admin, student_a, student_b):
    _entry(student_a, description="Работа класса А")
    _entry(student_b, description="Работа класса Б")
    _admin_login(client)

    html = client.get("/admin?class=10A").get_data(as_text=True)

    assert "Работа класса А" in html
    assert "Работа класса Б" not in html


def test_admin_list_shows_entry_period(client, admin, student_a):
    entry = _entry(student_a)
    entry.date_start = date(2026, 11, 3)
    entry.date_end = date(2026, 11, 7)
    db.session.commit()
    _admin_login(client)

    html = client.get("/admin").get_data(as_text=True)

    assert "03.11.2026 — 07.11.2026" in html


def test_ensure_admin_twice_does_not_duplicate(app):
    ensure_admin(ADMIN_LOGIN, ADMIN_PASSWORD)
    ensure_admin(ADMIN_LOGIN, "other-pass-456")

    count = db.session.scalar(select(func.count()).select_from(Admin).where(Admin.login == ADMIN_LOGIN))
    assert count == 1
    row = db.session.scalar(select(Admin).where(Admin.login == ADMIN_LOGIN))
    assert bcrypt.checkpw(b"other-pass-456", row.password_hash.encode())
    assert not bcrypt.checkpw(ADMIN_PASSWORD.encode(), row.password_hash.encode())


def test_ensure_admin_stores_bcrypt_hash_not_plaintext(app):
    ensure_admin(ADMIN_LOGIN, ADMIN_PASSWORD)

    row = db.session.scalar(select(Admin).where(Admin.login == ADMIN_LOGIN))
    assert row.password_hash != ADMIN_PASSWORD
    assert row.password_hash.startswith("$2")
    assert bcrypt.checkpw(ADMIN_PASSWORD.encode(), row.password_hash.encode())


def test_create_app_calls_ensure_admin_when_env_set(tmp_path):
    db_url = f"sqlite:///{(tmp_path / 'bootstrap.db').as_posix()}"
    first = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": db_url})
    with first.app_context():
        db.create_all()

    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": db_url,
            "ADMIN_LOGIN": ADMIN_LOGIN,
            "ADMIN_PASSWORD": ADMIN_PASSWORD,
        }
    )
    with app.app_context():
        row = db.session.scalar(select(Admin).where(Admin.login == ADMIN_LOGIN))
        assert row is not None
        assert bcrypt.checkpw(ADMIN_PASSWORD.encode(), row.password_hash.encode())
        db.session.remove()
        db.engine.dispose()

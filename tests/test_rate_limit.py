from datetime import timedelta

import pytest

from app import create_app, db
from app.auth import CODE_TTL, issue_code
from app.models import LoginCode, Student, _utcnow


@pytest.fixture
def app_with_student():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite://", "WTF_CSRF_ENABLED": False})
    with app.app_context():
        db.create_all()
        db.session.add(Student(full_name="Test Student One", class_name="10A", email="test1@example.com"))
        db.session.commit()
    return app


@pytest.fixture
def sent(monkeypatch):
    calls = []
    monkeypatch.setattr("app.mailer.send_code_email", lambda to, code: calls.append(to))
    return calls


def test_second_code_within_a_minute_is_not_sent(app_with_student, sent):
    with app_with_student.app_context():
        issue_code("test1@example.com")
        issue_code("test1@example.com")
    assert len(sent) == 1


def test_no_more_than_five_codes_per_hour(app_with_student, sent):
    with app_with_student.app_context():
        now = _utcnow()
        # Five codes issued 20 minutes ago: outside the 1-minute gap, inside the hour.
        for _ in range(5):
            db.session.add(LoginCode(email="test1@example.com", code_hash="x", expires_at=now - timedelta(minutes=20) + CODE_TTL, used=True))
        db.session.commit()
        issue_code("test1@example.com")
    assert sent == []


def test_code_allowed_again_after_the_hour(app_with_student, sent):
    with app_with_student.app_context():
        now = _utcnow()
        for _ in range(5):
            db.session.add(LoginCode(email="test1@example.com", code_hash="x", expires_at=now - timedelta(minutes=90) + CODE_TTL, used=True))
        db.session.commit()
        issue_code("test1@example.com")
    assert len(sent) == 1

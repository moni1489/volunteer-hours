from datetime import datetime, timedelta, timezone
from unittest import mock

import pytest
from sqlalchemy import select

from app import db
from app.auth import issue_code, verify_code
from app import mailer
from app.models import LoginCode, Student

# Captured before the autouse fixture swaps the mailer for a mock.
_real_send_code_email = mailer.send_code_email


@pytest.fixture(autouse=True)
def mail():
    """Mock the mailer in every test. Also make any real SMTP connection fail loudly."""
    with mock.patch("app.mailer.send_code_email") as send, mock.patch(
        "app.mailer.smtplib.SMTP", side_effect=AssertionError("real SMTP must not be used in tests")
    ):
        yield send


@pytest.fixture
def student(app):
    s = Student(full_name="Тестов Тест", class_name="10A", email="test1@example.com")
    db.session.add(s)
    db.session.commit()
    return s


def _codes(email="test1@example.com"):
    return db.session.scalars(select(LoginCode).where(LoginCode.email == email).order_by(LoginCode.id)).all()


def _sent_code(mail):
    assert mail.call_count == 1
    return mail.call_args[0][1]


def test_unknown_email_sends_no_mail(app, mail):
    issue_code("nobody@example.com")
    mail.assert_not_called()
    assert _codes("nobody@example.com") == []


def test_known_email_sends_one_mail_and_creates_login_code(app, student, mail):
    issue_code("test1@example.com")
    assert mail.call_count == 1
    to, code = mail.call_args[0]
    assert to == "test1@example.com"
    assert len(code) == 6 and code.isdigit()
    rows = _codes()
    assert len(rows) == 1
    assert rows[0].used is False
    assert rows[0].attempts == 0
    assert rows[0].code_hash != code


def test_new_code_invalidates_older_unused_codes(app, student, mail):
    issue_code("test1@example.com")
    first = _sent_code(mail)
    mail.reset_mock()
    issue_code("test1@example.com")
    second = _sent_code(mail)
    rows = _codes()
    assert [r.used for r in rows] == [True, False]
    assert verify_code("test1@example.com", first) is False
    assert verify_code("test1@example.com", second) is True


def test_wrong_code_increments_attempts(app, student, mail):
    issue_code("test1@example.com")
    code = _sent_code(mail)
    wrong = "000000" if code != "000000" else "111111"
    assert verify_code("test1@example.com", wrong) is False
    assert _codes()[0].attempts == 1


def test_sixth_attempt_is_refused_even_with_correct_code(app, student, mail):
    issue_code("test1@example.com")
    code = _sent_code(mail)
    wrong = "000000" if code != "000000" else "111111"
    for _ in range(5):
        assert verify_code("test1@example.com", wrong) is False
    assert _codes()[0].attempts == 5
    assert verify_code("test1@example.com", code) is False
    assert _codes()[0].used is False


def test_expired_code_is_refused(app, student, mail):
    issue_code("test1@example.com")
    code = _sent_code(mail)
    row = _codes()[0]
    row.expires_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=1)
    db.session.commit()
    assert verify_code("test1@example.com", code) is False


def test_correct_code_marks_used_and_reuse_fails(app, student, mail):
    issue_code("test1@example.com")
    code = _sent_code(mail)
    assert verify_code("test1@example.com", code) is True
    assert _codes()[0].used is True
    assert verify_code("test1@example.com", code) is False


def test_email_with_spaces_and_uppercase_matches_list(app, student, mail):
    issue_code("  Test1@Example.COM ")
    assert mail.call_count == 1
    assert mail.call_args[0][0] == "test1@example.com"
    code = mail.call_args[0][1]
    assert verify_code(" TEST1@example.com", code) is True


def test_login_flow_sets_student_id_in_session(client, student, mail):
    resp = client.post("/login", data={"email": "  TEST1@example.com "})
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/login/code")
    code = _sent_code(mail)

    resp = client.post("/login/code", data={"code": code})
    assert resp.status_code == 302
    with client.session_transaction() as sess:
        assert sess["student_id"] == student.id
    assert _codes()[0].used is True


def test_login_flow_rejects_reused_code(client, student, mail):
    client.post("/login", data={"email": "test1@example.com"})
    code = _sent_code(mail)
    client.post("/login/code", data={"code": code})
    client.get("/logout")
    client.post("/login", data={"email": "test1@example.com"})
    resp = client.post("/login/code", data={"code": code})
    assert resp.status_code == 200
    with client.session_transaction() as sess:
        assert "student_id" not in sess


def test_unknown_email_on_login_page_shows_message_and_sends_nothing(client, mail):
    resp = client.post("/login", data={"email": "nobody@example.com"})
    assert resp.status_code == 200
    assert "вас нет в списке, обратитесь к координатору".encode() in resp.data
    mail.assert_not_called()


def test_logout_clears_student_id(client, student, mail):
    client.post("/login", data={"email": "test1@example.com"})
    client.post("/login/code", data={"code": _sent_code(mail)})
    client.get("/logout")
    with client.session_transaction() as sess:
        assert "student_id" not in sess


def test_send_code_email_uses_starttls_and_config(app):
    app.config.update(SMTP_HOST="smtp.test.invalid", SMTP_PORT=587, SMTP_USER="sender@test.invalid", SMTP_PASSWORD="pw")
    smtp_cls = mock.MagicMock()
    with mock.patch("app.mailer.smtplib.SMTP", smtp_cls):
        with app.app_context():
            _real_send_code_email("test1@example.com", "123456")
    smtp_cls.assert_called_once()
    assert smtp_cls.call_args[0][:2] == ("smtp.test.invalid", 587)
    server = smtp_cls.return_value.__enter__.return_value
    server.starttls.assert_called_once()
    server.login.assert_called_once_with("sender@test.invalid", "pw")
    sent = server.send_message.call_args[0][0]
    assert sent["To"] == "test1@example.com"
    assert "123456" in sent.get_content()

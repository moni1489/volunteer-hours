import pytest

from app import create_app
from app.mailer import send_code_email


@pytest.fixture
def app_no_smtp():
    return create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite://", "WTF_CSRF_ENABLED": False, "SMTP_HOST": ""})


def test_no_smtp_raises_without_dev_flag(app_no_smtp, monkeypatch):
    monkeypatch.delenv("DEV_PRINT_CODES", raising=False)
    with app_no_smtp.app_context():
        with pytest.raises(RuntimeError):
            send_code_email("test1@example.com", "123456")


def test_dev_flag_prints_code_instead(app_no_smtp, monkeypatch, capsys):
    monkeypatch.setenv("DEV_PRINT_CODES", "1")
    with app_no_smtp.app_context():
        send_code_email("test1@example.com", "123456")
    assert "123456" in capsys.readouterr().out

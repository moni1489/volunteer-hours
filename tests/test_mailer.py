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


def test_brevo_api_used_when_key_set(monkeypatch):
    monkeypatch.setenv("BREVO_API_KEY", "fake-key")
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite://", "WTF_CSRF_ENABLED": False, "SMTP_HOST": "smtp.gmail.com"})
    sent = {}

    class FakeResp:
        status = 201
        def __enter__(self): return self
        def __exit__(self, *a): return False

    def fake_urlopen(req, timeout=None):
        sent["url"] = req.full_url
        sent["key"] = req.get_header("Api-key")
        sent["body"] = req.data.decode("utf-8")
        return FakeResp()

    monkeypatch.setattr("app.mailer.urllib.request.urlopen", fake_urlopen)
    with app.app_context():
        send_code_email("test1@example.com", "654321")
    assert sent["url"] == "https://api.brevo.com/v3/smtp/email"
    assert sent["key"] == "fake-key"
    assert "654321" in sent["body"] and "test1@example.com" in sent["body"]

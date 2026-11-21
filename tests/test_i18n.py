import json
from string import Formatter
from unittest import mock
from urllib.parse import urlsplit

import pytest
from flask import session

from app import db
from app.i18n import TRANSLATIONS, translate
from app.mailer import send_code_email
from app.models import Student


@pytest.fixture(autouse=True)
def mail():
    with mock.patch("app.mailer.send_code_email") as send:
        yield send


def _fields(text):
    return {name for _, name, _, _ in Formatter().parse(text) if name}


def test_default_page_is_russian(client):
    body = client.get("/login").get_data(as_text=True)
    assert "Вход ученика" in body
    assert 'lang="ru"' in body


def test_kazakh_after_switch(client):
    resp = client.get("/lang/kk")
    assert resp.status_code == 302
    body = client.get("/login").get_data(as_text=True)
    assert "Оқушы кіруі" in body
    assert 'lang="kk"' in body


def test_unknown_language_code_falls_back_to_russian(client):
    client.get("/lang/kk")
    client.get("/lang/xx")
    body = client.get("/login").get_data(as_text=True)
    assert "Вход ученика" in body
    assert 'lang="ru"' in body


def test_open_redirect_is_refused(client):
    resp = client.get("/lang/kk", headers={"Referer": "https://evil.example"})
    assert resp.status_code == 302
    location = urlsplit(resp.headers["Location"])
    assert location.netloc in ("", "localhost")
    assert location.path == "/"


def test_same_host_referer_with_double_slash_path_is_refused(client):
    resp = client.get("/lang/kk", headers={"Referer": "http://localhost//evil.example"})
    location = urlsplit(resp.headers["Location"])
    assert location.netloc in ("", "localhost")
    assert location.path == "/"


def test_same_host_referer_is_followed(client):
    resp = client.get("/lang/kk", headers={"Referer": "http://localhost/login"})
    assert urlsplit(resp.headers["Location"]).path == "/login"


def test_translate_returns_key_outside_request(app):
    with app.app_context():
        assert translate("login.title") == "login.title"


def test_every_russian_key_has_kazakh_with_same_placeholders():
    ru, kk = TRANSLATIONS["ru"], TRANSLATIONS["kk"]
    assert set(ru) == set(kk)
    for key, text in ru.items():
        assert _fields(text) == _fields(kk[key]), key


def test_email_follows_session_language(app, monkeypatch):
    monkeypatch.setenv("BREVO_API_KEY", "fake-key")
    sent = {}

    class FakeResp:
        status = 201

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def fake_urlopen(req, timeout=None):
        sent.update(json.loads(req.data.decode("utf-8")))
        return FakeResp()

    monkeypatch.setattr("app.mailer.urllib.request.urlopen", fake_urlopen)
    with app.test_request_context("/"):
        session["lang"] = "kk"
        send_code_email("test1@example.com", "654321")
    assert sent["subject"] == TRANSLATIONS["kk"]["mail.subject"]
    assert sent["textContent"].startswith("Сіздің кіру кодыңыз")
    assert "654321" in sent["textContent"]

    with app.app_context():
        send_code_email("test1@example.com", "111222")
    assert sent["subject"] == TRANSLATIONS["ru"]["mail.subject"]
    assert "111222" in sent["textContent"]


def test_language_survives_login(client, app, mail):
    db.session.add(Student(full_name="Тестов Тест", class_name="10A", email="test1@example.com"))
    db.session.commit()
    client.get("/lang/kk")
    client.post("/login", data={"email": "test1@example.com"})
    client.post("/login/code", data={"code": mail.call_args[0][1]})
    with client.session_transaction() as sess:
        assert sess["student_id"] is not None
        assert sess["lang"] == "kk"

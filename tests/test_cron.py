from datetime import timedelta

import pytest

from app import create_app, db
from app.models import LoginCode, _utcnow


@pytest.fixture
def cron_app(monkeypatch):
    monkeypatch.setenv("CRON_SECRET", "test-cron-secret")
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite://", "WTF_CSRF_ENABLED": False})
    with app.app_context():
        db.create_all()
        now = _utcnow()
        db.session.add_all([
            LoginCode(email="test1@example.com", code_hash="x", expires_at=now + timedelta(minutes=5), used=False),
            LoginCode(email="test2@example.com", code_hash="x", expires_at=now - timedelta(minutes=5), used=False),
            LoginCode(email="test3@example.com", code_hash="x", expires_at=now + timedelta(minutes=5), used=True),
        ])
        db.session.commit()
    return app


def test_disabled_without_secret(monkeypatch):
    monkeypatch.delenv("CRON_SECRET", raising=False)
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite://"})
    assert app.test_client().post("/internal/cleanup-login-codes").status_code == 404


def test_rejects_missing_or_wrong_token(cron_app):
    client = cron_app.test_client()
    assert client.post("/internal/cleanup-login-codes").status_code == 401
    bad = {"Authorization": "Bearer wrong"}
    assert client.post("/internal/cleanup-login-codes", headers=bad).status_code == 401


def test_cleanup_deletes_expired_and_used_only(cron_app):
    client = cron_app.test_client()
    good = {"Authorization": "Bearer test-cron-secret"}
    resp = client.post("/internal/cleanup-login-codes", headers=good)
    assert resp.status_code == 200
    assert resp.get_json() == {"deleted": 2}
    with cron_app.app_context():
        remaining = db.session.scalars(db.select(LoginCode.email)).all()
        assert remaining == ["test1@example.com"]

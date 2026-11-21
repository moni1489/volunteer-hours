import pytest

from app import create_app
from app.config import DEV_SECRET_KEY, _database_url


def test_create_app_returns_flask_app_with_testing_flag():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite://"})
    assert app is not None
    assert app.config["TESTING"] is True


def test_create_app_refuses_placeholder_secret_outside_testing():
    with pytest.raises(RuntimeError):
        create_app({"TESTING": False, "SECRET_KEY": DEV_SECRET_KEY})


def test_postgres_url_is_rewritten_to_psycopg(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgres://u:p@h/db")
    assert _database_url() == "postgresql+psycopg://u:p@h/db"


def test_database_url_defaults_to_sqlite_dev_db(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert _database_url() == "sqlite:///dev.db"

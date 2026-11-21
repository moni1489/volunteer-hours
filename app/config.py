import os


def _database_url() -> str:
    url = os.environ.get("DATABASE_URL", "sqlite:///dev.db")
    # Render provides postgres:// URLs; SQLAlchemy needs the psycopg driver prefix.
    if url.startswith("postgres://"):
        url = "postgresql+psycopg://" + url[len("postgres://"):]
    return url


class Config:
    SQLALCHEMY_DATABASE_URI = _database_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-not-for-production")
    SMTP_HOST = os.environ.get("SMTP_HOST", "")
    SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
    SMTP_USER = os.environ.get("SMTP_USER", "")
    SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
    ADMIN_LOGIN = os.environ.get("ADMIN_LOGIN", "")
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")

from flask import Flask
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

from app.config import DEV_SECRET_KEY, Config

db = SQLAlchemy()
migrate = Migrate()


def create_app(config: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)
    if config:
        app.config.update(config)
    if not app.config["TESTING"] and app.config["SECRET_KEY"] == DEV_SECRET_KEY:
        raise RuntimeError("SECRET_KEY must be set in the environment outside TESTING mode")
    db.init_app(app)
    migrate.init_app(app, db)
    from app.cli import register_commands

    register_commands(app)
    return app


# Register models on db.metadata so Flask-Migrate autogenerate sees them.
from app import models  # noqa: E402,F401

from flask import Flask
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

from app.config import DEV_SECRET_KEY, Config

db = SQLAlchemy()
migrate = Migrate()


def create_app(config: dict | None = None) -> Flask:
    # Templates live in the project-root templates/ folder, one level above this package.
    app = Flask(__name__, template_folder="../templates")
    app.config.from_object(Config)
    if config:
        app.config.update(config)
    if not app.config["TESTING"] and app.config["SECRET_KEY"] == DEV_SECRET_KEY:
        raise RuntimeError("SECRET_KEY must be set in the environment outside TESTING mode")
    db.init_app(app)
    migrate.init_app(app, db)
    from app.cli import register_commands
    from app.auth import bp as auth_bp

    register_commands(app)
    app.register_blueprint(auth_bp)
    return app


# Register models on db.metadata so Flask-Migrate autogenerate sees them.
from app import models  # noqa: E402,F401

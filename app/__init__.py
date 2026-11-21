from flask import Flask
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from flask_sqlalchemy import SQLAlchemy

from app.config import DEV_SECRET_KEY, Config

db = SQLAlchemy()
migrate = Migrate()
csrf = CSRFProtect()


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
    csrf.init_app(app)
    from app.cli import register_commands
    from app.admin import bp as admin_bp
    from app.auth import bp as auth_bp
    from app.cron import bp as cron_bp
    from app.student import bp as student_bp

    from app.i18n import bp as i18n_bp, translate

    app.jinja_env.globals["_"] = translate
    register_commands(app)
    app.register_blueprint(i18n_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(cron_bp)

    admin_login = app.config.get("ADMIN_LOGIN")
    admin_password = app.config.get("ADMIN_PASSWORD")
    if admin_login and admin_password:
        from sqlalchemy import inspect

        from app.bootstrap import ensure_admin
        from app.models import Admin

        with app.app_context():
            # Skip before migrations have created the table, so `flask db upgrade` still works.
            if inspect(db.engine).has_table(Admin.__tablename__):
                ensure_admin(admin_login, admin_password)
    return app


# Register models on db.metadata so Flask-Migrate autogenerate sees them.
from app import models  # noqa: E402,F401

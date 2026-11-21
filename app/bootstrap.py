import bcrypt
from sqlalchemy import select

from app import db
from app.models import Admin


def ensure_admin(login: str, password: str) -> None:
    """Create the admin row for `login`, or update its password hash if it already exists.

    Only a bcrypt hash is stored. Call inside an app context.
    """
    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    admin = db.session.scalar(select(Admin).where(Admin.login == login))
    if admin is None:
        db.session.add(Admin(login=login, password_hash=password_hash))
    else:
        admin.password_hash = password_hash
    db.session.commit()

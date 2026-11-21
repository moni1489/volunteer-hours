import hmac
import os

from flask import Blueprint, abort, jsonify, request
from sqlalchemy import delete, or_

from app import csrf, db
from app.models import LoginCode, _utcnow

bp = Blueprint("cron", __name__, url_prefix="/internal")
csrf.exempt(bp)


@bp.before_request
def require_cron_token():
    # Disabled entirely when CRON_SECRET is not set.
    secret = os.environ.get("CRON_SECRET", "")
    if not secret:
        abort(404)
    header = request.headers.get("Authorization", "")
    expected = f"Bearer {secret}"
    if not hmac.compare_digest(header, expected):
        abort(401)


@bp.post("/cleanup-login-codes")
def cleanup_login_codes():
    """Delete login codes that are used or expired. Call from a Render cron job."""
    result = db.session.execute(
        delete(LoginCode).where(or_(LoginCode.used.is_(True), LoginCode.expires_at <= _utcnow()))
    )
    db.session.commit()
    return jsonify(deleted=result.rowcount)

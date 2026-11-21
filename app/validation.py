from datetime import date
from decimal import Decimal, InvalidOperation

from app.i18n import translate as _

MAX_DESCRIPTION = 500
MIN_HOURS = Decimal("0.5")
HOURS_STEP = Decimal("0.5")


def _parse_hours(hours_str: str) -> Decimal | None:
    try:
        hours = Decimal((hours_str or "").strip())
    except InvalidOperation:
        return None
    if not hours.is_finite():
        return None
    if hours < MIN_HOURS:
        return None
    if (hours / HOURS_STEP) != (hours / HOURS_STEP).to_integral_value():
        return None
    return hours


def _parse_date(date_str: str) -> date | None:
    try:
        return date.fromisoformat((date_str or "").strip())
    except ValueError:
        return None


def validate_entry(
    date_start_str: str, date_end_str: str, description: str, hours_str: str, today: date
) -> tuple[dict, dict]:
    """Validate a volunteer entry form. Returns (cleaned, errors); errors maps field name to message."""
    cleaned: dict = {}
    errors: dict = {}

    date_start = _parse_date(date_start_str)
    if date_start is None or date_start > today:
        errors["date_start"] = _("val.date")
    else:
        cleaned["date_start"] = date_start

    date_end = _parse_date(date_end_str)
    if date_end is None or date_end > today:
        errors["date_end"] = _("val.date")
    else:
        cleaned["date_end"] = date_end

    if "date_start" in cleaned and "date_end" in cleaned and cleaned["date_start"] > cleaned["date_end"]:
        errors["date_end"] = _("val.period")
        del cleaned["date_end"]

    text = (description or "").strip()
    if not text or len(text) > MAX_DESCRIPTION:
        errors["description"] = _("val.description", max=MAX_DESCRIPTION)
    else:
        cleaned["description"] = text

    hours = _parse_hours(hours_str)
    if hours is None:
        errors["hours"] = _("val.hours")
    else:
        cleaned["hours"] = hours

    return cleaned, errors

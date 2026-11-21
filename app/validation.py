from datetime import date
from decimal import Decimal, InvalidOperation

MAX_DESCRIPTION = 500
MIN_HOURS = Decimal("0.5")
MAX_HOURS = Decimal("12.0")
HOURS_STEP = Decimal("0.5")

DATE_ERROR = "Укажите дату не позже сегодняшней."
DESCRIPTION_ERROR = f"Опишите работу (не более {MAX_DESCRIPTION} символов)."
HOURS_ERROR = "Часы: от 0.5 до 12, с шагом 0.5."


def _parse_hours(hours_str: str) -> Decimal | None:
    try:
        hours = Decimal((hours_str or "").strip())
    except InvalidOperation:
        return None
    if not hours.is_finite():
        return None
    if not (MIN_HOURS <= hours <= MAX_HOURS):
        return None
    if (hours / HOURS_STEP) != (hours / HOURS_STEP).to_integral_value():
        return None
    return hours


def validate_entry(date_str: str, description: str, hours_str: str, today: date) -> tuple[dict, dict]:
    """Validate a volunteer entry form. Returns (cleaned, errors); errors maps field name to message."""
    cleaned: dict = {}
    errors: dict = {}

    try:
        entry_date = date.fromisoformat((date_str or "").strip())
    except ValueError:
        entry_date = None
    if entry_date is None or entry_date > today:
        errors["date"] = DATE_ERROR
    else:
        cleaned["date"] = entry_date

    text = (description or "").strip()
    if not text or len(text) > MAX_DESCRIPTION:
        errors["description"] = DESCRIPTION_ERROR
    else:
        cleaned["description"] = text

    hours = _parse_hours(hours_str)
    if hours is None:
        errors["hours"] = HOURS_ERROR
    else:
        cleaned["hours"] = hours

    return cleaned, errors

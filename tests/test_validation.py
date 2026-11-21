from datetime import date
from decimal import Decimal

import pytest

from app.validation import validate_entry

TODAY = date(2026, 11, 21)
GOOD_DESC = "Помощь в библиотеке"


@pytest.mark.parametrize("hours", ["0", "0.3", "13", "2.25", "12.5", "-1", "abc", "", "NaN", "Infinity"])
def test_rejects_invalid_hours(hours):
    cleaned, errors = validate_entry("2026-11-20", GOOD_DESC, hours, TODAY)
    assert "hours" in errors
    assert "hours" not in cleaned


@pytest.mark.parametrize("hours, expected", [("0.5", Decimal("0.5")), ("12", Decimal("12.0")), (" 1.5 ", Decimal("1.5"))])
def test_accepts_valid_hours(hours, expected):
    cleaned, errors = validate_entry("2026-11-20", GOOD_DESC, hours, TODAY)
    assert errors == {}
    assert cleaned["hours"] == expected
    assert isinstance(cleaned["hours"], Decimal)


def test_rejects_future_date():
    _, errors = validate_entry("2026-11-22", GOOD_DESC, "1", TODAY)
    assert "date" in errors


def test_accepts_today():
    cleaned, errors = validate_entry("2026-11-21", GOOD_DESC, "1", TODAY)
    assert errors == {}
    assert cleaned["date"] == TODAY


@pytest.mark.parametrize("date_str", ["", "not-a-date", "2026-13-01"])
def test_rejects_bad_date(date_str):
    _, errors = validate_entry(date_str, GOOD_DESC, "1", TODAY)
    assert "date" in errors


@pytest.mark.parametrize("description", ["", "   "])
def test_rejects_empty_description(description):
    _, errors = validate_entry("2026-11-20", description, "1", TODAY)
    assert "description" in errors


def test_description_limit_500_chars():
    _, errors = validate_entry("2026-11-20", "а" * 500, "1", TODAY)
    assert errors == {}
    _, errors = validate_entry("2026-11-20", "а" * 501, "1", TODAY)
    assert "description" in errors


def test_description_is_stripped():
    cleaned, _ = validate_entry("2026-11-20", "  текст  ", "1", TODAY)
    assert cleaned["description"] == "текст"

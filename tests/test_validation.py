from datetime import date
from decimal import Decimal

import pytest

from app.validation import validate_entry

TODAY = date(2026, 11, 21)
GOOD_DESC = "Помощь в библиотеке"


@pytest.mark.parametrize("hours", ["0", "0.3", "2.25", "-1", "abc", "", "NaN", "Infinity"])
def test_rejects_invalid_hours(hours):
    cleaned, errors = validate_entry("2026-11-20", "2026-11-20", GOOD_DESC, hours, TODAY)
    assert "hours" in errors
    assert "hours" not in cleaned


@pytest.mark.parametrize("hours, expected", [("0.5", Decimal("0.5")), ("12", Decimal("12.0")), ("200", Decimal("200.0")), ("1000", Decimal("1000.0")), (" 1.5 ", Decimal("1.5"))])
def test_accepts_valid_hours(hours, expected):
    cleaned, errors = validate_entry("2026-11-20", "2026-11-20", GOOD_DESC, hours, TODAY)
    assert errors == {}
    assert cleaned["hours"] == expected
    assert isinstance(cleaned["hours"], Decimal)


def test_rejects_future_date():
    _, errors = validate_entry("2026-11-22", "2026-11-22", GOOD_DESC, "1", TODAY)
    assert "date_start" in errors
    assert "date_end" in errors


def test_rejects_future_end_date():
    _, errors = validate_entry("2026-11-20", "2026-11-22", GOOD_DESC, "1", TODAY)
    assert "date_end" in errors
    assert "date_start" not in errors


def test_rejects_start_after_end():
    cleaned, errors = validate_entry("2026-11-20", "2026-11-19", GOOD_DESC, "1", TODAY)
    assert "date_end" in errors
    assert "date_end" not in cleaned


def test_accepts_one_day_period():
    cleaned, errors = validate_entry("2026-11-20", "2026-11-20", GOOD_DESC, "1", TODAY)
    assert errors == {}
    assert cleaned["date_start"] == cleaned["date_end"] == date(2026, 11, 20)


def test_accepts_multi_day_period():
    cleaned, errors = validate_entry("2026-11-10", "2026-11-20", GOOD_DESC, "1", TODAY)
    assert errors == {}
    assert cleaned["date_start"] == date(2026, 11, 10)
    assert cleaned["date_end"] == date(2026, 11, 20)


def test_accepts_today():
    cleaned, errors = validate_entry("2026-11-21", "2026-11-21", GOOD_DESC, "1", TODAY)
    assert errors == {}
    assert cleaned["date_start"] == TODAY
    assert cleaned["date_end"] == TODAY


@pytest.mark.parametrize("date_str", ["", "not-a-date", "2026-13-01"])
def test_rejects_bad_start_date(date_str):
    _, errors = validate_entry(date_str, "2026-11-20", GOOD_DESC, "1", TODAY)
    assert "date_start" in errors


@pytest.mark.parametrize("date_str", ["", "not-a-date", "2026-13-01"])
def test_rejects_bad_end_date(date_str):
    _, errors = validate_entry("2026-11-20", date_str, GOOD_DESC, "1", TODAY)
    assert "date_end" in errors


@pytest.mark.parametrize("description", ["", "   "])
def test_rejects_empty_description(description):
    _, errors = validate_entry("2026-11-20", "2026-11-20", description, "1", TODAY)
    assert "description" in errors


def test_description_limit_500_chars():
    _, errors = validate_entry("2026-11-20", "2026-11-20", "а" * 500, "1", TODAY)
    assert errors == {}
    _, errors = validate_entry("2026-11-20", "2026-11-20", "а" * 501, "1", TODAY)
    assert "description" in errors


def test_description_is_stripped():
    cleaned, _ = validate_entry("2026-11-20", "2026-11-20", "  текст  ", "1", TODAY)
    assert cleaned["description"] == "текст"

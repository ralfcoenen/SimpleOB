"""Tests für das Domänenobjekt FiscalYear."""

from dataclasses import FrozenInstanceError
from datetime import date

import pytest

from openbilanz.domain import FiscalYear


def test_fiscal_year_accepts_calendar_year() -> None:
    fiscal_year = FiscalYear(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )

    assert fiscal_year.start_date == date(2026, 1, 1)
    assert fiscal_year.end_date == date(2026, 12, 31)


def test_fiscal_year_accepts_non_calendar_year() -> None:
    fiscal_year = FiscalYear(
        start_date=date(2026, 7, 1),
        end_date=date(2027, 6, 30),
    )

    assert fiscal_year.start_date == date(2026, 7, 1)
    assert fiscal_year.end_date == date(2027, 6, 30)


@pytest.mark.parametrize(
    "value",
    [
        date(2026, 1, 1),
        date(2026, 6, 15),
        date(2026, 12, 31),
    ],
)
def test_contains_returns_true_for_dates_inside_fiscal_year(
    value: date,
) -> None:
    fiscal_year = FiscalYear(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )

    assert fiscal_year.contains(value)


@pytest.mark.parametrize(
    "value",
    [
        date(2025, 12, 31),
        date(2027, 1, 1),
    ],
)
def test_contains_returns_false_for_dates_outside_fiscal_year(
    value: date,
) -> None:
    fiscal_year = FiscalYear(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )

    assert not fiscal_year.contains(value)


def test_contains_rejects_invalid_type() -> None:
    fiscal_year = FiscalYear(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )

    with pytest.raises(TypeError, match="date"):
        fiscal_year.contains("2026-06-15")  # type: ignore[arg-type]


def test_duration_days_for_calendar_year() -> None:
    fiscal_year = FiscalYear(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )

    assert fiscal_year.duration_days == 365


def test_duration_days_includes_start_and_end_date() -> None:
    fiscal_year = FiscalYear(
        start_date=date(2026, 5, 10),
        end_date=date(2026, 5, 10),
    )

    assert fiscal_year.duration_days == 1


def test_duration_days_for_leap_year() -> None:
    fiscal_year = FiscalYear(
        start_date=date(2024, 1, 1),
        end_date=date(2024, 12, 31),
    )

    assert fiscal_year.duration_days == 366


def test_calendar_years_for_single_calendar_year() -> None:
    fiscal_year = FiscalYear(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )

    assert fiscal_year.calendar_years == (2026,)


def test_calendar_years_for_non_calendar_year() -> None:
    fiscal_year = FiscalYear(
        start_date=date(2026, 7, 1),
        end_date=date(2027, 6, 30),
    )

    assert fiscal_year.calendar_years == (2026, 2027)


def test_calendar_years_for_multi_year_period() -> None:
    fiscal_year = FiscalYear(
        start_date=date(2025, 12, 1),
        end_date=date(2027, 1, 31),
    )

    assert fiscal_year.calendar_years == (2025, 2026, 2027)


def test_start_date_after_end_date_is_rejected() -> None:
    with pytest.raises(ValueError, match="start_date"):
        FiscalYear(
            start_date=date(2026, 12, 31),
            end_date=date(2026, 1, 1),
        )


@pytest.mark.parametrize(
    ("start_date", "end_date"),
    [
        ("2026-01-01", date(2026, 12, 31)),
        (date(2026, 1, 1), "2026-12-31"),
        (2026, date(2026, 12, 31)),
        (date(2026, 1, 1), None),
    ],
)
def test_invalid_date_types_are_rejected(
    start_date: object,
    end_date: object,
) -> None:
    with pytest.raises(TypeError, match="date"):
        FiscalYear(
            start_date=start_date,  # type: ignore[arg-type]
            end_date=end_date,  # type: ignore[arg-type]
        )


def test_fiscal_year_is_immutable() -> None:
    fiscal_year = FiscalYear(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )

    with pytest.raises(FrozenInstanceError):
        fiscal_year.start_date = date(2025, 1, 1)  # type: ignore[misc]


def test_equal_fiscal_years_are_equal() -> None:
    first = FiscalYear(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )
    second = FiscalYear(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )

    assert first == second


def test_fiscal_year_is_hashable() -> None:
    fiscal_year = FiscalYear(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )

    assert {fiscal_year} == {fiscal_year}
    
def test_display_name() -> None:
    fiscal_year = FiscalYear(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )

    assert (
        fiscal_year.display_name
        == "01.01.2026 – 31.12.2026"
    )


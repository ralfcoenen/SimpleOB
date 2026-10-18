"""Tests für verwaltete Geschäftsjahre."""

from datetime import date

import pytest

from simpleob.domain.fiscal_year import FiscalYear
from simpleob.domain.fiscal_year_status import FiscalYearStatus
from simpleob.domain.managed_fiscal_year import ManagedFiscalYear


def test_managed_fiscal_year_contains_period_and_status() -> None:
    fiscal_year = FiscalYear(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )

    managed = ManagedFiscalYear(
        fiscal_year=fiscal_year,
        status=FiscalYearStatus.OPEN,
    )

    assert managed.fiscal_year is fiscal_year
    assert managed.status is FiscalYearStatus.OPEN
    assert managed.is_open
    assert not managed.is_closed


def test_closed_managed_fiscal_year_is_closed() -> None:
    managed = ManagedFiscalYear(
        fiscal_year=FiscalYear(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        ),
        status=FiscalYearStatus.CLOSED,
    )

    assert managed.is_closed
    assert not managed.is_open


def test_managed_fiscal_year_requires_fiscal_year() -> None:
    with pytest.raises(TypeError):
        ManagedFiscalYear(
            fiscal_year=2026,  # type: ignore[arg-type]
            status=FiscalYearStatus.OPEN,
        )


def test_managed_fiscal_year_requires_status() -> None:
    with pytest.raises(TypeError):
        ManagedFiscalYear(
            fiscal_year=FiscalYear(
                start_date=date(2026, 1, 1),
                end_date=date(2026, 12, 31),
            ),
            status="OPEN",  # type: ignore[arg-type]
        )

def test_managed_fiscal_year_has_no_opening_source_by_default() -> None:
    managed = ManagedFiscalYear(
        fiscal_year=FiscalYear(
            start_date=date(2027, 1, 1),
            end_date=date(2027, 12, 31),
        ),
        status=FiscalYearStatus.OPEN,
    )

    assert managed.opening_source is None
    assert not managed.has_opening_source


def test_managed_fiscal_year_can_have_opening_source() -> None:
    source = FiscalYear(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )

    managed = ManagedFiscalYear(
        fiscal_year=FiscalYear(
            start_date=date(2027, 1, 1),
            end_date=date(2027, 12, 31),
        ),
        status=FiscalYearStatus.OPEN,
        opening_source=source,
    )

    assert managed.opening_source == source
    assert managed.has_opening_source


def test_managed_fiscal_year_rejects_invalid_opening_source() -> None:
    with pytest.raises(TypeError):
        ManagedFiscalYear(
            fiscal_year=FiscalYear(
                start_date=date(2027, 1, 1),
                end_date=date(2027, 12, 31),
            ),
            status=FiscalYearStatus.OPEN,
            opening_source=2026,  # type: ignore[arg-type]
        )

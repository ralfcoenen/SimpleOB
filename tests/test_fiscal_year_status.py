"""Tests für den Status eines Geschäftsjahres."""

import pytest

from openbilanz.domain.fiscal_year_status import FiscalYearStatus


def test_fiscal_year_status_contains_open_and_closed() -> None:
    """Die zulässigen Geschäftsjahresstatus sind definiert."""

    assert FiscalYearStatus.OPEN.value == "OPEN"
    assert FiscalYearStatus.CLOSED.value == "CLOSED"


def test_fiscal_year_status_can_be_created_from_value() -> None:
    """Ein Status kann aus seinem Persistenzwert erzeugt werden."""

    assert FiscalYearStatus("OPEN") is FiscalYearStatus.OPEN
    assert FiscalYearStatus("CLOSED") is FiscalYearStatus.CLOSED


def test_fiscal_year_status_rejects_unknown_value() -> None:
    """Unbekannte Statuswerte sind unzulässig."""

    with pytest.raises(ValueError):
        FiscalYearStatus("FINISHED")
        

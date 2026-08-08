"""Tests für den Anwendungskontext."""

from datetime import date
from uuid import uuid4

import pytest

from openbilanz.core.context import ApplicationContext
from openbilanz.domain.company import Company
from openbilanz.domain.fiscal_year import FiscalYear


def test_application_context_contains_company_and_fiscal_year() -> None:
    """Der Kontext hält Unternehmen und Geschäftsjahr."""

    company = Company(
        company_id=uuid4(),
        name="Muster UG",
    )
    fiscal_year = FiscalYear(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )

    context = ApplicationContext(
        company=company,
        fiscal_year=fiscal_year,
    )

    assert context.company is company
    assert context.fiscal_year is fiscal_year


def test_application_context_requires_company() -> None:
    """Der Kontext akzeptiert nur ein Company-Objekt."""

    fiscal_year = FiscalYear(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )

    with pytest.raises(TypeError):
        ApplicationContext(
            company="Muster UG",  # type: ignore[arg-type]
            fiscal_year=fiscal_year,
        )


def test_application_context_requires_fiscal_year() -> None:
    """Der Kontext akzeptiert nur ein FiscalYear-Objekt."""

    company = Company(
        company_id=uuid4(),
        name="Muster UG",
    )

    with pytest.raises(TypeError):
        ApplicationContext(
            company=company,
            fiscal_year=2026,  # type: ignore[arg-type]
        )

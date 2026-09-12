"""Tests für jahresbezogene BVV-Daten."""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from openbilanz.database.bvv_annual_data_repository import (
    BvvAnnualDataRepository,
)
from openbilanz.database.company_repository import (
    CompanyRepository,
)
from openbilanz.database.database import Base
from openbilanz.domain.bvv_annual_data import (
    BvvAnnualData,
)
from openbilanz.domain.company import Company
from openbilanz.domain.fiscal_year import FiscalYear


@pytest.fixture
def session():
    """Erzeugt eine leere Testdatenbank."""

    engine = create_engine(
        "sqlite:///:memory:"
    )

    Base.metadata.create_all(engine)

    Session = sessionmaker(
        bind=engine
    )

    with Session() as session:
        yield session

    engine.dispose()


def test_saves_loads_and_updates_bvv_annual_data(
    session,
) -> None:
    """BVV-Jahresdaten können gespeichert und aktualisiert werden."""

    company = Company(
        company_id=uuid4(),
        name="Muster UG",
    )

    fiscal_year = FiscalYear(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )

    company_repository = CompanyRepository(
        session
    )

    company_repository.add(
        company
    )

    company_repository.add_fiscal_year(
        company.company_id,
        fiscal_year,
    )

    repository = BvvAnnualDataRepository(
        session
    )

    initial_data = BvvAnnualData(
        previous_hgb_equity=Decimal("13868.35"),
        contribution=Decimal("0.00"),
        withdrawal_distribution=Decimal("0.00"),
    )

    repository.save_for_fiscal_year(
        company_id=company.company_id,
        fiscal_year=fiscal_year,
        data=initial_data,
    )

    loaded = repository.get_for_fiscal_year(
        company_id=company.company_id,
        fiscal_year=fiscal_year,
    )

    assert loaded == initial_data

    updated_data = BvvAnnualData(
        previous_hgb_equity=None,
        contribution=Decimal("1000.00"),
        withdrawal_distribution=Decimal("250.00"),
    )

    repository.save_for_fiscal_year(
        company_id=company.company_id,
        fiscal_year=fiscal_year,
        data=updated_data,
    )

    loaded = repository.get_for_fiscal_year(
        company_id=company.company_id,
        fiscal_year=fiscal_year,
    )

    assert loaded == updated_data

"""Tests für jahresbezogene Daten zur Ergebnisverwendung."""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from simpleob.database.company_repository import (
    CompanyRepository,
)
from simpleob.database.database import Base
from simpleob.database.profit_appropriation_annual_data_repository import (
    ProfitAppropriationAnnualDataRepository,
)
from simpleob.domain.company import Company
from simpleob.domain.fiscal_year import FiscalYear
from simpleob.domain.profit_appropriation_annual_data import (
    ProfitAppropriationAnnualData,
)


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


def test_saves_loads_and_updates_profit_appropriation_annual_data(
    session,
) -> None:
    """Ergebnisverwendung kann gespeichert und aktualisiert werden."""

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

    repository = ProfitAppropriationAnnualDataRepository(
        session
    )

    initial_data = ProfitAppropriationAnnualData(
        statutory_reserve_addition=Decimal("2500.00"),
        other_revenue_reserves_addition=Decimal("1000.00"),
        statutory_reserve_release=Decimal("0.00"),
        other_revenue_reserves_release=Decimal("0.00"),
        distribution=Decimal("3000.00"),
        profit_loss_carryforward=Decimal("4500.00"),
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

    updated_data = ProfitAppropriationAnnualData(
        statutory_reserve_addition=Decimal("0.00"),
        other_revenue_reserves_addition=Decimal("0.00"),
        statutory_reserve_release=Decimal("1000.00"),
        other_revenue_reserves_release=Decimal("2000.00"),
        distribution=Decimal("0.00"),
        profit_loss_carryforward=Decimal("-5000.00"),
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

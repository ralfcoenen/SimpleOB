from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from openbilanz.database.company_repository import (
    CompanyRepository,
)
from openbilanz.database.database import Base
from openbilanz.domain.company import Company
from openbilanz.domain.fiscal_year import FiscalYear


def test_adds_and_loads_company() -> None:
    engine = create_engine(
        "sqlite:///:memory:"
    )
    Base.metadata.create_all(engine)

    Session = sessionmaker(
        bind=engine
    )

    with Session() as session:
        repository = CompanyRepository(
            session
        )

        company = Company(
            company_id=uuid4(),
            name="Muster UG",
        )

        repository.add(company)

        loaded_company = repository.get(
            company.company_id
        )

    assert loaded_company == company
    assert loaded_company is not company
    assert loaded_company.name == "Muster UG"

def test_adds_and_loads_fiscal_year() -> None:
    engine = create_engine(
        "sqlite:///:memory:"
    )
    Base.metadata.create_all(engine)

    Session = sessionmaker(
        bind=engine
    )

    with Session() as session:
        repository = CompanyRepository(
            session
        )

        company = Company(
            company_id=uuid4(),
            name="Muster UG",
        )
        repository.add(company)

        fiscal_year = FiscalYear(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )

        repository.add_fiscal_year(
            company.company_id,
            fiscal_year,
        )

        fiscal_years = repository.get_fiscal_years(
            company.company_id
        )

    assert fiscal_years == (fiscal_year,)


def test_loads_fiscal_years_in_chronological_order() -> None:
    engine = create_engine(
        "sqlite:///:memory:"
    )
    Base.metadata.create_all(engine)

    Session = sessionmaker(
        bind=engine
    )

    with Session() as session:
        repository = CompanyRepository(
            session
        )

        company = Company(
            company_id=uuid4(),
            name="Muster UG",
        )
        repository.add(company)

        later_fiscal_year = FiscalYear(
            start_date=date(2027, 1, 1),
            end_date=date(2027, 12, 31),
        )
        earlier_fiscal_year = FiscalYear(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )

        repository.add_fiscal_year(
            company.company_id,
            later_fiscal_year,
        )
        repository.add_fiscal_year(
            company.company_id,
            earlier_fiscal_year,
        )

        fiscal_years = repository.get_fiscal_years(
            company.company_id
        )

    assert fiscal_years == (
        earlier_fiscal_year,
        later_fiscal_year,
    )

def test_rejects_duplicate_fiscal_year() -> None:
    engine = create_engine(
        "sqlite:///:memory:"
    )
    Base.metadata.create_all(engine)

    Session = sessionmaker(
        bind=engine
    )

    with Session() as session:
        repository = CompanyRepository(
            session
        )

        company = Company(
            company_id=uuid4(),
            name="Muster UG",
        )
        repository.add(company)

        fiscal_year = FiscalYear(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )

        repository.add_fiscal_year(
            company.company_id,
            fiscal_year,
        )

        with pytest.raises(
            ValueError,
            match="Geschäftsjahr überschneidet sich",
        ):
            repository.add_fiscal_year(
                company.company_id,
                fiscal_year,
            )


def test_rejects_overlapping_fiscal_year() -> None:
    engine = create_engine(
        "sqlite:///:memory:"
    )
    Base.metadata.create_all(engine)

    Session = sessionmaker(
        bind=engine
    )

    with Session() as session:
        repository = CompanyRepository(
            session
        )

        company = Company(
            company_id=uuid4(),
            name="Muster UG",
        )
        repository.add(company)

        repository.add_fiscal_year(
            company.company_id,
            FiscalYear(
                start_date=date(2026, 1, 1),
                end_date=date(2026, 12, 31),
            ),
        )

        overlapping_fiscal_year = FiscalYear(
            start_date=date(2026, 7, 1),
            end_date=date(2027, 6, 30),
        )

        with pytest.raises(
            ValueError,
            match="Geschäftsjahr überschneidet sich",
        ):
            repository.add_fiscal_year(
                company.company_id,
                overlapping_fiscal_year,
            )

def test_lists_companies_alphabetically() -> None:
    engine = create_engine(
        "sqlite:///:memory:"
    )
    Base.metadata.create_all(engine)

    Session = sessionmaker(
        bind=engine
    )

    with Session() as session:
        repository = CompanyRepository(session)

        companies = (
            Company(
                company_id=uuid4(),
                name="Zeta GmbH",
            ),
            Company(
                company_id=uuid4(),
                name="Alpha UG",
            ),
            Company(
                company_id=uuid4(),
                name="Muster GmbH",
            ),
        )

        for company in companies:
            repository.add(company)

        loaded_companies = repository.list_companies()

    assert tuple(
        company.name
        for company in loaded_companies
    ) == (
        "Alpha UG",
        "Muster GmbH",
        "Zeta GmbH",
    )


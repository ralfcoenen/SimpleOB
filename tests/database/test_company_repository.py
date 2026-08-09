from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from openbilanz.database.company_repository import (
    CompanyRepository,
)
from openbilanz.database.database import Base
from openbilanz.database.models import Wirtschaftsjahr
from openbilanz.domain.company import Company
from openbilanz.domain.fiscal_year import FiscalYear
from openbilanz.domain.fiscal_year_status import FiscalYearStatus
from openbilanz.domain.managed_fiscal_year import ManagedFiscalYear


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

def test_new_fiscal_year_is_open() -> None:
    """Ein neues Geschäftsjahr wird mit Status OPEN gespeichert."""

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

        fiscal_year = FiscalYear(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )

        repository.add(
            company
        )

        repository.add_fiscal_year(
            company.company_id,
            fiscal_year,
        )

        managed_fiscal_years = (
            repository.get_managed_fiscal_years(
                company.company_id
            )
        )

    assert managed_fiscal_years == (
        ManagedFiscalYear(
            fiscal_year=fiscal_year,
            status=FiscalYearStatus.OPEN,
        ),
    )
    

def test_closes_fiscal_year() -> None:
    """Ein offenes Geschäftsjahr kann abgeschlossen werden."""

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

        fiscal_year = FiscalYear(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )

        repository.add(
            company
        )

        repository.add_fiscal_year(
            company.company_id,
            fiscal_year,
        )

        repository.close_fiscal_year(
            company.company_id,
            fiscal_year,
        )

        managed_fiscal_years = (
            repository.get_managed_fiscal_years(
                company.company_id
            )
        )

    assert managed_fiscal_years == (
        ManagedFiscalYear(
            fiscal_year=fiscal_year,
            status=FiscalYearStatus.CLOSED,
        ),
    )

def test_rejects_closing_closed_fiscal_year() -> None:
    """Ein bereits abgeschlossenes Geschäftsjahr darf nicht erneut geschlossen werden."""

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

        fiscal_year = FiscalYear(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )

        repository.add(
            company
        )

        repository.add_fiscal_year(
            company.company_id,
            fiscal_year,
        )

        repository.close_fiscal_year(
            company.company_id,
            fiscal_year,
        )

        with pytest.raises(
            ValueError,
            match="Geschäftsjahr ist bereits abgeschlossen",
        ):
            repository.close_fiscal_year(
                company.company_id,
                fiscal_year,
            )

def test_close_fiscal_year_can_defer_commit() -> None:
    """Der Statuswechsel kann Teil einer äußeren Transaktion sein."""

    engine = create_engine(
        "sqlite:///:memory:"
    )
    Base.metadata.create_all(engine)

    Session = sessionmaker(
        bind=engine
    )

    company = Company(
        company_id=uuid4(),
        name="Muster UG",
    )

    fiscal_year = FiscalYear(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )

    with Session() as session:
        repository = CompanyRepository(
            session
        )

        repository.add(company)
        repository.add_fiscal_year(
            company.company_id,
            fiscal_year,
        )

        repository.close_fiscal_year(
            company.company_id,
            fiscal_year,
            commit=False,
        )

        session.rollback()

    with Session() as session:
        repository = CompanyRepository(
            session
        )

        managed_fiscal_years = (
            repository.get_managed_fiscal_years(
                company.company_id
            )
        )

    assert managed_fiscal_years == (
        ManagedFiscalYear(
            fiscal_year=fiscal_year,
            status=FiscalYearStatus.OPEN,
        ),
    )

def test_loads_opening_source_of_fiscal_year() -> None:
    """Die Herkunft eines eröffneten Geschäftsjahres wird geladen."""

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

        source_fiscal_year = FiscalYear(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )

        target_fiscal_year = FiscalYear(
            start_date=date(2027, 1, 1),
            end_date=date(2027, 12, 31),
        )

        repository.add(company)

        repository.add_fiscal_year(
            company.company_id,
            source_fiscal_year,
        )

        repository.add_fiscal_year(
            company.company_id,
            target_fiscal_year,
        )

        source_model = (
            session.query(Wirtschaftsjahr)
            .filter(
                Wirtschaftsjahr.start_date
                == source_fiscal_year.start_date,
                Wirtschaftsjahr.end_date
                == source_fiscal_year.end_date,
            )
            .one()
        )

        target_model = (
            session.query(Wirtschaftsjahr)
            .filter(
                Wirtschaftsjahr.start_date
                == target_fiscal_year.start_date,
                Wirtschaftsjahr.end_date
                == target_fiscal_year.end_date,
            )
            .one()
        )

        target_model.opening_source = source_model
        session.commit()

        managed_fiscal_years = (
            repository.get_managed_fiscal_years(
                company.company_id
            )
        )

    assert managed_fiscal_years == (
        ManagedFiscalYear(
            fiscal_year=source_fiscal_year,
            status=FiscalYearStatus.OPEN,
        ),
        ManagedFiscalYear(
            fiscal_year=target_fiscal_year,
            status=FiscalYearStatus.OPEN,
            opening_source=source_fiscal_year,
        ),
    )

def test_rejects_opening_source_from_other_company() -> None:
    """Ein Geschäftsjahr eines anderen Unternehmens darf nicht als Quelle dienen."""

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

        company_a = Company(
            company_id=uuid4(),
            name="Unternehmen A",
        )

        company_b = Company(
            company_id=uuid4(),
            name="Unternehmen B",
        )

        source_fiscal_year = FiscalYear(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )

        target_fiscal_year = FiscalYear(
            start_date=date(2027, 1, 1),
            end_date=date(2027, 12, 31),
        )

        repository.add(company_a)
        repository.add(company_b)

        repository.add_fiscal_year(
            company_a.company_id,
            source_fiscal_year,
        )

        repository.add_fiscal_year(
            company_b.company_id,
            target_fiscal_year,
        )

        with pytest.raises(
            ValueError,
            match="Herkunftsgeschäftsjahr wurde nicht gefunden.",
        ):
            repository.set_opening_source(
                company_b.company_id,
                target_fiscal_year,
                source_fiscal_year,
            )

def test_rejects_missing_target_fiscal_year_for_opening_source() -> None:
    """Ein nicht vorhandenes Zielgeschäftsjahr wird abgelehnt."""

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

        source_fiscal_year = FiscalYear(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )

        missing_target_fiscal_year = FiscalYear(
            start_date=date(2027, 1, 1),
            end_date=date(2027, 12, 31),
        )

        repository.add(company)

        repository.add_fiscal_year(
            company.company_id,
            source_fiscal_year,
        )

        with pytest.raises(
            ValueError,
            match="Geschäftsjahr wurde nicht gefunden.",
        ):
            repository.set_opening_source(
                company.company_id,
                missing_target_fiscal_year,
                source_fiscal_year,
            )


def test_rejects_missing_opening_source_fiscal_year() -> None:
    """Ein nicht vorhandenes Herkunftsgeschäftsjahr wird abgelehnt."""

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

        missing_source_fiscal_year = FiscalYear(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )

        target_fiscal_year = FiscalYear(
            start_date=date(2027, 1, 1),
            end_date=date(2027, 12, 31),
        )

        repository.add(company)

        repository.add_fiscal_year(
            company.company_id,
            target_fiscal_year,
        )

        with pytest.raises(
            ValueError,
            match="Herkunftsgeschäftsjahr wurde nicht gefunden.",
        ):
            repository.set_opening_source(
                company.company_id,
                target_fiscal_year,
                missing_source_fiscal_year,
            )


def test_sets_opening_source_of_fiscal_year() -> None:
    """Die Herkunft eines Geschäftsjahres kann gespeichert werden."""

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

        source_fiscal_year = FiscalYear(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )

        target_fiscal_year = FiscalYear(
            start_date=date(2027, 1, 1),
            end_date=date(2027, 12, 31),
        )

        repository.add(company)

        repository.add_fiscal_year(
            company.company_id,
            source_fiscal_year,
        )

        repository.add_fiscal_year(
            company.company_id,
            target_fiscal_year,
        )

        repository.set_opening_source(
            company.company_id,
            target_fiscal_year,
            source_fiscal_year,
        )

        managed_fiscal_years = (
            repository.get_managed_fiscal_years(
                company.company_id
            )
        )

    assert managed_fiscal_years == (
        ManagedFiscalYear(
            fiscal_year=source_fiscal_year,
            status=FiscalYearStatus.OPEN,
        ),
        ManagedFiscalYear(
            fiscal_year=target_fiscal_year,
            status=FiscalYearStatus.OPEN,
            opening_source=source_fiscal_year,
        ),
    )



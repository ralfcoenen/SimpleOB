from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from simpleob.database.company_repository import (
    CompanyRepository,
)
from simpleob.database.database import Base
from simpleob.database.models import Wirtschaftsjahr
from simpleob.domain.company import Company
from simpleob.domain.company_master_data import (
    CompanyMasterData,
)
from simpleob.domain.fiscal_year import FiscalYear
from simpleob.domain.fiscal_year_status import FiscalYearStatus
from simpleob.domain.managed_fiscal_year import ManagedFiscalYear


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



def test_loads_empty_company_master_data() -> None:
    """Für neue Unternehmen sind zunächst leere Stammdaten vorhanden."""

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

        master_data = repository.get_master_data(
            company.company_id
        )

    assert master_data == CompanyMasterData(
        company=company,
    )

    assert master_data is not None
    assert master_data.is_e_bilanz_ready is False


def test_saves_and_loads_company_master_data() -> None:
    """Unternehmensstammdaten können vollständig gespeichert werden."""

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

        master_data = CompanyMasterData(
            company=company,
            legal_form="UG (haftungsbeschränkt)",
            tax_number="1234567890123",
            tax_office="Finanzamt Musterstadt",
            tax_id="12345678901",
            tax_economic_id="DE123456789",
            bf4="1234",
            street="Musterstraße",
            house_number="12a",
            postal_code="12345",
            city="Musterstadt",
            country="DE",
            federal_state="NW",
            business="Softwareentwicklung",
        )

        repository.save_master_data(
            master_data
        )

        loaded_master_data = (
            repository.get_master_data(
                company.company_id
            )
        )

    assert loaded_master_data == master_data
    assert loaded_master_data is not master_data

    assert (
        loaded_master_data is not None
    )
    assert (
        loaded_master_data.is_e_bilanz_ready
        is True
    )


def test_updates_company_master_data() -> None:
    """Vorhandene Unternehmensstammdaten können geändert werden."""

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

        repository.save_master_data(
            CompanyMasterData(
                company=company,
                legal_form="UG (haftungsbeschränkt)",
                tax_number="1234567890123",
                city="Musterstadt",
                country="DE",
                federal_state="NW",
            )
        )

        updated_master_data = CompanyMasterData(
            company=company,
            legal_form="UG (haftungsbeschränkt)",
            tax_number="1234567890123",
            tax_office="Finanzamt Berlin",
            tax_id="12345678901",
            tax_economic_id="DE987654321",
            bf4="5678",
            street="Neue Straße",
            house_number="25",
            postal_code="10115",
            city="Berlin",
            country="DE",
            federal_state="NW",
            business="Software und Beratung",
        )

        repository.save_master_data(
            updated_master_data
        )

        loaded_master_data = (
            repository.get_master_data(
                company.company_id
            )
        )

    assert loaded_master_data == (
        updated_master_data
    )


def test_save_master_data_can_be_rolled_back() -> None:
    """Stammdaten können ohne Commit gespeichert und zurückgerollt werden."""

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

        original_master_data = CompanyMasterData(
            company=company,
            legal_form="UG (haftungsbeschränkt)",
            tax_number="1234567890123",
            city="Musterstadt",
            country="DE",
            federal_state="NW",
        )

        repository.save_master_data(
            original_master_data
        )

        changed_master_data = CompanyMasterData(
            company=company,
            legal_form="GmbH",
            tax_number="9876543210987",
            city="Berlin",
            country="DE",
            federal_state="BE",
        )

        repository.save_master_data(
            changed_master_data,
            commit=False,
        )

        session.rollback()

        loaded_master_data = (
            repository.get_master_data(
                company.company_id
            )
        )

    assert loaded_master_data == (
        original_master_data
    )


def test_rejects_master_data_for_missing_company() -> None:
    """Stammdaten eines unbekannten Unternehmens werden abgelehnt."""

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
            name="Nicht vorhandene UG",
        )

        master_data = CompanyMasterData(
            company=company,
            legal_form="UG (haftungsbeschränkt)",
            tax_number="1234567890123",
        )

        with pytest.raises(
            ValueError,
            match="Unternehmen wurde nicht gefunden.",
        ):
            repository.save_master_data(
                master_data
            )


def test_rejects_stale_company_master_data() -> None:
    """Veraltete Stammdaten dürfen neuere Änderungen nicht überschreiben."""

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    with Session() as session:
        repository = CompanyRepository(session)

        company = Company(
            company_id=uuid4(),
            name="Muster UG",
        )
        repository.add(company)

        original = CompanyMasterData(
            company=company,
            city="Musterstadt",
        )
        repository.save_master_data(original)

        current = CompanyMasterData(
            company=company,
            city="Berlin",
        )
        repository.save_master_data(
            current,
            expected_master_data=original,
        )

        stale_change = CompanyMasterData(
            company=company,
            city="Hamburg",
        )

        with pytest.raises(
            ValueError,
            match="zwischenzeitlich",
        ):
            repository.save_master_data(
                stale_change,
                expected_master_data=original,
            )

        assert repository.get_master_data(
            company.company_id
        ) == current

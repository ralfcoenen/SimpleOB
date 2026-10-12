"""PostgreSQL-Konkurrenztest für die Geschäftsjahresanlage."""

import os
from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from openbilanz.database.company_repository import CompanyRepository
from openbilanz.database.lock_error import DatabaseLockError
from openbilanz.database.models import Mandant, Wirtschaftsjahr
from openbilanz.domain.company import Company
from openbilanz.domain.fiscal_year import FiscalYear


@pytest.fixture
def postgres_fiscal_year_creation_data():
    """Erzeugt einen isolierten Mandanten in der PostgreSQL-Testdatenbank."""

    database_url = os.environ.get("SIMPLEOB_POSTGRES_TEST_URL")

    if not database_url:
        pytest.skip("SIMPLEOB_POSTGRES_TEST_URL ist nicht gesetzt.")

    url = make_url(database_url)

    if (
        url.drivername != "postgresql+psycopg"
        or url.database != "simpleob_migration_test"
        or url.host not in ("localhost", "127.0.0.1")
    ):
        pytest.fail(
            "Nur die lokale PostgreSQL-Datenbank "
            "'simpleob_migration_test' ist zulässig."
        )

    engine = create_engine(database_url)
    Session = sessionmaker(bind=engine)

    company = Company(
        company_id=uuid4(),
        name="PostgreSQL Geschäftsjahresanlage Test",
    )

    try:
        with Session() as session:
            CompanyRepository(session).add(company)

        yield Session, company

    finally:
        try:
            with Session() as session:
                company_model = session.scalar(
                    select(Mandant).where(
                        Mandant.company_id == str(company.company_id)
                    )
                )

                if company_model is not None:
                    session.query(Wirtschaftsjahr).filter(
                        Wirtschaftsjahr.mandant_id == company_model.id
                    ).delete(synchronize_session=False)

                    session.delete(company_model)
                    session.commit()
        finally:
            engine.dispose()


def test_fiscal_year_creation_lock_conflict_and_retry(
    postgres_fiscal_year_creation_data,
) -> None:
    """Sperrkonflikt und erneute Überschneidungsprüfung."""

    Session, company = postgres_fiscal_year_creation_data

    fiscal_year = FiscalYear(
        start_date=date(2027, 1, 1),
        end_date=date(2027, 12, 31),
    )

    with Session() as session_a, Session() as session_b:
        repository_a = CompanyRepository(session_a)
        repository_b = CompanyRepository(session_b)

        # Benutzer A sperrt den Mandanten und legt das Jahr an,
        # ohne die Transaktion bereits abzuschließen.
        session_a.execute(
            select(Mandant)
            .where(
                Mandant.company_id == str(company.company_id)
            )
            .with_for_update()
        ).scalar_one()

        repository_a.add_fiscal_year(
            company.company_id,
            fiscal_year,
            commit=False,
        )

        try:
            # Benutzer B darf die Überschneidungsprüfung
            # nicht parallel zur noch offenen Anlage ausführen.
            with pytest.raises(
                DatabaseLockError,
                match="Mandant momentan gesperrt",
            ):
                repository_b.add_fiscal_year(
                    company.company_id,
                    fiscal_year,
                )

        finally:
            # Die Anlage durch Benutzer A wird abgeschlossen.
            session_a.commit()

        # Nach Freigabe der Sperre prüft Benutzer B erneut.
        # Das inzwischen angelegte Geschäftsjahr muss erkannt werden.
        with pytest.raises(
            ValueError,
            match="Geschäftsjahr überschneidet sich",
        ):
            repository_b.add_fiscal_year(
                company.company_id,
                fiscal_year,
            )

        session_b.rollback()

    # Abschließend prüfen wir die dauerhaft gespeicherten Daten.
    with Session() as session:
        company_model = session.scalar(
            select(Mandant).where(
                Mandant.company_id == str(company.company_id)
            )
        )

        assert company_model is not None

        fiscal_years = session.scalars(
            select(Wirtschaftsjahr).where(
                Wirtschaftsjahr.mandant_id == company_model.id
            )
        ).all()

        assert len(fiscal_years) == 1
        assert fiscal_years[0].start_date == fiscal_year.start_date
        assert fiscal_years[0].end_date == fiscal_year.end_date

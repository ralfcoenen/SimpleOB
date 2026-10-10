
"""PostgreSQL-Tests für die Geschäftsjahressperre."""

import os
import time
from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from openbilanz.database.company_repository import CompanyRepository
from openbilanz.database.lock_error import DatabaseLockError
from openbilanz.database.models import Mandant, Wirtschaftsjahr
from openbilanz.domain.company import Company
from openbilanz.domain.fiscal_year import FiscalYear


@pytest.fixture
def postgres_sessions():
    """Erstellt zwei Sessions für die isolierte PostgreSQL-Testdatenbank."""

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
        name="SimpleOB PostgreSQL Lock-Timeout-Test",
    )
    fiscal_year = FiscalYear(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )

    try:
        with Session() as setup_session:
            repository = CompanyRepository(setup_session)
            repository.add(company)
            repository.add_fiscal_year(
                company.company_id,
                fiscal_year,
            )

        yield Session, company, fiscal_year

    finally:
        with Session() as cleanup_session:
            company_model = (
                cleanup_session.query(Mandant)
                .filter(
                    Mandant.company_id == str(company.company_id)
                )
                .one_or_none()
            )

            if company_model is not None:
                cleanup_session.delete(company_model)
                cleanup_session.commit()

        engine.dispose()


def test_fiscal_year_lock_timeout_and_retry(
    postgres_sessions,
) -> None:
    """Sperrkonflikt meldet sich und die Session bleibt verwendbar."""

    Session, company, fiscal_year = postgres_sessions

    with Session() as session_a, Session() as session_b:
        repository_a = CompanyRepository(session_a)
        repository_b = CompanyRepository(session_b)

        try:
            repository_a.lock_open_fiscal_year(
                company.company_id,
                fiscal_year,
            )

            start = time.monotonic()

            with pytest.raises(DatabaseLockError) as error:
                repository_b.lock_open_fiscal_year(
                    company.company_id,
                    fiscal_year,
                )

            elapsed = time.monotonic() - start

            assert 2.5 <= elapsed < 6.0

            assert (
                "Geschäftsjahr momentan gesperrt"
                in str(error.value)
            )
            assert (
                "Es wurden keine Änderungen gespeichert"
                in str(error.value)
            )

            # Sitzung A hält ihre Sperre weiterhin.
            locked_year = (
                session_a.query(Wirtschaftsjahr)
                .join(Mandant)
                .filter(
                    Mandant.company_id == str(company.company_id),
                    Wirtschaftsjahr.start_date == fiscal_year.start_date,
                    Wirtschaftsjahr.end_date == fiscal_year.end_date,
                )
                .one()
            )
            assert locked_year.status == "OPEN"

            # Sitzung A gibt die Sperre frei.
            session_a.commit()

            # Sitzung B wurde nach dem Timeout zurückgesetzt
            # und muss jetzt erneut erfolgreich sperren können.
            repository_b.lock_open_fiscal_year(
                company.company_id,
                fiscal_year,
            )

            session_b.commit()

        finally:
            session_a.rollback()
            session_b.rollback()

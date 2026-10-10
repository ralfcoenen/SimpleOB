
"""PostgreSQL-Konkurrenztest für BookingRepository."""

import os
import time
from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from openbilanz.database.booking_repository import BookingRepository
from openbilanz.database.company_repository import CompanyRepository
from openbilanz.database.lock_error import DatabaseLockError
from openbilanz.database.models import Mandant, Wirtschaftsjahr
from openbilanz.domain.booking import Booking
from openbilanz.domain.booking_line import BookingLine
from openbilanz.domain.company import Company
from openbilanz.domain.entry_side import EntrySide
from openbilanz.domain.fiscal_year import FiscalYear


@pytest.fixture
def postgres_sessions():
    """Zwei unabhängige Sessions in der isolierten Testdatenbank."""

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

    try:
        with Session() as setup_session:
            company = Company(
                company_id=uuid4(),
                name="SimpleOB PostgreSQL Sperrtest",
            )
            fiscal_year = FiscalYear(
                start_date=date(2026, 1, 1),
                end_date=date(2026, 12, 31),
            )

            company_repository = CompanyRepository(setup_session)
            company_repository.add(company)
            company_repository.add_fiscal_year(
                company.company_id,
                fiscal_year,
            )

        yield Session, company, fiscal_year

    finally:
        # Ausschließlich die eigenen Testdatensätze entfernen.
        with Session() as cleanup_session:
            company_model = (
                cleanup_session.query(Mandant)
                .filter(Mandant.company_id == str(company.company_id))
                .one_or_none()
            )

            if company_model is not None:
                cleanup_session.delete(company_model)
                cleanup_session.commit()

        engine.dispose()



def test_postgresql_booking_waits_for_fiscal_year_lock(
    postgres_sessions,
) -> None:
    """Sperrkonflikt wird gemeldet; danach ist die Buchung möglich."""

    Session, company, fiscal_year = postgres_sessions

    booking = Booking(
        booking_date=date(2026, 8, 8),
        description="PostgreSQL-Sperrtest",
        lines=(
            BookingLine(
                account_number="4980",
                side=EntrySide.DEBIT,
                amount=Decimal("100.00"),
            ),
            BookingLine(
                account_number="1200",
                side=EntrySide.CREDIT,
                amount=Decimal("100.00"),
            ),
        ),
    )

    with Session() as session_a, Session() as session_b:
        try:
            # Session A sperrt das Geschäftsjahr.
            fiscal_year_model = (
                session_a.query(Wirtschaftsjahr)
                .join(Mandant)
                .filter(
                    Mandant.company_id == str(company.company_id),
                    Wirtschaftsjahr.start_date == fiscal_year.start_date,
                    Wirtschaftsjahr.end_date == fiscal_year.end_date,
                )
                .with_for_update(of=Wirtschaftsjahr)
                .one()
            )

            assert fiscal_year_model.status == "OPEN"

            repository_b = BookingRepository(session_b)

            # Session B erhält nach dem Timeout eine Fachmeldung.
            start = time.monotonic()

            with pytest.raises(DatabaseLockError) as error:
                repository_b.add(
                    company_id=company.company_id,
                    fiscal_year=fiscal_year,
                    booking=booking,
                )

            elapsed = time.monotonic() - start

            assert 2.5 <= elapsed < 6.0

            assert "Geschäftsjahr" in str(error.value)
            assert "gesperrt" in str(error.value)
            assert "Es wurden keine Änderungen gespeichert" in str(
                error.value
            )

            # Session A gibt die Sperre frei.
            session_a.commit()

            # Derselbe Buchungsversuch muss jetzt gelingen.
            repository_b.add(
                company_id=company.company_id,
                fiscal_year=fiscal_year,
                booking=booking,
            )

            loaded = repository_b.list_for_fiscal_year(
                company_id=company.company_id,
                fiscal_year=fiscal_year,
            )

            assert loaded == (booking,)

        finally:
            session_a.rollback()
            session_b.rollback()

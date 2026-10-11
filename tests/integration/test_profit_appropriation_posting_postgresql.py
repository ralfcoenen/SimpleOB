"""PostgreSQL-Konkurrenztest für Ergebnisverwendungsbuchungen."""

import os
from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, delete, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from openbilanz.database.booking_repository import BookingRepository
from openbilanz.database.company_repository import CompanyRepository
from openbilanz.database.lock_error import DatabaseLockError
from openbilanz.database.models import (
    Gewinnverwendungsbuchung,
    Mandant,
    Wirtschaftsjahr,
)
from openbilanz.database.profit_appropriation_posting_repository import (
    ProfitAppropriationPostingRepository,
)
from openbilanz.domain.company import Company
from openbilanz.domain.fiscal_year import FiscalYear
from openbilanz.domain.profit_appropriation_posting_proposal import (
    ProfitAppropriationPostingProposal,
)
from openbilanz.domain.profit_appropriation_posting_type import (
    ProfitAppropriationPostingType,
)
from openbilanz.services.profit_appropriation_booking_service import (
    ProfitAppropriationBookingService,
)
from openbilanz.services.profit_appropriation_posting_workflow import (
    ProfitAppropriationPostingWorkflow,
)


@pytest.fixture
def postgres_profit_appropriation_data():
    """Erzeugt isolierte Daten ausschließlich in der Testdatenbank."""

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
        name="PostgreSQL Ergebnisverwendung Test",
    )

    source_fiscal_year = FiscalYear(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )

    target_fiscal_year = FiscalYear(
        start_date=date(2027, 1, 1),
        end_date=date(2027, 12, 31),
    )

    try:
        with Session() as session:
            company_repository = CompanyRepository(session)

            company_repository.add(company)

            company_repository.add_fiscal_year(
                company.company_id,
                source_fiscal_year,
            )

            company_repository.add_fiscal_year(
                company.company_id,
                target_fiscal_year,
            )

            company_repository.close_fiscal_year(
                company.company_id,
                source_fiscal_year,
            )

            company_repository.set_opening_source(
                company.company_id,
                target_fiscal_year,
                source_fiscal_year,
            )

        yield (
            Session,
            company,
            source_fiscal_year,
            target_fiscal_year,
        )

    finally:
        try:
            with Session() as session:
                company_model = session.scalar(
                    select(Mandant).where(
                        Mandant.company_id == str(company.company_id)
                    )
                )

                if company_model is not None:
                    fiscal_year_ids = select(Wirtschaftsjahr.id).where(
                        Wirtschaftsjahr.mandant_id == company_model.id
                    )

                    session.execute(
                        delete(Gewinnverwendungsbuchung).where(
                            Gewinnverwendungsbuchung
                            .quell_wirtschaftsjahr_id.in_(
                                fiscal_year_ids
                            )
                        )
                    )

                    session.delete(company_model)
                    session.commit()
        finally:
            engine.dispose()


def _workflow(session):
    """Erstellt den Workflow mit gemeinsam genutzter Session."""

    return ProfitAppropriationPostingWorkflow(
        session=session,
        company_repository=CompanyRepository(session),
        booking_repository=BookingRepository(session),
        posting_repository=ProfitAppropriationPostingRepository(session),
        booking_service=ProfitAppropriationBookingService(),
    )


def test_profit_appropriation_lock_retry_and_duplicate_prevention(
    postgres_profit_appropriation_data,
):
    """Sperrkonflikt, Wiederholung und doppelte Buchung werden geprüft."""

    (
        Session,
        company,
        source_fiscal_year,
        target_fiscal_year,
    ) = postgres_profit_appropriation_data

    proposal = ProfitAppropriationPostingProposal(
        posting_type=ProfitAppropriationPostingType.DISTRIBUTION,
        booking_date=date(2027, 3, 15),
        amount=Decimal("5000.00"),
        debit_account_number="2970",
        credit_account_number="0755",
    )

    def confirm(session):
        return _workflow(session).confirm(
            company_id=company.company_id,
            source_fiscal_year=source_fiscal_year,
            target_fiscal_year=target_fiscal_year,
            proposal=proposal,
        )

    def persisted_state(session):
        bookings = BookingRepository(session).list_for_fiscal_year(
            company_id=company.company_id,
            fiscal_year=target_fiscal_year,
        )

        postings = (
            ProfitAppropriationPostingRepository(session)
            .list_for_source_fiscal_year(
                company_id=company.company_id,
                source_fiscal_year_end=source_fiscal_year.end_date,
            )
        )

        return bookings, postings

    with Session() as session_a, Session() as session_b:
        CompanyRepository(session_a).lock_open_fiscal_year(
            company.company_id,
            target_fiscal_year,
        )

        try:
            with pytest.raises(DatabaseLockError):
                confirm(session_b)

            with Session() as check_session:
                bookings, postings = persisted_state(check_session)
                assert bookings == ()
                assert postings == ()

        finally:
            session_a.rollback()

        posting = confirm(session_b)

        with Session() as check_session:
            bookings, postings = persisted_state(check_session)

            assert len(bookings) == 1
            assert postings == (posting,)
            assert posting.booking_id == bookings[0].booking_id

        with pytest.raises(
            ValueError,
            match="existiert bereits eine wirksame Buchung",
        ):
            confirm(session_b)

        with Session() as check_session:
            bookings, postings = persisted_state(check_session)

            assert len(bookings) == 1
            assert postings == (posting,)


def test_profit_appropriation_can_be_reposted_after_reversal(
    postgres_profit_appropriation_data,
):
    """Nach Stornierung ist derselbe Ergebnisverwendungstyp erneut buchbar."""

    from openbilanz.domain.booking import Booking
    from openbilanz.domain.booking_line import BookingLine
    from openbilanz.domain.booking_type import BookingType
    from openbilanz.domain.entry_side import EntrySide

    (
        Session,
        company,
        source_fiscal_year,
        target_fiscal_year,
    ) = postgres_profit_appropriation_data

    proposal = ProfitAppropriationPostingProposal(
        posting_type=ProfitAppropriationPostingType.DISTRIBUTION,
        booking_date=date(2027, 3, 15),
        amount=Decimal("5000.00"),
        debit_account_number="2970",
        credit_account_number="0755",
    )

    with Session() as session:
        workflow = _workflow(session)
        booking_repository = BookingRepository(session)
        posting_repository = ProfitAppropriationPostingRepository(
            session
        )

        first_posting = workflow.confirm(
            company_id=company.company_id,
            source_fiscal_year=source_fiscal_year,
            target_fiscal_year=target_fiscal_year,
            proposal=proposal,
        )

        original_booking = next(
            booking
            for booking in booking_repository.list_for_fiscal_year(
                company_id=company.company_id,
                fiscal_year=target_fiscal_year,
            )
            if booking.booking_id == first_posting.booking_id
        )

        reversal = Booking(
            booking_date=date(2027, 3, 16),
            description="Storno Ergebnisverwendung",
            booking_type=BookingType.REVERSAL,
            reversal_of_booking_id=original_booking.booking_id,
            lines=tuple(
                BookingLine(
                    account_number=line.account_number,
                    side=(
                        EntrySide.CREDIT
                        if line.side is EntrySide.DEBIT
                        else EntrySide.DEBIT
                    ),
                    amount=line.amount,
                )
                for line in original_booking.lines
            ),
        )

        booking_repository.add(
            company_id=company.company_id,
            fiscal_year=target_fiscal_year,
            booking=reversal,
        )

        assert booking_repository.is_reversed(
            first_posting.booking_id
        )

        second_posting = workflow.confirm(
            company_id=company.company_id,
            source_fiscal_year=source_fiscal_year,
            target_fiscal_year=target_fiscal_year,
            proposal=proposal,
        )

        assert second_posting.booking_id != first_posting.booking_id

        postings = posting_repository.list_for_source_fiscal_year(
            company_id=company.company_id,
            source_fiscal_year_end=source_fiscal_year.end_date,
        )

        assert len(postings) == 2
        assert {posting.booking_id for posting in postings} == {
            first_posting.booking_id,
            second_posting.booking_id,
        }

        assert booking_repository.is_reversed(
            first_posting.booking_id
        )
        assert not booking_repository.is_reversed(
            second_posting.booking_id
        )

        bookings = booking_repository.list_for_fiscal_year(
            company_id=company.company_id,
            fiscal_year=target_fiscal_year,
        )

        assert len(bookings) == 3
        assert sum(
            booking.booking_type is BookingType.REVERSAL
            for booking in bookings
        ) == 1

"""PostgreSQL-Konkurrenztest für die Geschäftsjahreseröffnung."""

import os
from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from unittest.mock import Mock

from openbilanz.core.context import ApplicationContext
from openbilanz.services.fiscal_year_workspace import FiscalYearWorkspace
from openbilanz.database.booking_repository import BookingRepository
from openbilanz.database.company_repository import CompanyRepository
from openbilanz.database.lock_error import DatabaseLockError
from openbilanz.database.models import Mandant
from openbilanz.domain.account_type import AccountType
from openbilanz.domain.booking import Booking
from openbilanz.domain.booking_line import BookingLine
from openbilanz.domain.booking_type import BookingType
from openbilanz.domain.company import Company
from openbilanz.domain.entry_side import EntrySide
from openbilanz.domain.fiscal_year import FiscalYear
from openbilanz.services.fiscal_year_opening_workflow import (
    FiscalYearOpeningWorkflow,
)
from openbilanz.services.fiscal_year_transfer_service import (
    FiscalYearTransferService,
)
from openbilanz.services.posting_service import PostingService


@pytest.fixture
def postgres_opening_data():
    """Erzeugt isolierte Daten in der lokalen PostgreSQL-Testdatenbank."""

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
        name="PostgreSQL Geschäftsjahreseröffnung Test",
    )

    source_fiscal_year = FiscalYear(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )

    target_fiscal_year = FiscalYear(
        start_date=date(2027, 1, 1),
        end_date=date(2027, 12, 31),
    )

    account_types = {
        "1200": AccountType.ASSET,
        "1800": AccountType.EQUITY,
    }

    try:
        with Session() as session:
            company_repository = CompanyRepository(session)
            booking_repository = BookingRepository(session)

            company_repository.add(company)

            company_repository.add_fiscal_year(
                company.company_id,
                source_fiscal_year,
            )

            company_repository.add_fiscal_year(
                company.company_id,
                target_fiscal_year,
            )

            booking_repository.add(
                company_id=company.company_id,
                fiscal_year=source_fiscal_year,
                booking=Booking(
                    booking_date=date(2026, 12, 31),
                    description="Abschlusssalden",
                    lines=(
                        BookingLine(
                            account_number="1200",
                            side=EntrySide.DEBIT,
                            amount=Decimal("25000.00"),
                        ),
                        BookingLine(
                            account_number="1800",
                            side=EntrySide.CREDIT,
                            amount=Decimal("25000.00"),
                        ),
                    ),
                ),
            )

            company_repository.close_fiscal_year(
                company.company_id,
                source_fiscal_year,
            )

        yield (
            Session,
            company,
            source_fiscal_year,
            target_fiscal_year,
            account_types,
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
                    session.delete(company_model)
                    session.commit()
        finally:
            engine.dispose()


def _workflow(session):
    """Erstellt den Eröffnungsworkflow mit einer gemeinsamen Session."""

    return FiscalYearOpeningWorkflow(
        session=session,
        booking_repository=BookingRepository(session),
        company_repository=CompanyRepository(session),
        transfer_service=FiscalYearTransferService(
            opening_balance_account_number="9000",
            profit_account_number="8020",
            loss_account_number="8021",
            profit_loss_carryforward_account_number="2970",
        ),
        posting_service=PostingService(),
    )


def test_opening_lock_timeout_retry_and_duplicate_prevention(
    postgres_opening_data,
):
    """Sperrkonflikt verhindert Eröffnung; Wiederholung ist eindeutig."""

    (
        Session,
        company,
        source_fiscal_year,
        target_fiscal_year,
        account_types,
    ) = postgres_opening_data

    def open_year(session):
        return _workflow(session).open(
            company_id=company.company_id,
            source_fiscal_year=source_fiscal_year,
            target_fiscal_year=target_fiscal_year,
            account_types=account_types,
        )

    def opening_bookings(session):
        return tuple(
            booking
            for booking in BookingRepository(
                session
            ).list_for_fiscal_year(
                company_id=company.company_id,
                fiscal_year=target_fiscal_year,
            )
            if booking.booking_type is BookingType.OPENING
        )

    with Session() as session_a, Session() as session_b:
        CompanyRepository(session_a).lock_open_fiscal_year(
            company.company_id,
            target_fiscal_year,
        )

        try:
            with pytest.raises(DatabaseLockError):
                open_year(session_b)

            with Session() as check_session:
                assert opening_bookings(check_session) == ()

                target = next(
                    managed
                    for managed in CompanyRepository(
                        check_session
                    ).get_managed_fiscal_years(
                        company.company_id
                    )
                    if managed.fiscal_year == target_fiscal_year
                )

                assert target.opening_source is None

        finally:
            session_a.rollback()

        created_bookings = open_year(session_b)

        assert len(created_bookings) == 2

        with Session() as check_session:
            persisted = opening_bookings(check_session)

            assert len(persisted) == 2

            target = next(
                managed
                for managed in CompanyRepository(
                    check_session
                ).get_managed_fiscal_years(
                    company.company_id
                )
                if managed.fiscal_year == target_fiscal_year
            )

            assert target.opening_source == source_fiscal_year

        with pytest.raises(
            ValueError,
            match="Zielgeschäftsjahr wurde bereits eröffnet.",
        ):
            open_year(session_b)

        with Session() as check_session:
            assert len(opening_bookings(check_session)) == 2


def test_manual_opening_lock_timeout_retry_and_duplicate_prevention(
    postgres_opening_data,
):
    """Manuelle Eröffnung ist gegen konkurrierende Zugriffe geschützt."""

    (
        Session,
        company,
        _source_fiscal_year,
        target_fiscal_year,
        _account_types,
    ) = postgres_opening_data

    opening_booking = Booking(
        booking_date=target_fiscal_year.start_date,
        description="Manuelle Eröffnungsbilanz",
        booking_type=BookingType.OPENING,
        lines=(
            BookingLine(
                account_number="1200",
                side=EntrySide.DEBIT,
                amount=Decimal("25000.00"),
            ),
            BookingLine(
                account_number="9000",
                side=EntrySide.CREDIT,
                amount=Decimal("25000.00"),
            ),
        ),
    )

    def workspace(session):
        return FiscalYearWorkspace(
            context=ApplicationContext(
                company=company,
                fiscal_year=target_fiscal_year,
            ),
            booking_repository=BookingRepository(session),
            company_repository=CompanyRepository(session),
            posting_service=Mock(),
            closing_workflow=Mock(),
            closing_consistency_service=Mock(),
            e_bilanz_preparation_service=Mock(),
            e_bilanz_service=Mock(),
            e_bilanz_account_detail_service=Mock(),
            e_bilanz_export_service=Mock(),
            taxonomy_management_service=Mock(),
        )

    def opening_bookings(session):
        return tuple(
            booking
            for booking in BookingRepository(
                session
            ).list_for_fiscal_year(
                company_id=company.company_id,
                fiscal_year=target_fiscal_year,
            )
            if booking.booking_type is BookingType.OPENING
        )

    with Session() as session_a, Session() as session_b:
        CompanyRepository(session_a).lock_open_fiscal_year(
            company.company_id,
            target_fiscal_year,
        )

        try:
            with pytest.raises(DatabaseLockError):
                workspace(session_b).post_opening_balance(
                    (opening_booking,)
                )

            with Session() as check_session:
                assert opening_bookings(check_session) == ()

        finally:
            session_a.rollback()

        workspace(session_b).post_opening_balance(
            (opening_booking,)
        )

        with Session() as check_session:
            persisted = opening_bookings(check_session)

            assert len(persisted) == 1
            assert persisted[0].booking_id == opening_booking.booking_id

        with pytest.raises(
            ValueError,
            match="Eröffnungsbuchungen vorhanden",
        ):
            workspace(session_b).post_opening_balance(
                (opening_booking,)
            )

        with Session() as check_session:
            assert len(opening_bookings(check_session)) == 1

"""Integrationstests für den persistenten Jahresabschluss."""
import os
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal
from pathlib import Path
from threading import Event
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from simpleob.accounting.financial_statement_builder import (
    FinancialStatementBuilder,
)
from simpleob.accounting.hgb_financial_statement_position_provider import (
    HgbFinancialStatementPositionProvider,
)
from simpleob.accounting.income_statement import IncomeStatement
from simpleob.accounting.ledger import Ledger
from simpleob.accounting.mapper import AccountMapper
from simpleob.database.booking_repository import BookingRepository
from simpleob.database.company_repository import CompanyRepository
from simpleob.database.database import Base
from simpleob.domain.account_type import AccountType
from simpleob.domain.booking import Booking
from simpleob.domain.booking_line import BookingLine
from simpleob.domain.company import Company
from simpleob.domain.entry_side import EntrySide
from simpleob.domain.fiscal_year import FiscalYear
from simpleob.domain.fiscal_year_status import FiscalYearStatus
from simpleob.domain.journal import Journal
from simpleob.hgb.balance_sheet_structure import (
    create_hgb_balance_sheet_structure,
)
from simpleob.hgb.income_statement_structure import (
    create_hgb_income_statement_structure,
)
from simpleob.importers.csv_chart_of_accounts_importer import (
    CsvChartOfAccountsImporter,
)
from simpleob.services.closing_accounts import ClosingAccounts
from simpleob.services.closing_service import ClosingService
from simpleob.services.fiscal_year_closing_workflow import (
    FiscalYearClosingWorkflow,
)
from simpleob.services.posting_service import PostingService


def test_closes_fiscal_year_and_persists_closing_bookings() -> None:
    """Abschlussbuchungen und CLOSED-Status werden gemeinsam gespeichert."""

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

    assets, liabilities = (
        create_hgb_balance_sheet_structure()
    )
    income_statement_root = (
        create_hgb_income_statement_structure()
    )

    provider = HgbFinancialStatementPositionProvider(
        (
            assets,
            liabilities,
            income_statement_root,
        )
    )

    csv_file = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "simpleob"
        / "resources"
        / "chart_of_accounts"
        / "openbilanz_standard.csv"
    )

    chart_of_accounts = CsvChartOfAccountsImporter(
        position_provider=provider,
    ).load(csv_file)

    ledger = Ledger()
    posting_service = PostingService()

    revenue_booking = Booking(
        booking_date=date(2026, 6, 1),
        description="Umsatzerlös",
        lines=(
            BookingLine(
                account_number="1200",
                side=EntrySide.DEBIT,
                amount=Decimal("2000.00"),
            ),
            BookingLine(
                account_number="8400",
                side=EntrySide.CREDIT,
                amount=Decimal("2000.00"),
            ),
        ),
    )

    expense_booking = Booking(
        booking_date=date(2026, 6, 2),
        description="Büromaterial",
        lines=(
            BookingLine(
                account_number="4980",
                side=EntrySide.DEBIT,
                amount=Decimal("500.00"),
            ),
            BookingLine(
                account_number="1200",
                side=EntrySide.CREDIT,
                amount=Decimal("500.00"),
            ),
        ),
    )

    journal = Journal()

    for booking in (
        revenue_booking,
        expense_booking,
    ):
        posting_service.post_booking(
            booking=booking,
            journal=journal,
            ledger=ledger,
        )

    account_types = {
        account.account_number: account.account_type
        for account in chart_of_accounts.accounts
    }

    income_statement_balances = tuple(
        balance
        for balance in ledger.balances()
        if account_types.get(balance.account_number)
        in (
            AccountType.REVENUE,
            AccountType.EXPENSE,
        )
    )

    builder = FinancialStatementBuilder(
        AccountMapper(chart_of_accounts)
    )

    amounts = builder.build(
        balances=income_statement_balances,
        root_positions=(
            income_statement_root,
        ),
    )

    income_statement = IncomeStatement(
        income_statement=income_statement_root,
        amounts=amounts,
    )

    with Session() as session:
        company_repository = CompanyRepository(
            session
        )
        booking_repository = BookingRepository(
            session
        )

        company_repository.add(company)
        company_repository.add_fiscal_year(
            company.company_id,
            fiscal_year,
        )

        booking_repository.add(
            company_id=company.company_id,
            fiscal_year=fiscal_year,
            booking=revenue_booking,
        )
        booking_repository.add(
            company_id=company.company_id,
            fiscal_year=fiscal_year,
            booking=expense_booking,
        )

        closing_service = ClosingService(
            closing_accounts=ClosingAccounts(
                income_summary_account="8990",
                profit_account="8020",
                loss_account="8021",
            )
        )

        workflow = FiscalYearClosingWorkflow(
            session=session,
            booking_repository=booking_repository,
            company_repository=company_repository,
            closing_service=closing_service,
        )

        result = workflow.close(
            company_id=company.company_id,
            fiscal_year=fiscal_year,
            income_statement=income_statement,
            ledger=ledger,
            chart_of_accounts=chart_of_accounts,
            closing_date=date(2026, 12, 31),
        )

    assert result.net_income == Decimal("1500.00")

    with Session() as session:
        company_repository = CompanyRepository(
            session
        )
        booking_repository = BookingRepository(
            session
        )

        managed = (
            company_repository.get_managed_fiscal_years(
                company.company_id
            )
        )

        persisted_bookings = (
            booking_repository.list_for_fiscal_year(
                company_id=company.company_id,
                fiscal_year=fiscal_year,
            )
        )

    assert managed[0].status is FiscalYearStatus.CLOSED

    descriptions = {
        booking.description
        for booking in persisted_bookings
    }

    assert "Abschluss des Erlöskontos 8400" in descriptions
    assert "Abschluss des Aufwandskontos 4980" in descriptions
    assert "Abschluss des GuV-Kontos" in descriptions

def test_rolls_back_when_closing_booking_cannot_be_persisted() -> None:
    """Ein fehlgeschlagener Abschluss wird vollständig zurückgerollt."""

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

    assets, liabilities = (
        create_hgb_balance_sheet_structure()
    )
    income_statement_root = (
        create_hgb_income_statement_structure()
    )

    provider = HgbFinancialStatementPositionProvider(
        (
            assets,
            liabilities,
            income_statement_root,
        )
    )

    csv_file = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "simpleob"
        / "resources"
        / "chart_of_accounts"
        / "openbilanz_standard.csv"
    )

    chart_of_accounts = CsvChartOfAccountsImporter(
        position_provider=provider,
    ).load(csv_file)

    ledger = Ledger()
    journal = Journal()
    posting_service = PostingService()

    revenue_booking = Booking(
        booking_date=date(2026, 6, 1),
        description="Umsatzerlös",
        lines=(
            BookingLine(
                account_number="1200",
                side=EntrySide.DEBIT,
                amount=Decimal("2000.00"),
            ),
            BookingLine(
                account_number="8400",
                side=EntrySide.CREDIT,
                amount=Decimal("2000.00"),
            ),
        ),
    )

    expense_booking = Booking(
        booking_date=date(2026, 6, 2),
        description="Büromaterial",
        lines=(
            BookingLine(
                account_number="4980",
                side=EntrySide.DEBIT,
                amount=Decimal("500.00"),
            ),
            BookingLine(
                account_number="1200",
                side=EntrySide.CREDIT,
                amount=Decimal("500.00"),
            ),
        ),
    )

    for booking in (
        revenue_booking,
        expense_booking,
    ):
        posting_service.post_booking(
            booking=booking,
            journal=journal,
            ledger=ledger,
        )

    account_types = {
        account.account_number: account.account_type
        for account in chart_of_accounts.accounts
    }

    income_statement_balances = tuple(
        balance
        for balance in ledger.balances()
        if account_types.get(balance.account_number)
        in (
            AccountType.REVENUE,
            AccountType.EXPENSE,
        )
    )

    builder = FinancialStatementBuilder(
        AccountMapper(chart_of_accounts)
    )

    amounts = builder.build(
        balances=income_statement_balances,
        root_positions=(
            income_statement_root,
        ),
    )

    income_statement = IncomeStatement(
        income_statement=income_statement_root,
        amounts=amounts,
    )

    closing_service = ClosingService(
        closing_accounts=ClosingAccounts(
            income_summary_account="8990",
            profit_account="8020",
            loss_account="8021",
        )
    )

    class FailingBookingRepository(BookingRepository):
        """Scheitert kontrolliert beim zweiten Speicherversuch."""

        def __init__(self, session) -> None:
            super().__init__(session)
            self._add_count = 0

        def add(
            self,
            *,
            company_id,
            fiscal_year,
            booking,
            commit=True,
        ) -> None:
            self._add_count += 1

            if self._add_count == 2:
                raise ValueError(
                    "Simulierter Persistenzfehler"
                )

            super().add(
                company_id=company_id,
                fiscal_year=fiscal_year,
                booking=booking,
                commit=commit,
            )

    with Session() as session:
        company_repository = CompanyRepository(
            session
        )
        normal_booking_repository = BookingRepository(
            session
        )

        company_repository.add(company)
        company_repository.add_fiscal_year(
            company.company_id,
            fiscal_year,
        )

        normal_booking_repository.add(
            company_id=company.company_id,
            fiscal_year=fiscal_year,
            booking=revenue_booking,
        )

        normal_booking_repository.add(
            company_id=company.company_id,
            fiscal_year=fiscal_year,
            booking=expense_booking,
        )

        failing_booking_repository = (
            FailingBookingRepository(
                session
            )
        )

        workflow = FiscalYearClosingWorkflow(
            session=session,
            booking_repository=failing_booking_repository,
            company_repository=company_repository,
            closing_service=closing_service,
        )

        with pytest.raises(
            ValueError,
            match="Simulierter Persistenzfehler",
        ):
            workflow.close(
                company_id=company.company_id,
                fiscal_year=fiscal_year,
                income_statement=income_statement,
                ledger=ledger,
                chart_of_accounts=chart_of_accounts,
                closing_date=date(2026, 12, 31),
            )

    with Session() as session:
        company_repository = CompanyRepository(
            session
        )
        booking_repository = BookingRepository(
            session
        )

        managed = (
            company_repository.get_managed_fiscal_years(
                company.company_id
            )
        )

        persisted_bookings = (
            booking_repository.list_for_fiscal_year(
                company_id=company.company_id,
                fiscal_year=fiscal_year,
            )
        )

    assert managed[0].status is FiscalYearStatus.OPEN

    descriptions = {
        booking.description
        for booking in persisted_bookings
    }

    assert descriptions == {
        "Umsatzerlös",
        "Büromaterial",
    }

    assert (
        "Abschluss des Erlöskontos 8400"
        not in descriptions
    )

    assert (
        "Abschluss des Aufwandskontos 4980"
        not in descriptions
    )

    assert (
        "Abschluss des GuV-Kontos"
        not in descriptions
    )



def test_postgresql_closing_recalculates_stale_income_statement() -> None:
    """Der Abschluss verwendet aktuelle DB-Buchungen statt GUI-Altwerten."""

    database_url = os.environ.get("SIMPLEOB_TEST_POSTGRESQL_URL")

    if not database_url:
        pytest.skip(
            "SIMPLEOB_TEST_POSTGRESQL_URL ist nicht gesetzt."
        )

    parsed_url = make_url(database_url)

    if (
        parsed_url.get_backend_name() != "postgresql"
        or parsed_url.database != "simpleob_migration_test"
    ):
        pytest.fail(
            "Dieser Test darf ausschließlich gegen die PostgreSQL-"
            "Datenbank simpleob_migration_test ausgeführt werden."
        )

    engine = create_engine(database_url)
    Session = sessionmaker(bind=engine)

    company = Company(
        company_id=uuid4(),
        name="PostgreSQL Abschluss-Neuberechnung",
    )

    fiscal_year = FiscalYear(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )

    assets, liabilities = create_hgb_balance_sheet_structure()
    income_statement_root = create_hgb_income_statement_structure()

    provider = HgbFinancialStatementPositionProvider(
        (assets, liabilities, income_statement_root)
    )

    csv_file = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "simpleob"
        / "resources"
        / "chart_of_accounts"
        / "openbilanz_standard.csv"
    )

    chart_of_accounts = CsvChartOfAccountsImporter(
        position_provider=provider,
    ).load(csv_file)

    posting_service = PostingService()

    account_types = {
        account.account_number: account.account_type
        for account in chart_of_accounts.accounts
    }

    builder = FinancialStatementBuilder(
        AccountMapper(chart_of_accounts)
    )

    revenue_booking = Booking(
        booking_date=date(2026, 6, 1),
        description="Umsatzerlös",
        lines=(
            BookingLine(
                account_number="1200",
                side=EntrySide.DEBIT,
                amount=Decimal("2000.00"),
            ),
            BookingLine(
                account_number="8400",
                side=EntrySide.CREDIT,
                amount=Decimal("2000.00"),
            ),
        ),
    )

    expense_booking = Booking(
        booking_date=date(2026, 6, 2),
        description="Büromaterial",
        lines=(
            BookingLine(
                account_number="4980",
                side=EntrySide.DEBIT,
                amount=Decimal("500.00"),
            ),
            BookingLine(
                account_number="1200",
                side=EntrySide.CREDIT,
                amount=Decimal("500.00"),
            ),
        ),
    )

    late_expense_booking = Booking(
        booking_date=date(2026, 6, 3),
        description="Nachträglicher Aufwand",
        lines=(
            BookingLine(
                account_number="4980",
                side=EntrySide.DEBIT,
                amount=Decimal("200.00"),
            ),
            BookingLine(
                account_number="1200",
                side=EntrySide.CREDIT,
                amount=Decimal("200.00"),
            ),
        ),
    )

    try:
        with Session() as session:
            company_repository = CompanyRepository(session)
            booking_repository = BookingRepository(session)

            company_repository.add(company)
            company_repository.add_fiscal_year(
                company.company_id,
                fiscal_year,
            )

            for booking in (revenue_booking, expense_booking):
                booking_repository.add(
                    company_id=company.company_id,
                    fiscal_year=fiscal_year,
                    booking=booking,
                )

        # Der GUI-Datenstand kennt nur die ersten beiden Buchungen.
        stale_ledger = Ledger()

        for booking in (revenue_booking, expense_booking):
            posting_service.post_booking(
                booking=booking,
                ledger=stale_ledger,
            )

        stale_balances = tuple(
            balance
            for balance in stale_ledger.balances()
            if account_types.get(balance.account_number)
            in (AccountType.REVENUE, AccountType.EXPENSE)
        )

        stale_income_statement = IncomeStatement(
            income_statement=income_statement_root,
            amounts=builder.build(
                balances=stale_balances,
                root_positions=(income_statement_root,),
            ),
        )

        closing_service = ClosingService(
            closing_accounts=ClosingAccounts(
                income_summary_account="8990",
                profit_account="8020",
                loss_account="8021",
            )
        )

        assert closing_service.calculate_net_income(
            income_statement=stale_income_statement,
        ) == Decimal("1500.00")

        # Ein anderer Benutzer speichert danach eine zusätzliche Buchung.
        with Session() as session:
            BookingRepository(session).add(
                company_id=company.company_id,
                fiscal_year=fiscal_year,
                booking=late_expense_booking,
            )

        # Der Abschluss erhält absichtlich weiterhin den alten GUI-Stand.
        with Session() as session:
            company_repository = CompanyRepository(session)
            booking_repository = BookingRepository(session)

            workflow = FiscalYearClosingWorkflow(
                session=session,
                booking_repository=booking_repository,
                company_repository=company_repository,
                closing_service=closing_service,
                posting_service=posting_service,
                statement_builder=builder,
                income_statement_position=income_statement_root,
                account_types=account_types,
            )

            result = workflow.close(
                company_id=company.company_id,
                fiscal_year=fiscal_year,
                income_statement=stale_income_statement,
                ledger=stale_ledger,
                chart_of_accounts=chart_of_accounts,
                closing_date=date(2026, 12, 31),
            )

        assert result.net_income == Decimal("1300.00")

        with Session() as session:
            company_repository = CompanyRepository(session)
            booking_repository = BookingRepository(session)

            managed = company_repository.get_managed_fiscal_years(
                company.company_id
            )

            persisted_bookings = (
                booking_repository.list_for_fiscal_year(
                    company_id=company.company_id,
                    fiscal_year=fiscal_year,
                )
            )

        assert managed[0].status is FiscalYearStatus.CLOSED

        descriptions = {
            booking.description
            for booking in persisted_bookings
        }

        assert "Nachträglicher Aufwand" in descriptions
        assert "Abschluss des Erlöskontos 8400" in descriptions
        assert "Abschluss des Aufwandskontos 4980" in descriptions
        assert "Abschluss des GuV-Kontos" in descriptions

    finally:
        engine.dispose()




def test_postgresql_booking_is_rejected_after_concurrent_closing() -> None:
    """Eine während des Abschlusses blockierte Buchung wird abgewiesen."""

    database_url = os.environ.get("SIMPLEOB_TEST_POSTGRESQL_URL")

    if not database_url:
        pytest.skip(
            "SIMPLEOB_TEST_POSTGRESQL_URL ist nicht gesetzt."
        )

    parsed_url = make_url(database_url)

    if (
        parsed_url.get_backend_name() != "postgresql"
        or parsed_url.database != "simpleob_migration_test"
    ):
        pytest.fail(
            "Dieser Test darf ausschließlich gegen "
            "simpleob_migration_test ausgeführt werden."
        )

    engine = create_engine(database_url)
    Session = sessionmaker(bind=engine)

    company = Company(
        company_id=uuid4(),
        name="PostgreSQL Konkurrenztest Jahresabschluss",
    )

    fiscal_year = FiscalYear(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )

    booking = Booking(
        booking_date=date(2026, 6, 1),
        description="Buchung während Jahresabschluss",
        lines=(
            BookingLine(
                account_number="1200",
                side=EntrySide.DEBIT,
                amount=Decimal("100.00"),
            ),
            BookingLine(
                account_number="8400",
                side=EntrySide.CREDIT,
                amount=Decimal("100.00"),
            ),
        ),
    )

    lock_acquired = Event()
    booking_started = Event()

    def attempt_booking() -> tuple[int, str]:
        with Session() as session:
            repository = BookingRepository(session)

            if not lock_acquired.wait(timeout=10):
                raise AssertionError(
                    "Der Abschluss hat die Sperre nicht erworben."
                )

            backend_pid = session.execute(
                text("SELECT pg_backend_pid()")
            ).scalar_one()

            booking_started.set()

            try:
                repository.add(
                    company_id=company.company_id,
                    fiscal_year=fiscal_year,
                    booking=booking,
                )
            except ValueError as exc:
                session.rollback()
                return backend_pid, str(exc)

            raise AssertionError(
                "Die Buchung wurde trotz abgeschlossenem "
                "Geschäftsjahr gespeichert."
            )

    try:
        with Session() as session:
            company_repository = CompanyRepository(session)

            company_repository.add(company)
            company_repository.add_fiscal_year(
                company.company_id,
                fiscal_year,
            )

        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(attempt_booking)

            with Session() as closing_session:
                company_repository = CompanyRepository(
                    closing_session
                )

                company_repository.lock_open_fiscal_year(
                    company.company_id,
                    fiscal_year,
                )

                lock_acquired.set()

                assert booking_started.wait(timeout=10)

                # Die wartende Verbindung anhand ihrer PostgreSQL-PID
                # identifizieren. Die PID wird vor repository.add()
                # abgefragt und über eine eigene Verbindung ermittelt.
                with engine.connect() as observer:
                    deadline = time.monotonic() + 10
                    blocked_pid = None

                    while time.monotonic() < deadline:
                        blocked_pid = observer.execute(
                            text(
                                """
                                SELECT pid
                                FROM pg_stat_activity
                                WHERE datname = current_database()
                                  AND pid <> pg_backend_pid()
                                  AND wait_event_type = 'Lock'
                                  AND query ILIKE
                                      '%FOR UPDATE%'
                                LIMIT 1
                                """
                            )
                        ).scalar_one_or_none()

                        if blocked_pid is not None:
                            break

                        time.sleep(0.05)

                    assert blocked_pid is not None, (
                        "Keine auf eine PostgreSQL-Sperre "
                        "wartende Buchung beobachtet."
                    )

                # Die Geschäftsjahressperre bleibt bis zum Commit
                # bestehen.
                company_repository.close_fiscal_year(
                    company.company_id,
                    fiscal_year,
                    commit=False,
                )

                closing_session.commit()

            backend_pid, error_message = future.result(timeout=10)

        assert backend_pid == blocked_pid
        assert (
            "Das Geschäftsjahr ist abgeschlossen."
            in error_message
        )

        with Session() as session:
            company_repository = CompanyRepository(session)
            booking_repository = BookingRepository(session)

            managed = company_repository.get_managed_fiscal_years(
                company.company_id
            )

            persisted_bookings = (
                booking_repository.list_for_fiscal_year(
                    company_id=company.company_id,
                    fiscal_year=fiscal_year,
                )
            )

        assert managed[0].status is FiscalYearStatus.CLOSED
        assert persisted_bookings == ()

    finally:
        engine.dispose()

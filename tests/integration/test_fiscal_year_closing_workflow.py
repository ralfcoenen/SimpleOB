"""Integrationstests für den persistenten Jahresabschluss."""
from datetime import date
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from openbilanz.accounting.financial_statement_builder import (
    FinancialStatementBuilder,
)
from openbilanz.accounting.hgb_financial_statement_position_provider import (
    HgbFinancialStatementPositionProvider,
)
from openbilanz.accounting.income_statement import IncomeStatement
from openbilanz.accounting.ledger import Ledger
from openbilanz.accounting.mapper import AccountMapper
from openbilanz.database.booking_repository import BookingRepository
from openbilanz.database.company_repository import CompanyRepository
from openbilanz.database.database import Base
from openbilanz.domain.account_type import AccountType
from openbilanz.domain.booking import Booking
from openbilanz.domain.booking_line import BookingLine
from openbilanz.domain.company import Company
from openbilanz.domain.entry_side import EntrySide
from openbilanz.domain.fiscal_year import FiscalYear
from openbilanz.domain.fiscal_year_status import FiscalYearStatus
from openbilanz.domain.journal import Journal
from openbilanz.hgb.balance_sheet_structure import (
    create_hgb_balance_sheet_structure,
)
from openbilanz.hgb.income_statement_structure import (
    create_hgb_income_statement_structure,
)
from openbilanz.importers.csv_chart_of_accounts_importer import (
    CsvChartOfAccountsImporter,
)
from openbilanz.services.closing_accounts import ClosingAccounts
from openbilanz.services.closing_service import ClosingService
from openbilanz.services.fiscal_year_closing_workflow import (
    FiscalYearClosingWorkflow,
)
from openbilanz.services.posting_service import PostingService


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
        / "openbilanz"
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
        / "openbilanz"
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


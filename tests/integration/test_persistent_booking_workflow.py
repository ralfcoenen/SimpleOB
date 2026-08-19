"""Integrationstest für persistierte Buchungen."""

from datetime import date
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from openbilanz.accounting.balance_sheet import BalanceSheet
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
from openbilanz.domain.chart_of_accounts_template import (
    ChartOfAccountsTemplate,
)
from openbilanz.domain.company import Company
from openbilanz.domain.entry_side import EntrySide
from openbilanz.domain.fiscal_year import FiscalYear
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
from openbilanz.services.closing_result import ClosingResult
from openbilanz.services.closing_service import ClosingService
from openbilanz.services.posting_service import PostingService


def test_reconstructs_journal_and_ledger_from_persisted_bookings() -> None:
    """Persistierte Buchungen rekonstruieren Journal und Ledger."""

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

    opening_booking = Booking(
        booking_date=date(2026, 1, 1),
        voucher_no="EB-001",
        description="Eröffnung Bank",
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

    expense_booking = Booking(
        booking_date=date(2026, 8, 8),
        voucher_no="RE-001",
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

    revenue_booking = Booking(
        booking_date=date(2026, 8, 9),
        voucher_no="AR-001",
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

    with Session() as session:
        company_repository = CompanyRepository(
            session
        )
        booking_repository = BookingRepository(
            session
        )

        company_repository.add(
            company
        )
        company_repository.add_fiscal_year(
            company.company_id,
            fiscal_year,
        )

        for booking in (
            opening_booking,
            expense_booking,
            revenue_booking,
        ):
            booking_repository.add(
                company_id=company.company_id,
                fiscal_year=fiscal_year,
                booking=booking,
            )

    journal = Journal()
    ledger = Ledger()
    posting_service = PostingService()

    with Session() as session:
        booking_repository = BookingRepository(
            session
        )

        loaded_bookings = (
            booking_repository.list_for_fiscal_year(
                company_id=company.company_id,
                fiscal_year=fiscal_year,
            )
        )

        for booking in loaded_bookings:
            posting_service.post_booking(
                booking=booking,
                journal=journal,
                ledger=ledger,
            )

    assert journal.bookings == (
        opening_booking,
        expense_booking,
        revenue_booking,
    )

    bank = ledger.get_account("1200")
    office_supplies = ledger.get_account("4980")
    revenue = ledger.get_account("8400")
    opening_balance_account = ledger.get_account("9000")

    assert bank.debit == Decimal("27000.00")
    assert bank.credit == Decimal("500.00")
    assert bank.debit_balance == Decimal("26500.00")

    assert office_supplies.debit_balance == Decimal("500.00")
    assert revenue.credit_balance == Decimal("2000.00")
    assert opening_balance_account.credit_balance == Decimal("25000.00")

    assert ledger.is_balanced
    
def test_reconstructs_income_statement_and_balance_sheet() -> None:
    """Persistierte Buchungen rekonstruieren GuV und Bilanz."""

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

    bookings = (
        Booking(
            booking_date=date(2026, 1, 1),
            description="Eröffnung Bank",
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
        ),
        Booking(
            booking_date=date(2026, 1, 1),
            description="Eröffnung Verbindlichkeiten",
            lines=(
                BookingLine(
                    account_number="9000",
                    side=EntrySide.DEBIT,
                    amount=Decimal("8000.00"),
                ),
                BookingLine(
                    account_number="1600",
                    side=EntrySide.CREDIT,
                    amount=Decimal("8000.00"),
                ),
            ),
        ),
        Booking(
            booking_date=date(2026, 1, 1),
            description="Eröffnung Eigenkapital",
            lines=(
                BookingLine(
                    account_number="9000",
                    side=EntrySide.DEBIT,
                    amount=Decimal("17000.00"),
                ),
                BookingLine(
                    account_number="0800",
                    side=EntrySide.CREDIT,
                    amount=Decimal("17000.00"),
                ),
            ),
        ),
        Booking(
            booking_date=date(2026, 8, 8),
            description="Büromaterial",
            lines=(
                BookingLine(
                    account_number="4930",
                    side=EntrySide.DEBIT,
                    amount=Decimal("500.00"),
                ),
                BookingLine(
                    account_number="1200",
                    side=EntrySide.CREDIT,
                    amount=Decimal("500.00"),
                ),
            ),
        ),
        Booking(
            booking_date=date(2026, 8, 9),
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
        ),
    )

    with Session() as session:
        company_repository = CompanyRepository(
            session
        )
        booking_repository = BookingRepository(
            session
        )

        company_repository.add(
            company
        )
        company_repository.add_fiscal_year(
            company.company_id,
            fiscal_year,
        )

        for booking in bookings:
            booking_repository.add(
                company_id=company.company_id,
                fiscal_year=fiscal_year,
                booking=booking,
            )

    journal = Journal()
    ledger = Ledger()
    posting_service = PostingService()

    with Session() as session:
        booking_repository = BookingRepository(
            session
        )

        loaded_bookings = (
            booking_repository.list_for_fiscal_year(
                company_id=company.company_id,
                fiscal_year=fiscal_year,
            )
        )

        for booking in loaded_bookings:
            posting_service.post_booking(
                booking=booking,
                journal=journal,
                ledger=ledger,
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
        ),
    )

    csv_file = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "openbilanz"
        / "resources"
        / "chart_of_accounts"
        / "openbilanz_standard.csv"
    )

    chart_of_accounts: ChartOfAccountsTemplate = (
        CsvChartOfAccountsImporter(
            position_provider=provider,
        ).load(csv_file)
    )

    account_types = {
        account.account_number: account.account_type
        for account in chart_of_accounts.accounts
    }

    builder = FinancialStatementBuilder(
        AccountMapper(chart_of_accounts)
    )

    income_statement_balances = tuple(
        balance
        for balance in ledger.balances()
        if account_types.get(
            balance.account_number
        )
        in (
            AccountType.REVENUE,
            AccountType.EXPENSE,
        )
    )

    income_statement_amounts = builder.build(
        balances=income_statement_balances,
        root_positions=(
            income_statement_root,
        ),
    )

    income_statement = IncomeStatement(
        income_statement=income_statement_root,
        amounts=income_statement_amounts,
    )

    net_income = ClosingService().calculate_net_income(
        income_statement=income_statement,
    )

    assert net_income == Decimal("1500.00")

    equity = next(
        position
        for position in liabilities.children
        if position.code == "HGB.266.PASSIVA.A"
    )

    result_position = next(
        position
        for position in equity.children
        if position.code == "HGB.266.PASSIVA.A.V"
    )

    balance_sheet_balances = tuple(
        balance
        for balance in ledger.balances()
        if account_types.get(
            balance.account_number
        )
        in (
            AccountType.ASSET,
            AccountType.LIABILITY,
            AccountType.EQUITY,
        )
        and balance.account_number != "9000"
    )

    amounts = builder.build(
        balances=balance_sheet_balances,
        root_positions=(
            assets,
            liabilities,
        ),
        closing_result=ClosingResult(
            net_income=net_income,
        ),
        result_position=result_position,
    )

    balance_sheet = BalanceSheet(
        assets=assets,
        liabilities=liabilities,
        amounts=amounts,
    )

    assert balance_sheet.is_balanced()
    assert balance_sheet.amount_for(
        assets
    ) == Decimal("26500.00")
    assert balance_sheet.amount_for(
        liabilities
    ) == Decimal("26500.00")

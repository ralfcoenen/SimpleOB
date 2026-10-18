"""Integrationstest für Jahresabschluss und Jahresüberleitung."""

from datetime import date
from decimal import Decimal
from pathlib import Path

from simpleob.accounting.financial_statement_builder import (
    FinancialStatementBuilder,
)
from simpleob.accounting.hgb_financial_statement_position_provider import (
    HgbFinancialStatementPositionProvider,
)
from simpleob.accounting.income_statement import IncomeStatement
from simpleob.accounting.ledger import Ledger
from simpleob.accounting.mapper import AccountMapper
from simpleob.domain.account_type import AccountType
from simpleob.domain.booking import Booking
from simpleob.domain.booking_line import BookingLine
from simpleob.domain.entry_side import EntrySide
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
from simpleob.services.fiscal_year_transfer_service import (
    FiscalYearTransferService,
)
from simpleob.services.posting_service import PostingService


def test_closes_profit_and_transfers_it_to_next_fiscal_year() -> None:
    """Ein Jahresüberschuss wird als Gewinnvortrag übernommen."""

    ledger_2026 = Ledger()
    journal_2026 = Journal()
    posting_service = PostingService()

    bookings_2026 = (
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
            booking_date=date(2026, 8, 8),
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

    for booking in bookings_2026:
        posting_service.post_booking(
            booking=booking,
            journal=journal_2026,
            ledger=ledger_2026,
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

    account_types = {
        account.account_number: account.account_type
        for account in chart_of_accounts.accounts
    }

    builder = FinancialStatementBuilder(
        AccountMapper(chart_of_accounts)
    )

    income_statement_balances = tuple(
        balance
        for balance in ledger_2026.balances()
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

    closing_service = ClosingService(
        closing_accounts=ClosingAccounts(
            income_summary_account="8990",
            profit_account="8020",
            loss_account="8021",
        )
    )

    closing_result = closing_service.close(
        income_statement=income_statement,
        ledger=ledger_2026,
        chart_of_accounts=chart_of_accounts,
        closing_date=date(2026, 12, 31),
    )

    assert closing_result.net_income == Decimal("1500.00")

    for booking in closing_result.bookings:
        posting_service.post_booking(
            booking=booking,
            journal=journal_2026,
            ledger=ledger_2026,
        )

    balances = {
        balance.account_number: balance
        for balance in ledger_2026.balances()
    }

    assert balances["8400"].credit_balance == Decimal("0.00")
    assert balances["4980"].debit_balance == Decimal("0.00")

    assert balances["8990"].debit_balance == Decimal("0.00")
    assert balances["8990"].credit_balance == Decimal("0.00")

    assert balances["8020"].credit_balance == Decimal("1500.00")

    transfer_service = FiscalYearTransferService(
        opening_balance_account_number="9000",
        profit_account_number="8020",
        loss_account_number="8021",
        profit_loss_carryforward_account_number="2970",
    )

    transfer_bookings = transfer_service.create_opening_bookings(
        ledger=ledger_2026,
        account_types=account_types,
        opening_date=date(2027, 1, 1),
    )

    transferred_accounts = {
        line.account_number
        for booking in transfer_bookings
        for line in booking.lines
    }

    assert "1200" in transferred_accounts
    assert "2970" in transferred_accounts

    assert "8020" not in transferred_accounts
    assert "8021" not in transferred_accounts
    assert "8400" not in transferred_accounts
    assert "4980" not in transferred_accounts
    assert "8990" not in transferred_accounts

    ledger_2027 = Ledger()
    journal_2027 = Journal()

    for booking in transfer_bookings:
        posting_service.post_booking(
            booking=booking,
            journal=journal_2027,
            ledger=ledger_2027,
        )

    balances_2027 = {
        balance.account_number: balance
        for balance in ledger_2027.balances()
    }

    assert (
        balances_2027["1200"].debit_balance
        == Decimal("26500.00")
    )
    assert (
        balances_2027["2970"].credit_balance
        == Decimal("1500.00")
    )

    assert "8020" not in balances_2027
    assert "8021" not in balances_2027
    assert "8400" not in balances_2027
    assert "4980" not in balances_2027
    assert "8990" not in balances_2027


def test_closes_loss_and_transfers_it_to_next_fiscal_year() -> None:
    """Ein Jahresfehlbetrag wird als Verlustvortrag übernommen."""

    ledger_2026 = Ledger()
    journal_2026 = Journal()
    posting_service = PostingService()

    bookings_2026 = (
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
            booking_date=date(2026, 8, 8),
            description="Büromaterial",
            lines=(
                BookingLine(
                    account_number="4980",
                    side=EntrySide.DEBIT,
                    amount=Decimal("2000.00"),
                ),
                BookingLine(
                    account_number="1200",
                    side=EntrySide.CREDIT,
                    amount=Decimal("2000.00"),
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
                    amount=Decimal("500.00"),
                ),
                BookingLine(
                    account_number="8400",
                    side=EntrySide.CREDIT,
                    amount=Decimal("500.00"),
                ),
            ),
        ),
    )

    for booking in bookings_2026:
        posting_service.post_booking(
            booking=booking,
            journal=journal_2026,
            ledger=ledger_2026,
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

    account_types = {
        account.account_number: account.account_type
        for account in chart_of_accounts.accounts
    }

    builder = FinancialStatementBuilder(
        AccountMapper(chart_of_accounts)
    )

    income_statement_balances = tuple(
        balance
        for balance in ledger_2026.balances()
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

    closing_service = ClosingService(
        closing_accounts=ClosingAccounts(
            income_summary_account="8990",
            profit_account="8020",
            loss_account="8021",
        )
    )

    closing_result = closing_service.close(
        income_statement=income_statement,
        ledger=ledger_2026,
        chart_of_accounts=chart_of_accounts,
        closing_date=date(2026, 12, 31),
    )

    assert closing_result.net_income == Decimal("-1500.00")

    for booking in closing_result.bookings:
        posting_service.post_booking(
            booking=booking,
            journal=journal_2026,
            ledger=ledger_2026,
        )

    balances = {
        balance.account_number: balance
        for balance in ledger_2026.balances()
    }

    assert balances["8400"].credit_balance == Decimal("0.00")
    assert balances["4980"].debit_balance == Decimal("0.00")

    assert balances["8990"].debit_balance == Decimal("0.00")
    assert balances["8990"].credit_balance == Decimal("0.00")

    assert balances["8021"].debit_balance == Decimal("1500.00")

    transfer_service = FiscalYearTransferService(
        opening_balance_account_number="9000",
        profit_account_number="8020",
        loss_account_number="8021",
        profit_loss_carryforward_account_number="2970",
    )

    transfer_bookings = transfer_service.create_opening_bookings(
        ledger=ledger_2026,
        account_types=account_types,
        opening_date=date(2027, 1, 1),
    )

    transferred_accounts = {
        line.account_number
        for booking in transfer_bookings
        for line in booking.lines
    }

    assert "1200" in transferred_accounts
    assert "2970" in transferred_accounts

    assert "8020" not in transferred_accounts
    assert "8021" not in transferred_accounts
    assert "8400" not in transferred_accounts
    assert "4980" not in transferred_accounts
    assert "8990" not in transferred_accounts

    ledger_2027 = Ledger()
    journal_2027 = Journal()

    for booking in transfer_bookings:
        posting_service.post_booking(
            booking=booking,
            journal=journal_2027,
            ledger=ledger_2027,
        )

    balances_2027 = {
        balance.account_number: balance
        for balance in ledger_2027.balances()
    }

    assert (
        balances_2027["1200"].debit_balance
        == Decimal("23500.00")
    )
    assert (
        balances_2027["2970"].debit_balance
        == Decimal("1500.00")
    )

    assert "8020" not in balances_2027
    assert "8021" not in balances_2027
    assert "8400" not in balances_2027
    assert "4980" not in balances_2027
    assert "8990" not in balances_2027

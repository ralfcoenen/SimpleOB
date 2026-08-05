"""
Erster End-to-End-Integrationstest.

Geschäftsfall:
Gründung einer Unternehmergesellschaft (UG)
durch Einzahlung des Stammkapitals auf das Bankkonto.

Dieser Test überprüft die vollständige Verarbeitungskette
vom Buchungssatz bis zur erzeugten Handelsbilanz.
"""

from datetime import date
from decimal import Decimal

from openbilanz.accounting.balance_sheet import BalanceSheet
from openbilanz.accounting.financial_statement_builder import (
    FinancialStatementBuilder,
)
from openbilanz.accounting.ledger import Ledger
from openbilanz.accounting.mapper import AccountMapper
from openbilanz.accounting.trial_balance import TrialBalance
from openbilanz.domain.account_mapping_rule import AccountMappingRule
from openbilanz.domain.account_type import AccountType
from openbilanz.domain.booking import Booking
from openbilanz.domain.booking_line import BookingLine
from openbilanz.domain.chart_of_accounts_template import (
    ChartOfAccountsTemplate,
)
from openbilanz.domain.entry_side import EntrySide
from openbilanz.domain.journal import Journal
from openbilanz.domain.template_account import TemplateAccount
from openbilanz.hgb.balance_sheet_structure import (
    create_hgb_balance_sheet_structure,
)
from openbilanz.services.posting_service import PostingService


def test_creates_first_balance_sheet_from_capital_contribution() -> None:
    assets, liabilities = create_hgb_balance_sheet_structure()

    current_assets = next(
        position
        for position in assets.children
        if position.code == "HGB.266.AKTIVA.B"
    )
    cash_and_bank = next(
        position
        for position in current_assets.children
        if position.code == "HGB.266.AKTIVA.B.IV"
    )

    equity = next(
        position
        for position in liabilities.children
        if position.code == "HGB.266.PASSIVA.A"
    )
    subscribed_capital = next(
        position
        for position in equity.children
        if position.code == "HGB.266.PASSIVA.A.I"
    )

    bank_account = TemplateAccount(
        account_number="1200",
        name="Bank",
        account_type=AccountType.ASSET,
    )
    subscribed_capital_account = TemplateAccount(
        account_number="0800",
        name="Gezeichnetes Kapital",
        account_type=AccountType.EQUITY,
    )

    chart_of_accounts = ChartOfAccountsTemplate(
        name="Integrationstest-Kontenrahmen",
        accounts=(
            subscribed_capital_account,
            bank_account,
        ),
        account_mapping_rules=(
            AccountMappingRule(
                account_number="1200",
                debit_position=cash_and_bank,
                credit_position=None,
            ),
            AccountMappingRule(
                account_number="0800",
                debit_position=None,
                credit_position=subscribed_capital,
            ),
        ),
    )

    capital_contribution = Booking(
        booking_date=date(2026, 1, 2),
        voucher_no="GR-001",
        description="Einzahlung des Stammkapitals",
        lines=(
            BookingLine(
                account_number="1200",
                side=EntrySide.DEBIT,
                amount=Decimal("1000.00"),
            ),
            BookingLine(
                account_number="0800",
                side=EntrySide.CREDIT,
                amount=Decimal("1000.00"),
            ),
        ),
    )

    journal = Journal()
    ledger = Ledger()

    PostingService().post_booking(
        booking=capital_contribution,
        journal=journal,
        ledger=ledger,
    )

    trial_balance = TrialBalance(ledger)

    builder = FinancialStatementBuilder(
        AccountMapper(chart_of_accounts)
    )
    amounts = builder.build(
        balances=ledger.balances(),
        root_positions=(assets, liabilities),
    )

    balance_sheet = BalanceSheet(
        assets=assets,
        liabilities=liabilities,
        amounts=amounts,
    )

    assert journal.bookings == (capital_contribution,)

    assert trial_balance.is_turnover_balanced
    assert trial_balance.is_balance_balanced
    assert trial_balance.debit_balance_total == Decimal("1000.00")
    assert trial_balance.credit_balance_total == Decimal("1000.00")

    assert balance_sheet.amount_for(cash_and_bank) == Decimal("1000.00")
    assert balance_sheet.amount_for(subscribed_capital) == Decimal("1000.00")

    assert balance_sheet.amount_for(assets) == Decimal("1000.00")
    assert balance_sheet.amount_for(liabilities) == Decimal("1000.00")
    assert balance_sheet.is_balanced()
    
    
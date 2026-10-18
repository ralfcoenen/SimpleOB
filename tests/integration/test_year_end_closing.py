from datetime import date
from decimal import Decimal

from simpleob.accounting.balance_sheet import BalanceSheet
from simpleob.accounting.financial_statement_builder import (
    FinancialStatementBuilder,
)
from simpleob.accounting.income_statement import IncomeStatement
from simpleob.accounting.ledger import Ledger
from simpleob.accounting.mapper import AccountMapper
from simpleob.accounting.trial_balance import TrialBalance
from simpleob.domain.account_mapping_rule import AccountMappingRule
from simpleob.domain.account_type import AccountType
from simpleob.domain.booking import Booking
from simpleob.domain.booking_line import BookingLine
from simpleob.domain.chart_of_accounts_template import (
    ChartOfAccountsTemplate,
)
from simpleob.domain.entry_side import EntrySide
from simpleob.domain.journal import Journal
from simpleob.domain.template_account import TemplateAccount
from simpleob.hgb.balance_sheet_structure import (
    create_hgb_balance_sheet_structure,
)
from simpleob.hgb.income_statement_structure import (
    create_hgb_income_statement_structure,
)
from simpleob.services.closing_service import ClosingService
from simpleob.services.posting_service import PostingService


def test_year_end_closing_calculates_net_income() -> None:
    income_statement_root = create_hgb_income_statement_structure()
    
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

    net_income_position = next(
        position
        for position in equity.children
        if position.code == "HGB.266.PASSIVA.A.V"
    )

    revenue_position = next(
        position
        for position in income_statement_root.children
        if position.code == "HGB.275.GKV.1"
    )
    expense_position = next(
        position
        for position in income_statement_root.children
        if position.code == "HGB.275.GKV.8"
    )

    bank_account = TemplateAccount(
        account_number="1200",
        name="Bank",
        account_type=AccountType.ASSET,
    )
    revenue_account = TemplateAccount(
        account_number="8400",
        name="Umsatzerlöse",
        account_type=AccountType.REVENUE,
    )
    expense_account = TemplateAccount(
        account_number="4930",
        name="Sonstige betriebliche Aufwendungen",
        account_type=AccountType.EXPENSE,
    )

    chart_of_accounts = ChartOfAccountsTemplate(
        name="Integrationstest-GuV",
        accounts=(
            bank_account,
            expense_account,
            revenue_account,
        ),
        account_mapping_rules=(
            AccountMappingRule(
                account_number="8400",
                debit_position=None,
                credit_position=revenue_position,
            ),
            AccountMappingRule(
                account_number="1200",
                debit_position=cash_and_bank,
                credit_position=None,
            ),
            AccountMappingRule(
                account_number="4930",
                debit_position=expense_position,
                credit_position=None,
            ),
        ),
    )

    revenue_booking = Booking(
        booking_date=date(2026, 1, 10),
        voucher_no="AR-001",
        description="Erbrachte Dienstleistung",
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
    )

    expense_booking = Booking(
        booking_date=date(2026, 1, 15),
        voucher_no="ER-001",
        description="Betrieblicher Aufwand",
        lines=(
            BookingLine(
                account_number="4930",
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

    journal = Journal()
    ledger = Ledger()
    posting_service = PostingService()

    posting_service.post_booking(
        booking=revenue_booking,
        journal=journal,
        ledger=ledger,
    )
    posting_service.post_booking(
        booking=expense_booking,
        journal=journal,
        ledger=ledger,
    )

    trial_balance = TrialBalance(ledger)

    builder = FinancialStatementBuilder(
        AccountMapper(chart_of_accounts)
    )

    guv_balances = tuple(
        balance
        for balance in ledger.balances()
        if balance.account_number in {"8400", "4930"}
    )

    amounts = builder.build(
        balances=guv_balances,
        root_positions=(income_statement_root,),
    )

    income_statement = IncomeStatement(
        income_statement=income_statement_root,
        amounts=amounts,
    )

    closing_result = ClosingService().close(
        income_statement=income_statement,
    )
    
    
    balance_builder = FinancialStatementBuilder(
        AccountMapper(chart_of_accounts)
    )

    balance_sheet_amounts = balance_builder.build(
        balances=tuple(
            balance
            for balance in ledger.balances()
            if balance.account_number == "1200"
        ),
        root_positions=(
            assets,
            liabilities,
        ),
        closing_result=closing_result,
        result_position=net_income_position,
    )

    balance_sheet = BalanceSheet(
        assets=assets,
        liabilities=liabilities,
        amounts=balance_sheet_amounts,
    )

    assert journal.bookings == (
        revenue_booking,
        expense_booking,
    )

    assert trial_balance.is_turnover_balanced
    assert trial_balance.is_balance_balanced

    assert income_statement.amount_for(
        revenue_position
    ) == Decimal("500.00")
    assert income_statement.amount_for(
        expense_position
    ) == Decimal("200.00")

    assert closing_result.net_income == Decimal("300.00")
    
    assert balance_sheet.amount_for(
        net_income_position
    ) == Decimal("300.00")   
    
    assert balance_sheet.amount_for(assets) == Decimal("300.00")
    assert balance_sheet.amount_for(liabilities) == Decimal("300.00")
    assert balance_sheet.is_balanced()
    
    
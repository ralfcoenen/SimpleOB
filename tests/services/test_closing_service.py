from datetime import date
from decimal import Decimal

from openbilanz.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
from openbilanz.accounting.income_statement import IncomeStatement
from openbilanz.accounting.ledger import Ledger
from openbilanz.accounting.statement_category import StatementCategory
from openbilanz.domain.account_type import AccountType
from openbilanz.domain.booking_line import BookingLine
from openbilanz.domain.booking_type import BookingType
from openbilanz.domain.chart_of_accounts_template import (
    ChartOfAccountsTemplate,
)
from openbilanz.domain.entry_side import EntrySide
from openbilanz.domain.template_account import TemplateAccount
from openbilanz.hgb.income_statement_structure import (
    create_hgb_income_statement_structure,
)
from openbilanz.services.closing_accounts import ClosingAccounts
from openbilanz.services.closing_result import ClosingResult
from openbilanz.services.closing_service import ClosingService


def test_calculates_net_income_from_income_and_expenses() -> None:
    service = ClosingService()

    net_income = service.calculate_net_income(
        income=Decimal("500.00"),
        expenses=Decimal("200.00"),
    )

    assert net_income == Decimal("300.00")
    
def test_calculates_net_loss_when_expenses_exceed_income() -> None:
    service = ClosingService()

    net_income = service.calculate_net_income(
        income=Decimal("200.00"),
        expenses=Decimal("500.00"),
    )

    assert net_income == Decimal("-300.00")
    
def test_calculates_net_income_from_income_statement() -> None:
    
    revenue = FinancialStatementPosition(
        code="HGB.275.GKV.1",
        name="Umsatzerlöse",
        category=StatementCategory.INCOME,
    )

    expenses = FinancialStatementPosition(
        code="HGB.275.GKV.8",
        name="Sonstige betriebliche Aufwendungen",
        category=StatementCategory.EXPENSE,
    )

    income_statement = IncomeStatement(
        income_statement=FinancialStatementPosition(
            code="HGB.275.GKV",
            name=(
                "Gewinn- und Verlustrechnung "
                "nach dem Gesamtkostenverfahren"
            ),
            children=(
                revenue,
                expenses,
            ),
        ),
        amounts={
            revenue: Decimal("500.00"),
            expenses: Decimal("200.00"),
        },
    )

    net_income = ClosingService().calculate_net_income(
        income_statement=income_statement,
    )

    assert net_income == Decimal("300.00")
    



def test_close_returns_closing_result() -> None:
    revenue = FinancialStatementPosition(
        code="HGB.275.GKV.1",
        name="Umsatzerlöse",
        category=StatementCategory.INCOME,
    )

    expense = FinancialStatementPosition(
        code="HGB.275.GKV.8",
        name="Sonstige betriebliche Aufwendungen",
        category=StatementCategory.EXPENSE,
    )

    income_statement = IncomeStatement(
        income_statement=FinancialStatementPosition(
            code="HGB.275.GKV",
            name="GuV",
            children=(revenue, expense),
        ),
        amounts={
            revenue: Decimal("500.00"),
            expense: Decimal("200.00"),
        },
    )

    result = ClosingService().close(
        income_statement=income_statement,
    )

    assert isinstance(result, ClosingResult)
    assert result.net_income == Decimal("300.00")

def test_close_accepts_ledger() -> None:
    service = ClosingService(
        closing_accounts=ClosingAccounts(
            income_summary_account="8990",
            profit_account="8020",
            loss_account="8021",
        ),
    )

    ledger = Ledger()

    income_statement = IncomeStatement(
        income_statement=FinancialStatementPosition(
            code="HGB.275.GKV",
            name="GuV",
        ),
        amounts={},
    )

    result = service.close(
        ledger=ledger,
        income_statement=income_statement,
    )

    assert result.net_income == Decimal("0.00")

def test_close_creates_closing_booking_for_revenue_account() -> None:
    closing_accounts = ClosingAccounts(
        income_summary_account="8990",
        profit_account="8020",
        loss_account="8021",
    )

    chart_of_accounts = ChartOfAccountsTemplate(
        name="Abschlusstest",
        accounts=(
            TemplateAccount(
                account_number="8400",
                name="Umsatzerlöse",
                account_type=AccountType.REVENUE,
            ),
        ),
        account_mapping_rules=(),
    )

    ledger = Ledger()
    ledger.post(
        debit_account="1200",
        credit_account="8400",
        amount=Decimal("500.00"),
    )

    income_statement = IncomeStatement(
        income_statement=FinancialStatementPosition(
            code="HGB.275.GKV",
            name="GuV",
        ),
        amounts={},
    )

    result = ClosingService(
        closing_accounts=closing_accounts,
    ).close(
        ledger=ledger,
        chart_of_accounts=chart_of_accounts,
        income_statement=income_statement,
        closing_date=date(2026, 12, 31),
    )

    assert len(result.bookings) == 1

    booking = result.bookings[0]
    assert booking.booking_type is BookingType.CLOSING

    assert booking.booking_date == date(2026, 12, 31)
    assert booking.description == "Abschluss des Erlöskontos 8400"
    assert booking.lines == (
        BookingLine(
            account_number="8400",
            side=EntrySide.DEBIT,
            amount=Decimal("500.00"),
        ),
        BookingLine(
            account_number="8990",
            side=EntrySide.CREDIT,
            amount=Decimal("500.00"),
        ),
    )

def test_close_creates_closing_booking_for_expense_account() -> None:
    closing_accounts = ClosingAccounts(
        income_summary_account="8990",
        profit_account="8020",
        loss_account="8021",
    )

    chart_of_accounts = ChartOfAccountsTemplate(
        name="Abschlusstest",
        accounts=(
            TemplateAccount(
                account_number="4930",
                name="Sonstige betriebliche Aufwendungen",
                account_type=AccountType.EXPENSE,
            ),
        ),
        account_mapping_rules=(),
    )

    ledger = Ledger()
    ledger.post(
        debit_account="4930",
        credit_account="1200",
        amount=Decimal("200.00"),
    )

    income_statement = IncomeStatement(
        income_statement=FinancialStatementPosition(
            code="HGB.275.GKV",
            name="GuV",
        ),
        amounts={},
    )

    result = ClosingService(
        closing_accounts=closing_accounts,
    ).close(
        ledger=ledger,
        chart_of_accounts=chart_of_accounts,
        income_statement=income_statement,
        closing_date=date(2026, 12, 31),
    )

    assert len(result.bookings) == 1

    booking = result.bookings[0]
    assert booking.booking_type is BookingType.CLOSING

    assert booking.booking_date == date(2026, 12, 31)
    assert booking.description == "Abschluss des Aufwandskontos 4930"
    assert booking.lines == (
        BookingLine(
            account_number="8990",
            side=EntrySide.DEBIT,
            amount=Decimal("200.00"),
        ),
        BookingLine(
            account_number="4930",
            side=EntrySide.CREDIT,
            amount=Decimal("200.00"),
        ),
    )

def test_close_creates_booking_for_net_income() -> None:
    ClosingAccounts(
        income_summary_account="8990",
        profit_account="8020",
        loss_account="8021",
    )

    revenue = FinancialStatementPosition(
        code="HGB.275.GKV.1",
        name="Umsatzerlöse",
        category=StatementCategory.INCOME,
    )
    expense = FinancialStatementPosition(
        code="HGB.275.GKV.8",
        name="Sonstige betriebliche Aufwendungen",
        category=StatementCategory.EXPENSE,
    )

    income_statement = IncomeStatement(
        income_statement=FinancialStatementPosition(
            code="HGB.275.GKV",
            name="GuV",
            children=(
                revenue,
                expense,
            ),
        ),
        amounts={
            revenue: Decimal("500.00"),
            expense: Decimal("200.00"),
        },
    )

    result = ClosingService(
        closing_accounts=ClosingAccounts(
            income_summary_account="8990",
            profit_account="8020",
            loss_account="8021",
        ),
    ).close(
        income_statement=income_statement,
        closing_date=date(2026, 12, 31)
    )

    assert result.net_income == Decimal("300.00")
    assert len(result.bookings) == 1

    booking = result.bookings[0]
    assert booking.booking_type is BookingType.CLOSING

    assert booking.booking_date == date(2026, 12, 31)
    assert booking.description == "Abschluss des GuV-Kontos"
    assert booking.lines == (
        BookingLine(
            account_number="8990",
            side=EntrySide.DEBIT,
            amount=Decimal("300.00"),
        ),
        BookingLine(
            account_number="8020",
            side=EntrySide.CREDIT,
            amount=Decimal("300.00"),
        ),
    )


def test_calculate_net_income_does_not_double_count_aggregated_positions(
) -> None:
    """Aggregierte GuV-Eltern und ihre Kinder werden nicht doppelt gezählt."""

    service = ClosingService()

    income_statement_root = (
        create_hgb_income_statement_structure()
    )

    positions = {}

    def collect(position) -> None:
        positions[position.code] = position

        for child in position.children:
            collect(child)

    collect(income_statement_root)

    income_statement = IncomeStatement(
        income_statement=income_statement_root,
        amounts={
            positions["HGB.275.GKV.1"]:
                Decimal("16500.00"),

            positions["HGB.275.GKV.5"]:
                Decimal("3000.00"),
            positions["HGB.275.GKV.5.b"]:
                Decimal("3000.00"),

            positions["HGB.275.GKV.7"]:
                Decimal("800.00"),
            positions["HGB.275.GKV.7.a"]:
                Decimal("800.00"),

            positions["HGB.275.GKV.8"]:
                Decimal("7620.00"),
        },
    )

    result = service.calculate_net_income(
        income_statement=income_statement,
    )

    assert result == Decimal("5080.00")
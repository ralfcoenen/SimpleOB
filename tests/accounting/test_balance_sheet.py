from decimal import Decimal

from simpleob.accounting.balance_sheet import BalanceSheet
from simpleob.accounting.financial_statement_position import (
    FinancialStatementPosition,
)


def create_balance_sheet(
    assets_amount: Decimal,
    liabilities_amount: Decimal,
) -> BalanceSheet:
    assets = FinancialStatementPosition(
        code="HGB.266.AKTIVA",
        name="Aktiva",
    )
    liabilities = FinancialStatementPosition(
        code="HGB.266.PASSIVA",
        name="Passiva",
    )

    return BalanceSheet(
        assets=assets,
        liabilities=liabilities,
        amounts={
            assets: assets_amount,
            liabilities: liabilities_amount,
        },
    )


def test_balance_sheet_is_balanced_when_totals_are_equal() -> None:
    balance_sheet = create_balance_sheet(
        assets_amount=Decimal("1000.00"),
        liabilities_amount=Decimal("1000.00"),
    )

    assert balance_sheet.is_balanced() is True


def test_balance_sheet_is_not_balanced_when_totals_differ() -> None:
    balance_sheet = create_balance_sheet(
        assets_amount=Decimal("1000.00"),
        liabilities_amount=Decimal("900.00"),
    )

    assert balance_sheet.is_balanced() is False


def test_balance_sheet_contains_structure_and_amounts() -> None:
    assets = FinancialStatementPosition(
        code="HGB.266.AKTIVA",
        name="Aktiva",
    )
    liabilities = FinancialStatementPosition(
        code="HGB.266.PASSIVA",
        name="Passiva",
    )

    amounts = {
        assets: Decimal("1500.00"),
        liabilities: Decimal("1500.00"),
    }

    balance_sheet = BalanceSheet(
        assets=assets,
        liabilities=liabilities,
        amounts=amounts,
    )

    assert balance_sheet.assets is assets
    assert balance_sheet.liabilities is liabilities
    assert balance_sheet.amount_for(assets) == Decimal("1500.00")
    assert balance_sheet.amount_for(liabilities) == Decimal("1500.00")
    assert balance_sheet.is_balanced() is True
    
    
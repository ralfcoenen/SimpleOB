from decimal import Decimal

from simpleob.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
from simpleob.accounting.hgb_balance_sheet import HgbBalanceSheet


def test_hgb_balance_sheet_stores_assets_liabilities_and_amounts() -> None:
    assets = FinancialStatementPosition(
        code="HGB.266.AKTIVA",
        name="Aktiva",
    )
    liabilities = FinancialStatementPosition(
        code="HGB.266.PASSIVA",
        name="Passiva",
    )

    amounts = {
        assets: Decimal("1000.00"),
        liabilities: Decimal("1000.00"),
    }

    balance_sheet = HgbBalanceSheet(
        assets=assets,
        liabilities=liabilities,
        amounts=amounts,
    )

    assert balance_sheet.assets is assets
    assert balance_sheet.liabilities is liabilities
    assert balance_sheet.amounts == amounts
    
    
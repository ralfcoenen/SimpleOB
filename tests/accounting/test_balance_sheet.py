from decimal import Decimal

from openbilanz.accounting.balance_sheet import (
    BalancePosition,
    BalanceSection,
    BalanceSheet,
)


def test_balance_sheet_is_balanced_when_totals_are_equal() -> None:
    balance_sheet = BalanceSheet(
        assets=BalanceSection(
            name="Assets",
            positions=(
                BalancePosition(
                    code="BANK",
                    name="Bank",
                    amount=Decimal("1000.00"),
                ),
            ),
        ),
        liabilities=BalanceSection(
            name="Liabilities",
            positions=(
                BalancePosition(
                    code="EQUITY",
                    name="Eigenkapital",
                    amount=Decimal("1000.00"),
                ),
            ),
        ),
    )

    assert balance_sheet.is_balanced()
    
def test_balance_sheet_is_not_balanced_when_totals_differ() -> None:
    balance_sheet = BalanceSheet(
        assets=BalanceSection(
            name="Assets",
            positions=(
                BalancePosition(
                    code="BANK",
                    name="Bank",
                    amount=Decimal("1000.00"),
                ),
            ),
        ),
        liabilities=BalanceSection(
            name="Liabilities",
            positions=(
                BalancePosition(
                    code="EQUITY",
                    name="Eigenkapital",
                    amount=Decimal("900.00"),
                ),
            ),
        ),
    )

    assert not balance_sheet.is_balanced()

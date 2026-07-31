from decimal import Decimal

from openbilanz.accounting.balance_sheet import (
    BalancePosition,
    BalanceSection,
)


def test_section_returns_sum_of_root_positions() -> None:
    section = BalanceSection(
        name="Assets",
        positions=(
            BalancePosition(
                code="BANK",
                name="Bank",
                amount=Decimal("1200.00"),
            ),
            BalancePosition(
                code="CASH",
                name="Kasse",
                amount=Decimal("300.00"),
            ),
        ),
    )

    assert section.total() == Decimal("1500.00")
    
    
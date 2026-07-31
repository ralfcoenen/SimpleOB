from decimal import Decimal

from openbilanz.accounting.balance_sheet import BalancePosition
import pytest


def test_leaf_position_returns_own_amount() -> None:
    position = BalancePosition(
        code="BANK",
        name="Bank",
        amount=Decimal("1250.00"),
    )

    assert position.total() == Decimal("1250.00")
    

    

def test_parent_position_returns_sum_of_children() -> None:
    position = BalancePosition(
        code="CURRENT_ASSETS",
        name="Umlaufvermögen",
        children=(
            BalancePosition(
                code="BANK",
                name="Bank",
                amount=Decimal("1250.00"),
            ),
            BalancePosition(
                code="CASH",
                name="Kasse",
                amount=Decimal("250.00"),
            ),
        ),
    )

    assert position.total() == Decimal("1500.00")
    
def test_position_with_children_must_not_have_own_amount() -> None:
    with pytest.raises(
        ValueError,
        match="with children must not have its own amount",
    ):
        BalancePosition(
            code="CURRENT_ASSETS",
            name="Umlaufvermögen",
            amount=Decimal("1500.00"),
            children=(
                BalancePosition(
                    code="BANK",
                    name="Bank",
                    amount=Decimal("1250.00"),
                ),
            ),
        )
        
   
def test_leaf_position_must_have_amount() -> None:
    with pytest.raises(
        ValueError,
        match="without children must have an amount",
    ):
        BalancePosition(
            code="BANK",
            name="Bank",
        )
        

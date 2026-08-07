from decimal import Decimal

import pytest

from openbilanz.domain.account import Account
from openbilanz.domain.account_type import AccountType
from openbilanz.domain.opening_balance_item import (
    OpeningBalanceItem,
)
from openbilanz.domain.template_account import TemplateAccount


def test_create_opening_balance_item() -> None:
    account = Account(
        template=TemplateAccount(
            account_number="1200",
            name="Bank",
            account_type=AccountType.ASSET,
        ),
    )

    item = OpeningBalanceItem(
        account=account,
        amount=Decimal("25000.00"),
    )

    assert item.account is account
    assert item.amount == Decimal("25000.00")
    
def test_rejects_revenue_account() -> None:
    account = Account(
        template=TemplateAccount(
            account_number="8400",
            name="Umsatzerlöse",
            account_type=AccountType.REVENUE,
        ),
    )

    with pytest.raises(
        ValueError,
        match="Bestandskonten",
    ):
        OpeningBalanceItem(
            account=account,
            amount=Decimal("1000.00"),
        )

def test_rejects_expense_account() -> None:
    ...

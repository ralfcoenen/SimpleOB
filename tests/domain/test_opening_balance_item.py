from decimal import Decimal

import pytest

from simpleob.domain.account import Account
from simpleob.domain.account_type import AccountType
from simpleob.domain.entry_side import EntrySide
from simpleob.domain.opening_balance_item import OpeningBalanceItem
from simpleob.domain.template_account import TemplateAccount


def _account(number: str, kind: AccountType) -> Account:
    return Account(
        template=TemplateAccount(number, f"Konto {number}", kind),
    )


def test_create_opening_balance_item() -> None:
    account = _account("1200", AccountType.ASSET)

    item = OpeningBalanceItem(
        account=account,
        amount=Decimal("25000.00"),
        side=EntrySide.DEBIT,
    )

    assert item.account is account
    assert item.amount == Decimal("25000.00")
    assert item.side is EntrySide.DEBIT


@pytest.mark.parametrize(
    "account_type",
    (AccountType.REVENUE, AccountType.EXPENSE),
)
def test_rejects_non_balance_sheet_account(account_type: AccountType) -> None:
    with pytest.raises(ValueError, match="Bestandskonten"):
        OpeningBalanceItem(
            account=_account("8400", account_type),
            amount=Decimal("1000.00"),
            side=EntrySide.DEBIT,
        )


def test_direction_is_explicit_and_not_inferred_from_account_type() -> None:
    item = OpeningBalanceItem(
        account=_account("2970", AccountType.EQUITY),
        amount=Decimal("250.00"),
        side=EntrySide.DEBIT,
    )

    assert item.side is EntrySide.DEBIT

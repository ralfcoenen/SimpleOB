from decimal import Decimal

import pytest

from simpleob.domain.account import Account
from simpleob.domain.account_type import AccountType
from simpleob.domain.entry_side import EntrySide
from simpleob.domain.opening_balance import OpeningBalance
from simpleob.domain.opening_balance_item import OpeningBalanceItem
from simpleob.domain.template_account import TemplateAccount


def _account(number: str, kind: AccountType) -> Account:
    return Account(
        template=TemplateAccount(number, f"Konto {number}", kind),
    )


def test_empty_opening_balance_is_balanced() -> None:
    balance = OpeningBalance(items=())

    assert balance.total_debits == Decimal("0.00")
    assert balance.total_credits == Decimal("0.00")
    assert balance.is_balanced


def test_normal_opening_balance_uses_equal_debit_and_credit_totals() -> None:
    balance = OpeningBalance(
        items=(
            OpeningBalanceItem(
                _account("1200", AccountType.ASSET),
                Decimal("25000.00"),
                EntrySide.DEBIT,
            ),
            OpeningBalanceItem(
                _account("1800", AccountType.EQUITY),
                Decimal("25000.00"),
                EntrySide.CREDIT,
            ),
        ),
    )

    assert balance.total_debits == Decimal("25000.00")
    assert balance.total_credits == Decimal("25000.00")
    assert balance.is_balanced


def test_loss_carryforward_can_be_debit_saldo_on_account_2970() -> None:
    balance = OpeningBalance(
        items=(
            OpeningBalanceItem(
                _account("1200", AccountType.ASSET),
                Decimal("10000.00"),
                EntrySide.CREDIT,
            ),
            OpeningBalanceItem(
                _account("2970", AccountType.EQUITY),
                Decimal("10000.00"),
                EntrySide.DEBIT,
            ),
        ),
    )

    assert balance.is_balanced
    assert balance.items[1].side is EntrySide.DEBIT


def test_negative_equity_can_be_opened_with_balanced_sides() -> None:
    balance = OpeningBalance(
        items=(
            OpeningBalanceItem(
                _account("1200", AccountType.ASSET),
                Decimal("10000.00"),
                EntrySide.DEBIT,
            ),
            OpeningBalanceItem(
                _account("3300", AccountType.LIABILITY),
                Decimal("12000.00"),
                EntrySide.CREDIT,
            ),
            OpeningBalanceItem(
                _account("2900", AccountType.EQUITY),
                Decimal("10000.00"),
                EntrySide.CREDIT,
            ),
            OpeningBalanceItem(
                _account("2970", AccountType.EQUITY),
                Decimal("12000.00"),
                EntrySide.DEBIT,
            ),
        ),
    )

    assert balance.total_debits == Decimal("22000.00")
    assert balance.total_credits == Decimal("22000.00")
    assert balance.is_balanced


def test_asset_can_have_credit_and_liability_can_have_debit_saldo() -> None:
    balance = OpeningBalance(
        items=(
            OpeningBalanceItem(
                _account("1200", AccountType.ASSET),
                Decimal("500.00"),
                EntrySide.CREDIT,
            ),
            OpeningBalanceItem(
                _account("3300", AccountType.LIABILITY),
                Decimal("500.00"),
                EntrySide.DEBIT,
            ),
        ),
    )

    assert balance.is_balanced


def test_unbalanced_sides_are_rejected() -> None:
    balance = OpeningBalance(
        items=(
            OpeningBalanceItem(
                _account("1200", AccountType.ASSET),
                Decimal("100.00"),
                EntrySide.DEBIT,
            ),
        ),
    )

    assert not balance.is_balanced


def test_duplicate_account_net_saldos_are_rejected() -> None:
    bank = _account("1200", AccountType.ASSET)

    with pytest.raises(ValueError, match="einen Nettosaldo"):
        OpeningBalance(
            items=(
                OpeningBalanceItem(bank, Decimal("100.00"), EntrySide.DEBIT),
                OpeningBalanceItem(bank, Decimal("100.00"), EntrySide.CREDIT),
            ),
        )

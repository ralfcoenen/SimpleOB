"""Tests für AccountBalance."""

from decimal import Decimal

import pytest

from openbilanz.accounting import AccountBalance, to_decimal


def test_new_account_has_zero_balances() -> None:
    account = AccountBalance(account_no="1200")

    assert account.account_no == "1200"
    assert account.debit == Decimal("0.00")
    assert account.credit == Decimal("0.00")
    assert account.balance == Decimal("0.00")
    assert account.debit_balance == Decimal("0.00")
    assert account.credit_balance == Decimal("0.00")


def test_account_number_is_trimmed() -> None:
    account = AccountBalance(account_no=" 1200 ")

    assert account.account_no == "1200"


def test_debit_posting_creates_debit_balance() -> None:
    account = AccountBalance(account_no="1200")

    account.add_debit("1000.00")

    assert account.debit == Decimal("1000.00")
    assert account.credit == Decimal("0.00")
    assert account.balance == Decimal("1000.00")
    assert account.debit_balance == Decimal("1000.00")
    assert account.credit_balance == Decimal("0.00")


def test_credit_posting_creates_credit_balance() -> None:
    account = AccountBalance(account_no="0800")

    account.add_credit("1000.00")

    assert account.debit == Decimal("0.00")
    assert account.credit == Decimal("1000.00")
    assert account.balance == Decimal("-1000.00")
    assert account.debit_balance == Decimal("0.00")
    assert account.credit_balance == Decimal("1000.00")


def test_debit_and_credit_are_offset() -> None:
    account = AccountBalance(account_no="1200")

    account.add_debit("1500.00")
    account.add_credit("400.00")

    assert account.debit == Decimal("1500.00")
    assert account.credit == Decimal("400.00")
    assert account.balance == Decimal("1100.00")
    assert account.debit_balance == Decimal("1100.00")
    assert account.credit_balance == Decimal("0.00")


def test_integer_amount_is_converted_to_decimal() -> None:
    account = AccountBalance(account_no="1200")

    account.add_debit(100)

    assert account.debit == Decimal("100.00")


def test_amount_is_rounded_to_two_decimal_places() -> None:
    assert to_decimal("12.345") == Decimal("12.34")
    assert to_decimal("12.355") == Decimal("12.36")


def test_empty_account_number_is_rejected() -> None:
    with pytest.raises(ValueError, match="Kontonummer"):
        AccountBalance(account_no="   ")


@pytest.mark.parametrize("amount", ["0.00", "-1.00", -10])
def test_non_positive_posting_amount_is_rejected(
    amount: str | int,
) -> None:
    account = AccountBalance(account_no="1200")

    with pytest.raises(ValueError, match="größer als 0,00"):
        account.add_debit(amount)


def test_float_amount_is_rejected() -> None:
    account = AccountBalance(account_no="1200")

    with pytest.raises(TypeError, match="Float"):
        account.add_debit(10.50)


def test_negative_initial_debit_is_rejected() -> None:
    with pytest.raises(ValueError, match="Sollumsatz"):
        AccountBalance(account_no="1200", debit=Decimal("-1.00"))


def test_negative_initial_credit_is_rejected() -> None:
    with pytest.raises(ValueError, match="Habenumsatz"):
        AccountBalance(account_no="1200", credit=Decimal("-1.00"))

"""Tests für das Hauptbuch."""

from decimal import Decimal

import pytest

from openbilanz.accounting import Ledger


def test_new_ledger_is_empty() -> None:
    ledger = Ledger()

    assert len(ledger) == 0
    assert ledger.balances() == ()
    assert ledger.debit_total == Decimal("0.00")
    assert ledger.credit_total == Decimal("0.00")
    assert ledger.is_balanced


def test_posting_creates_both_accounts() -> None:
    ledger = Ledger()

    ledger.post(
        debit_account="1200",
        credit_account="0800",
        amount="1000.00",
    )

    assert len(ledger) == 2
    assert ledger.has_account("1200")
    assert ledger.has_account("0800")


def test_posting_updates_debit_and_credit_accounts() -> None:
    ledger = Ledger()

    ledger.post("1200", "0800", "1000.00")

    bank = ledger.get_account("1200")
    equity = ledger.get_account("0800")

    assert bank.debit == Decimal("1000.00")
    assert bank.credit == Decimal("0.00")
    assert bank.balance == Decimal("1000.00")

    assert equity.debit == Decimal("0.00")
    assert equity.credit == Decimal("1000.00")
    assert equity.balance == Decimal("-1000.00")


def test_multiple_postings_are_accumulated() -> None:
    ledger = Ledger()

    ledger.post("1200", "0800", "1000.00")
    ledger.post("4930", "1200", "150.00")
    ledger.post("1200", "8400", "250.00")

    bank = ledger.get_account("1200")

    assert bank.debit == Decimal("1250.00")
    assert bank.credit == Decimal("150.00")
    assert bank.balance == Decimal("1100.00")


def test_ledger_totals_are_balanced() -> None:
    ledger = Ledger()

    ledger.post("1200", "0800", "1000.00")
    ledger.post("4930", "1200", "150.00")
    ledger.post("1200", "8400", "250.00")

    assert ledger.debit_total == Decimal("1400.00")
    assert ledger.credit_total == Decimal("1400.00")
    assert ledger.is_balanced


def test_existing_account_is_reused() -> None:
    ledger = Ledger()

    ledger.post("1200", "0800", "1000.00")
    original_account = ledger.get_account("1200")

    ledger.post("1200", "8400", "100.00")
    reused_account = ledger.get_account("1200")

    assert reused_account is original_account
    assert len(ledger) == 3


def test_get_or_create_account_creates_empty_account() -> None:
    ledger = Ledger()

    account = ledger.get_or_create_account("1000")

    assert account.account_no == "1000"
    assert account.debit == Decimal("0.00")
    assert account.credit == Decimal("0.00")
    assert len(ledger) == 1


def test_balances_are_sorted_by_account_number() -> None:
    ledger = Ledger()

    ledger.get_or_create_account("8400")
    ledger.get_or_create_account("0800")
    ledger.get_or_create_account("1200")

    account_numbers = [
        account.account_no for account in ledger.balances()
    ]

    assert account_numbers == ["0800", "1200", "8400"]


def test_ledger_is_iterable_in_account_order() -> None:
    ledger = Ledger()

    ledger.get_or_create_account("8400")
    ledger.get_or_create_account("1200")
    ledger.get_or_create_account("0800")

    account_numbers = [account.account_no for account in ledger]

    assert account_numbers == ["0800", "1200", "8400"]


def test_account_numbers_are_trimmed() -> None:
    ledger = Ledger()

    ledger.post(" 1200 ", " 0800 ", "1000.00")

    assert ledger.has_account("1200")
    assert ledger.has_account("0800")


def test_unknown_account_raises_key_error() -> None:
    ledger = Ledger()

    with pytest.raises(KeyError, match="9999"):
        ledger.get_account("9999")


def test_empty_account_number_is_rejected() -> None:
    ledger = Ledger()

    with pytest.raises(ValueError, match="Kontonummer"):
        ledger.post("", "0800", "100.00")


def test_non_string_account_number_is_rejected() -> None:
    ledger = Ledger()

    with pytest.raises(TypeError, match="Zeichenkette"):
        ledger.post(1200, "0800", "100.00")  # type: ignore[arg-type]


def test_identical_debit_and_credit_accounts_are_rejected() -> None:
    ledger = Ledger()

    with pytest.raises(ValueError, match="verschieden"):
        ledger.post("1200", "1200", "100.00")

    assert len(ledger) == 0


@pytest.mark.parametrize("amount", ["0.00", "-1.00", -10])
def test_non_positive_amount_is_rejected(
    amount: str | int,
) -> None:
    ledger = Ledger()

    with pytest.raises(ValueError, match="größer als 0,00"):
        ledger.post("1200", "0800", amount)

    assert len(ledger) == 0


def test_float_amount_is_rejected() -> None:
    ledger = Ledger()

    with pytest.raises(TypeError, match="Float"):
        ledger.post("1200", "0800", 10.50)

    assert len(ledger) == 0
    
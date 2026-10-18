"""Tests für die Summen- und Saldenliste."""

from decimal import Decimal

import pytest

from simpleob.accounting import Ledger, TrialBalance, TrialBalanceRow


def create_sample_ledger() -> Ledger:
    """Erzeugt ein kleines ausgeglichenes Beispielhauptbuch."""
    ledger = Ledger()

    ledger.post("1200", "0800", "1000.00")
    ledger.post("4930", "1200", "150.00")
    ledger.post("1200", "8400", "250.00")

    return ledger


def test_empty_trial_balance_has_no_rows() -> None:
    trial_balance = TrialBalance(Ledger())

    assert len(trial_balance) == 0
    assert trial_balance.rows() == ()
    assert trial_balance.debit_turnover_total == Decimal("0.00")
    assert trial_balance.credit_turnover_total == Decimal("0.00")
    assert trial_balance.debit_balance_total == Decimal("0.00")
    assert trial_balance.credit_balance_total == Decimal("0.00")
    assert trial_balance.is_turnover_balanced
    assert trial_balance.is_balance_balanced


def test_trial_balance_contains_one_row_per_account() -> None:
    trial_balance = TrialBalance(create_sample_ledger())

    assert len(trial_balance) == 4
    assert len(trial_balance.rows()) == 4


def test_rows_are_sorted_by_account_number() -> None:
    trial_balance = TrialBalance(create_sample_ledger())

    account_numbers = [row.account_number for row in trial_balance.rows()]

    assert account_numbers == ["0800", "1200", "4930", "8400"]


def test_rows_contain_turnovers_and_balances() -> None:
    trial_balance = TrialBalance(create_sample_ledger())

    rows_by_account = {row.account_number: row for row in trial_balance}

    equity = rows_by_account["0800"]
    bank = rows_by_account["1200"]
    expense = rows_by_account["4930"]
    revenue = rows_by_account["8400"]

    assert equity == TrialBalanceRow(
        account_number="0800",
        debit_turnover=Decimal("0.00"),
        credit_turnover=Decimal("1000.00"),
        debit_balance=Decimal("0.00"),
        credit_balance=Decimal("1000.00"),
    )

    assert bank == TrialBalanceRow(
        account_number="1200",
        debit_turnover=Decimal("1250.00"),
        credit_turnover=Decimal("150.00"),
        debit_balance=Decimal("1100.00"),
        credit_balance=Decimal("0.00"),
    )

    assert expense == TrialBalanceRow(
        account_number="4930",
        debit_turnover=Decimal("150.00"),
        credit_turnover=Decimal("0.00"),
        debit_balance=Decimal("150.00"),
        credit_balance=Decimal("0.00"),
    )

    assert revenue == TrialBalanceRow(
        account_number="8400",
        debit_turnover=Decimal("0.00"),
        credit_turnover=Decimal("250.00"),
        debit_balance=Decimal("0.00"),
        credit_balance=Decimal("250.00"),
    )


def test_turnover_totals_are_balanced() -> None:
    trial_balance = TrialBalance(create_sample_ledger())

    assert trial_balance.debit_turnover_total == Decimal("1400.00")
    assert trial_balance.credit_turnover_total == Decimal("1400.00")
    assert trial_balance.is_turnover_balanced


def test_balance_totals_are_balanced() -> None:
    trial_balance = TrialBalance(create_sample_ledger())

    assert trial_balance.debit_balance_total == Decimal("1250.00")
    assert trial_balance.credit_balance_total == Decimal("1250.00")
    assert trial_balance.is_balance_balanced


def test_trial_balance_is_iterable() -> None:
    trial_balance = TrialBalance(create_sample_ledger())

    account_numbers = [row.account_number for row in trial_balance]

    assert account_numbers == ["0800", "1200", "4930", "8400"]


def test_trial_balance_keeps_ledger_reference() -> None:
    ledger = create_sample_ledger()
    trial_balance = TrialBalance(ledger)

    assert trial_balance.ledger is ledger


def test_invalid_ledger_is_rejected() -> None:
    with pytest.raises(TypeError, match="Ledger"):
        TrialBalance(object())  # type: ignore[arg-type]

"""Unit-Tests für AccountStatementLine."""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from simpleob.accounting.ledger_entry import LedgerEntry
from simpleob.domain.entry_side import EntrySide
from simpleob.reporting.account_statement_line import (
    AccountStatementLine,
)


def test_account_statement_line_stores_entry_and_running_balance() -> None:
    """Eine Kontoblattzeile speichert Buchung und laufenden Saldo."""
    entry = LedgerEntry(
        booking_id=uuid4(),
        booking_date=date(2026, 1, 15),
        voucher_no="RE-1",
        description="Ausgangsrechnung",
        account_number="1200",
        side=EntrySide.DEBIT,
        amount=Decimal("100.00"),
    )

    line = AccountStatementLine(
        entry=entry,
        running_balance=Decimal("100.00"),
    )

    assert line.entry is entry
    assert line.running_balance == Decimal("100.00")
    
def test_account_statement_line_requires_ledger_entry() -> None:
    """Der Buchungseintrag muss ein LedgerEntry sein."""
    with pytest.raises(TypeError):
        AccountStatementLine(
            entry="kein LedgerEntry",
            running_balance=Decimal("100.00"),
        )
        
def test_account_statement_line_requires_decimal_running_balance() -> None:
    """Der laufende Saldo muss ein Decimal sein."""
    entry = LedgerEntry(
        booking_id=uuid4(),
        booking_date=date(2026, 1, 15),
        voucher_no="RE-1",
        description="Ausgangsrechnung",
        account_number="1200",
        side=EntrySide.DEBIT,
        amount=Decimal("100.00"),
    )

    with pytest.raises(TypeError):
        AccountStatementLine(
            entry=entry,
            running_balance="100.00",
        )

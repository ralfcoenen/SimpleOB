"""Unit-Tests für AccountStatement."""

from datetime import date
from decimal import Decimal
from uuid import uuid4

from openbilanz.accounting.ledger_entry import LedgerEntry
from openbilanz.domain.entry_side import EntrySide
from openbilanz.reporting.account_statement import AccountStatement
from openbilanz.reporting.account_statement_line import (
    AccountStatementLine,
)

import pytest


def test_account_statement_stores_account_number_and_lines() -> None:
    """Ein Kontoblatt speichert Kontonummer und Zeilen."""

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

    statement = AccountStatement(
        account_number="1200",
        lines=(line,),
    )

    assert statement.account_number == "1200"
    assert statement.lines == (line,)
    
def test_account_statement_requires_string_account_number() -> None:
    """Die Kontonummer muss eine Zeichenkette sein."""

    with pytest.raises(TypeError):
        AccountStatement(
            account_number=1200,
            lines=(),
        )

@pytest.mark.parametrize("account_number", ["", "   "])
def test_account_statement_rejects_empty_account_number(
    account_number: str,
) -> None:
    """Die Kontonummer darf nicht leer sein."""

    with pytest.raises(ValueError):
        AccountStatement(
            account_number=account_number,
            lines=(),
        )

def test_account_statement_strips_account_number() -> None:
    """Die Kontonummer wird von äußeren Leerzeichen bereinigt."""

    statement = AccountStatement(
        account_number="  1200  ",
        lines=(),
    )

    assert statement.account_number == "1200"
    
def test_account_statement_requires_tuple_lines() -> None:
    """Die Kontoblattzeilen müssen als Tupel übergeben werden."""

    with pytest.raises(TypeError):
        AccountStatement(
            account_number="1200",
            lines=[],
        )
        
def test_account_statement_requires_account_statement_lines() -> None:
    """Alle Elemente müssen AccountStatementLine sein."""

    with pytest.raises(TypeError):
        AccountStatement(
            account_number="1200",
            lines=("keine Zeile",),
        )
        


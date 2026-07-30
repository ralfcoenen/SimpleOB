"""Unit-Tests für ReportingService."""

from openbilanz.accounting.ledger import Ledger
from openbilanz.reporting.account_statement import AccountStatement
from openbilanz.services.reporting_service import ReportingService

from datetime import date
from decimal import Decimal
from uuid import uuid4

from openbilanz.accounting.ledger_entry import LedgerEntry
from openbilanz.domain.entry_side import EntrySide
from openbilanz.services.reporting_service import ReportingService


def test_reporting_service_returns_entries_for_account() -> None:
    """Das Kontoblatt enthält alle Buchungen des angegebenen Kontos."""

    ledger = Ledger()

    entry = LedgerEntry(
        booking_id=uuid4(),
        booking_date=date(2026, 1, 15),
        voucher_no="RE-1",
        description="Ausgangsrechnung",
        account_no="1200",
        side=EntrySide.DEBIT,
        amount=Decimal("100.00"),
    )

    ledger.add_entry(entry)

    service = ReportingService()

    statement = service.account_statement(
        ledger=ledger,
        account_no="1200",
    )

    assert len(statement.lines) == 1
    assert statement.lines[0].entry is entry



def test_reporting_service_creates_empty_account_statement() -> None:
    """Für ein leeres Hauptbuch wird ein leeres Kontoblatt erzeugt."""

    service = ReportingService()

    statement = service.account_statement(
        ledger=Ledger(),
        account_no="1200",
    )

    assert isinstance(statement, AccountStatement)
    assert statement.account_no == "1200"
    assert statement.lines == ()
    
def test_account_statement_calculates_running_balance_for_debit() -> None:
    """Eine Sollbuchung erhöht den laufenden Saldo."""

    ledger = Ledger()

    entry = LedgerEntry(
        booking_id=uuid4(),
        booking_date=date(2026, 1, 15),
        voucher_no="RE-1",
        description="Ausgangsrechnung",
        account_no="1200",
        side=EntrySide.DEBIT,
        amount=Decimal("100.00"),
    )

    ledger.add_entry(entry)

    statement = ReportingService().account_statement(
        ledger=ledger,
        account_no="1200",
    )

    assert statement.lines[0].running_balance == Decimal("100.00")
    
def test_account_statement_calculates_running_balance_for_multiple_debits() -> None:
    """Mehrere Sollbuchungen werden aufaddiert."""

    ledger = Ledger()

    entry1 = LedgerEntry(
        booking_id=uuid4(),
        booking_date=date(2026, 1, 15),
        voucher_no="RE-1",
        description="Erste Buchung",
        account_no="1200",
        side=EntrySide.DEBIT,
        amount=Decimal("100.00"),
    )

    entry2 = LedgerEntry(
        booking_id=uuid4(),
        booking_date=date(2026, 1, 16),
        voucher_no="RE-2",
        description="Zweite Buchung",
        account_no="1200",
        side=EntrySide.DEBIT,
        amount=Decimal("50.00"),
    )

    ledger.add_entry(entry1)
    ledger.add_entry(entry2)

    statement = ReportingService().account_statement(
        ledger=ledger,
        account_no="1200",
    )

    assert len(statement.lines) == 2
    assert statement.lines[0].running_balance == Decimal("100.00")
    assert statement.lines[1].running_balance == Decimal("150.00")

def test_account_statement_calculates_running_balance_for_credit() -> None:
    """Eine Habenbuchung vermindert den laufenden Saldo."""

    ledger = Ledger()

    entry = LedgerEntry(
        booking_id=uuid4(),
        booking_date=date(2026, 1, 15),
        voucher_no="RE-1",
        description="Zahlung",
        account_no="1200",
        side=EntrySide.CREDIT,
        amount=Decimal("100.00"),
    )

    ledger.add_entry(entry)

    statement = ReportingService().account_statement(
        ledger=ledger,
        account_no="1200",
    )

    assert len(statement.lines) == 1
    assert statement.lines[0].running_balance == Decimal("-100.00")
    
def test_account_statement_calculates_running_balance_for_mixed_entries() -> None:
    """Soll- und Habenbuchungen werden korrekt fortgeschrieben."""

    ledger = Ledger()

    debit_1 = LedgerEntry(
        booking_id=uuid4(),
        booking_date=date(2026, 1, 15),
        voucher_no="RE-1",
        description="Erste Sollbuchung",
        account_no="1200",
        side=EntrySide.DEBIT,
        amount=Decimal("100.00"),
    )

    credit = LedgerEntry(
        booking_id=uuid4(),
        booking_date=date(2026, 1, 16),
        voucher_no="ZA-1",
        description="Zahlungseingang",
        account_no="1200",
        side=EntrySide.CREDIT,
        amount=Decimal("40.00"),
    )

    debit_2 = LedgerEntry(
        booking_id=uuid4(),
        booking_date=date(2026, 1, 17),
        voucher_no="RE-2",
        description="Zweite Sollbuchung",
        account_no="1200",
        side=EntrySide.DEBIT,
        amount=Decimal("25.00"),
    )

    ledger.add_entry(debit_1)
    ledger.add_entry(credit)
    ledger.add_entry(debit_2)

    statement = ReportingService().account_statement(
        ledger=ledger,
        account_no="1200",
    )

    assert len(statement.lines) == 3
    assert statement.lines[0].running_balance == Decimal("100.00")
    assert statement.lines[1].running_balance == Decimal("60.00")
    assert statement.lines[2].running_balance == Decimal("85.00")
    
def test_account_statement_contains_only_requested_account() -> None:
    """Das Kontoblatt enthält keine Buchungen anderer Konten."""

    ledger = Ledger()

    entry_1200 = LedgerEntry(
        booking_id=uuid4(),
        booking_date=date(2026, 1, 15),
        voucher_no="RE-1",
        description="Konto 1200",
        account_no="1200",
        side=EntrySide.DEBIT,
        amount=Decimal("100.00"),
    )

    entry_1400 = LedgerEntry(
        booking_id=uuid4(),
        booking_date=date(2026, 1, 16),
        voucher_no="RE-2",
        description="Konto 1400",
        account_no="1400",
        side=EntrySide.DEBIT,
        amount=Decimal("50.00"),
    )

    ledger.add_entry(entry_1200)
    ledger.add_entry(entry_1400)

    statement = ReportingService().account_statement(
        ledger=ledger,
        account_no="1200",
    )

    assert len(statement.lines) == 1
    assert statement.lines[0].entry is entry_1200
    

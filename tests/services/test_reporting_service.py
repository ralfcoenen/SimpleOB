"""Unit-Tests für ReportingService."""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from openbilanz.accounting.ledger import Ledger
from openbilanz.accounting.ledger_entry import LedgerEntry
from openbilanz.domain.booking import Booking
from openbilanz.domain.booking_line import BookingLine
from openbilanz.domain.booking_type import BookingType
from openbilanz.domain.entry_side import EntrySide
from openbilanz.domain.journal import Journal
from openbilanz.reporting.account_statement import AccountStatement
from openbilanz.services.reporting_service import ReportingService


def test_reporting_service_returns_entries_for_account() -> None:
    """Das Kontoblatt enthält alle Buchungen des angegebenen Kontos."""

    ledger = Ledger()

    entry = LedgerEntry(
        booking_id=uuid4(),
        booking_date=date(2026, 1, 15),
        voucher_no="RE-1",
        description="Ausgangsrechnung",
        account_number="1200",
        side=EntrySide.DEBIT,
        amount=Decimal("100.00"),
    )

    ledger.add_entry(entry)

    service = ReportingService()

    statement = service.account_statement(
        ledger=ledger,
        account_number="1200",
    )

    assert len(statement.lines) == 1
    assert statement.lines[0].entry is entry


def test_reporting_service_creates_empty_account_statement() -> None:
    """Für ein leeres Hauptbuch wird ein leeres Kontoblatt erzeugt."""

    service = ReportingService()

    statement = service.account_statement(
        ledger=Ledger(),
        account_number="1200",
    )

    assert isinstance(statement, AccountStatement)
    assert statement.account_number == "1200"
    assert statement.lines == ()


def test_account_statement_calculates_running_balance_for_debit() -> None:
    """Eine Sollbuchung erhöht den laufenden Saldo."""

    ledger = Ledger()

    entry = LedgerEntry(
        booking_id=uuid4(),
        booking_date=date(2026, 1, 15),
        voucher_no="RE-1",
        description="Ausgangsrechnung",
        account_number="1200",
        side=EntrySide.DEBIT,
        amount=Decimal("100.00"),
    )

    ledger.add_entry(entry)

    statement = ReportingService().account_statement(
        ledger=ledger,
        account_number="1200",
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
        account_number="1200",
        side=EntrySide.DEBIT,
        amount=Decimal("100.00"),
    )

    entry2 = LedgerEntry(
        booking_id=uuid4(),
        booking_date=date(2026, 1, 16),
        voucher_no="RE-2",
        description="Zweite Buchung",
        account_number="1200",
        side=EntrySide.DEBIT,
        amount=Decimal("50.00"),
    )

    ledger.add_entry(entry1)
    ledger.add_entry(entry2)

    statement = ReportingService().account_statement(
        ledger=ledger,
        account_number="1200",
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
        account_number="1200",
        side=EntrySide.CREDIT,
        amount=Decimal("100.00"),
    )

    ledger.add_entry(entry)

    statement = ReportingService().account_statement(
        ledger=ledger,
        account_number="1200",
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
        account_number="1200",
        side=EntrySide.DEBIT,
        amount=Decimal("100.00"),
    )

    credit = LedgerEntry(
        booking_id=uuid4(),
        booking_date=date(2026, 1, 16),
        voucher_no="ZA-1",
        description="Zahlungseingang",
        account_number="1200",
        side=EntrySide.CREDIT,
        amount=Decimal("40.00"),
    )

    debit_2 = LedgerEntry(
        booking_id=uuid4(),
        booking_date=date(2026, 1, 17),
        voucher_no="RE-2",
        description="Zweite Sollbuchung",
        account_number="1200",
        side=EntrySide.DEBIT,
        amount=Decimal("25.00"),
    )

    ledger.add_entry(debit_1)
    ledger.add_entry(credit)
    ledger.add_entry(debit_2)

    statement = ReportingService().account_statement(
        ledger=ledger,
        account_number="1200",
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
        account_number="1200",
        side=EntrySide.DEBIT,
        amount=Decimal("100.00"),
    )

    entry_1400 = LedgerEntry(
        booking_id=uuid4(),
        booking_date=date(2026, 1, 16),
        voucher_no="RE-2",
        description="Konto 1400",
        account_number="1400",
        side=EntrySide.DEBIT,
        amount=Decimal("50.00"),
    )

    ledger.add_entry(entry_1200)
    ledger.add_entry(entry_1400)

    statement = ReportingService().account_statement(
        ledger=ledger,
        account_number="1200",
    )

    assert len(statement.lines) == 1
    assert statement.lines[0].entry is entry_1200


def test_trial_balance_report_separates_opening_and_turnover() -> None:
    """Eröffnungswerte werden nicht als laufender Umsatz ausgewiesen."""

    journal = Journal()
    ledger = Ledger()

    opening_booking = Booking(
        booking_id=uuid4(),
        booking_date=date(2026, 1, 1),
        voucher_no="EB-001",
        description="Eröffnungsbilanz",
        booking_type=BookingType.OPENING,
        lines=(
            BookingLine(
                account_number="1200",
                side=EntrySide.DEBIT,
                amount=Decimal("10000.00"),
            ),
            BookingLine(
                account_number="9000",
                side=EntrySide.CREDIT,
                amount=Decimal("10000.00"),
            ),
        ),
    )

    regular_booking = Booking(
        booking_id=uuid4(),
        booking_date=date(2026, 2, 15),
        voucher_no="B-001",
        description="Einzahlung",
        lines=(
            BookingLine(
                account_number="1200",
                side=EntrySide.DEBIT,
                amount=Decimal("2000.00"),
            ),
            BookingLine(
                account_number="8400",
                side=EntrySide.CREDIT,
                amount=Decimal("2000.00"),
            ),
        ),
    )

    journal.add(regular_booking)

    journal.add(opening_booking)

    ledger.add_entry(
        LedgerEntry(
            booking_id=opening_booking.booking_id,
            booking_date=opening_booking.booking_date,
            voucher_no="EB-001",
            description="Eröffnungsbilanz",
            account_number="1200",
            side=EntrySide.DEBIT,
            amount=Decimal("10000.00"),
        )
    )

    ledger.add_entry(
        LedgerEntry(
            booking_id=opening_booking.booking_id,
            booking_date=opening_booking.booking_date,
            voucher_no="EB-001",
            description="Eröffnungsbilanz",
            account_number="9000",
            side=EntrySide.CREDIT,
            amount=Decimal("10000.00"),
        )
    )

    regular_booking_id = uuid4()

    ledger.add_entry(
        LedgerEntry(
            booking_id=regular_booking_id,
            booking_date=date(2026, 2, 15),
            voucher_no="B-001",
            description="Einzahlung",
            account_number="1200",
            side=EntrySide.DEBIT,
            amount=Decimal("2000.00"),
        )
    )

    ledger.add_entry(
        LedgerEntry(
            booking_id=regular_booking_id,
            booking_date=date(2026, 2, 15),
            voucher_no="B-001",
            description="Einzahlung",
            account_number="8400",
            side=EntrySide.CREDIT,
            amount=Decimal("2000.00"),
        )
    )

    report = ReportingService().trial_balance_report(
        ledger=ledger,
        journal=journal,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )

    bank = next(row for row in report.rows if row.account_number == "1200")

    assert bank.opening_debit == Decimal("10000.00")
    assert bank.opening_credit == Decimal("0.00")
    assert bank.debit_turnover == Decimal("2000.00")
    assert bank.credit_turnover == Decimal("0.00")
    assert bank.closing_debit == Decimal("12000.00")
    assert bank.closing_credit == Decimal("0.00")

    assert all(row.account_number != "9000" for row in report.rows)


def test_trial_balance_report_uses_prior_movements_as_opening_balance() -> None:
    """Bewegungen vor dem Zeitraum fließen in den Anfangssaldo ein."""

    journal = Journal()
    ledger = Ledger()

    first_booking = Booking(
        booking_id=uuid4(),
        booking_date=date(2026, 2, 1),
        voucher_no="B-001",
        description="Einzahlung",
        lines=(
            BookingLine(
                account_number="1200",
                side=EntrySide.DEBIT,
                amount=Decimal("1000.00"),
            ),
            BookingLine(
                account_number="8400",
                side=EntrySide.CREDIT,
                amount=Decimal("1000.00"),
            ),
        ),
    )

    second_booking = Booking(
        booking_id=uuid4(),
        booking_date=date(2026, 4, 1),
        voucher_no="B-002",
        description="Auszahlung",
        lines=(
            BookingLine(
                account_number="4930",
                side=EntrySide.DEBIT,
                amount=Decimal("250.00"),
            ),
            BookingLine(
                account_number="1200",
                side=EntrySide.CREDIT,
                amount=Decimal("250.00"),
            ),
        ),
    )

    journal.add(first_booking)
    journal.add(second_booking)

    report = ReportingService().trial_balance_report(
        ledger=ledger,
        journal=journal,
        start_date=date(2026, 3, 1),
        end_date=date(2026, 6, 30),
    )

    row = next(row for row in report.rows if row.account_number == "1200")

    assert row.account_number == "1200"
    assert row.opening_debit == Decimal("1000.00")
    assert row.opening_credit == Decimal("0.00")
    assert row.debit_turnover == Decimal("0.00")
    assert row.credit_turnover == Decimal("250.00")
    assert row.closing_debit == Decimal("750.00")
    assert row.closing_credit == Decimal("0.00")


def test_trial_balance_report_rejects_invalid_date_range() -> None:
    """Das Enddatum darf nicht vor dem Startdatum liegen."""

    with pytest.raises(
        ValueError,
        match="Enddatum",
    ):
        ReportingService().trial_balance_report(
            ledger=Ledger(),
            journal=Journal(),
            start_date=date(2026, 12, 31),
            end_date=date(2026, 1, 1),
        )


def test_account_statement_filters_date_range() -> None:
    """Das Kontoblatt zeigt nur Buchungen im gewählten Zeitraum."""

    ledger = Ledger()

    before = LedgerEntry(
        booking_id=uuid4(),
        booking_date=date(2026, 1, 15),
        voucher_no="B-001",
        description="Vor Zeitraum",
        account_number="1200",
        side=EntrySide.DEBIT,
        amount=Decimal("100.00"),
    )

    inside = LedgerEntry(
        booking_id=uuid4(),
        booking_date=date(2026, 3, 15),
        voucher_no="B-002",
        description="Im Zeitraum",
        account_number="1200",
        side=EntrySide.CREDIT,
        amount=Decimal("40.00"),
    )

    after = LedgerEntry(
        booking_id=uuid4(),
        booking_date=date(2026, 8, 15),
        voucher_no="B-003",
        description="Nach Zeitraum",
        account_number="1200",
        side=EntrySide.DEBIT,
        amount=Decimal("25.00"),
    )

    ledger.add_entry(before)
    ledger.add_entry(inside)
    ledger.add_entry(after)

    statement = ReportingService().account_statement(
        ledger=ledger,
        account_number="1200",
        start_date=date(2026, 3, 1),
        end_date=date(2026, 6, 30),
    )

    assert len(statement.lines) == 1
    assert statement.lines[0].entry is inside
    assert statement.lines[0].running_balance == Decimal("60.00")


def test_account_statement_includes_date_range_boundaries() -> None:
    """Start- und Enddatum gehören zum Auswertungszeitraum."""

    ledger = Ledger()

    start_entry = LedgerEntry(
        booking_id=uuid4(),
        booking_date=date(2026, 3, 1),
        voucher_no="B-001",
        description="Startdatum",
        account_number="1200",
        side=EntrySide.DEBIT,
        amount=Decimal("100.00"),
    )

    end_entry = LedgerEntry(
        booking_id=uuid4(),
        booking_date=date(2026, 6, 30),
        voucher_no="B-002",
        description="Enddatum",
        account_number="1200",
        side=EntrySide.CREDIT,
        amount=Decimal("25.00"),
    )

    ledger.add_entry(start_entry)
    ledger.add_entry(end_entry)

    statement = ReportingService().account_statement(
        ledger=ledger,
        account_number="1200",
        start_date=date(2026, 3, 1),
        end_date=date(2026, 6, 30),
    )

    assert len(statement.lines) == 2
    assert statement.lines[0].entry is start_entry
    assert statement.lines[1].entry is end_entry
    assert statement.lines[1].running_balance == Decimal("75.00")


def test_account_statement_rejects_invalid_date_range() -> None:
    """Das Enddatum darf nicht vor dem Startdatum liegen."""

    with pytest.raises(
        ValueError,
        match="Enddatum",
    ):
        ReportingService().account_statement(
            ledger=Ledger(),
            account_number="1200",
            start_date=date(2026, 12, 31),
            end_date=date(2026, 1, 1),
        )

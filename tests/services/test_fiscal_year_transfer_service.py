"""Tests für die Überleitung in ein neues Geschäftsjahr."""

from datetime import date
from decimal import Decimal

from openbilanz.accounting.ledger import Ledger
from openbilanz.domain.account_type import AccountType
from openbilanz.domain.booking import Booking
from openbilanz.domain.booking_line import BookingLine
from openbilanz.domain.entry_side import EntrySide
from openbilanz.domain.journal import Journal
from openbilanz.services.fiscal_year_transfer_service import (
    FiscalYearTransferService,
)
from openbilanz.services.posting_service import PostingService


def test_creates_opening_bookings_for_balance_sheet_accounts() -> None:
    """Nur Bestandskonten werden in das neue Geschäftsjahr vorgetragen."""

    ledger = Ledger()
    journal = Journal()
    posting_service = PostingService()

    bookings = (
        Booking(
            booking_date=date(2026, 1, 1),
            description="Eröffnung",
            lines=(
                BookingLine(
                    account_number="1200",
                    side=EntrySide.DEBIT,
                    amount=Decimal("25000.00"),
                ),
                BookingLine(
                    account_number="9000",
                    side=EntrySide.CREDIT,
                    amount=Decimal("25000.00"),
                ),
            ),
        ),
        Booking(
            booking_date=date(2026, 8, 8),
            description="Büromaterial",
            lines=(
                BookingLine(
                    account_number="4980",
                    side=EntrySide.DEBIT,
                    amount=Decimal("500.00"),
                ),
                BookingLine(
                    account_number="1200",
                    side=EntrySide.CREDIT,
                    amount=Decimal("500.00"),
                ),
            ),
        ),
        Booking(
            booking_date=date(2026, 8, 9),
            description="Umsatzerlös",
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
        ),
    )

    for booking in bookings:
        posting_service.post_booking(
            booking=booking,
            journal=journal,
            ledger=ledger,
        )

    account_types = {
        "1200": AccountType.ASSET,
        "1600": AccountType.LIABILITY,
        "1800": AccountType.EQUITY,
        "4980": AccountType.EXPENSE,
        "8400": AccountType.REVENUE,
        "9000": AccountType.EQUITY,
    }

    service = FiscalYearTransferService(
        opening_balance_account_number="9000",
        profit_account_number="8020",
        loss_account_number="8021",
        retained_earnings_account_number="2970",
    )

    transfer_bookings = service.create_opening_bookings(
        ledger=ledger,
        account_types=account_types,
        opening_date=date(2027, 1, 1),
    )

    assert len(transfer_bookings) == 1

    booking = transfer_bookings[0]

    assert booking.booking_date == date(2027, 1, 1)
    assert booking.description == "Saldovortrag Konto 1200"

    assert booking.lines == (
        BookingLine(
            account_number="1200",
            side=EntrySide.DEBIT,
            amount=Decimal("26500.00"),
        ),
        BookingLine(
            account_number="9000",
            side=EntrySide.CREDIT,
            amount=Decimal("26500.00"),
        ),
    )

    transferred_accounts = {
        line.account_number
        for transfer_booking in transfer_bookings
        for line in transfer_booking.lines
    }

    assert "4980" not in transferred_accounts
    assert "8400" not in transferred_accounts


def test_creates_opening_bookings_for_credit_balances() -> None:
    """Passiv- und Eigenkapitalkonten werden im Haben vorgetragen."""

    ledger = Ledger()
    journal = Journal()
    posting_service = PostingService()

    bookings = (
        Booking(
            booking_date=date(2026, 1, 1),
            description="Eröffnung Verbindlichkeiten",
            lines=(
                BookingLine(
                    account_number="9000",
                    side=EntrySide.DEBIT,
                    amount=Decimal("8000.00"),
                ),
                BookingLine(
                    account_number="1600",
                    side=EntrySide.CREDIT,
                    amount=Decimal("8000.00"),
                ),
            ),
        ),
        Booking(
            booking_date=date(2026, 1, 1),
            description="Eröffnung Eigenkapital",
            lines=(
                BookingLine(
                    account_number="9000",
                    side=EntrySide.DEBIT,
                    amount=Decimal("17000.00"),
                ),
                BookingLine(
                    account_number="1800",
                    side=EntrySide.CREDIT,
                    amount=Decimal("17000.00"),
                ),
            ),
        ),
    )

    for booking in bookings:
        posting_service.post_booking(
            booking=booking,
            journal=journal,
            ledger=ledger,
        )

    account_types = {
        "1600": AccountType.LIABILITY,
        "1800": AccountType.EQUITY,
        "9000": AccountType.EQUITY,
    }

    service = FiscalYearTransferService(
        opening_balance_account_number="9000",
        profit_account_number="8020",
        loss_account_number="8021",
        retained_earnings_account_number="2970",
    )

    transfer_bookings = service.create_opening_bookings(
        ledger=ledger,
        account_types=account_types,
        opening_date=date(2027, 1, 1),
    )

    assert len(transfer_bookings) == 2

    assert transfer_bookings[0].lines == (
        BookingLine(
            account_number="9000",
            side=EntrySide.DEBIT,
            amount=Decimal("8000.00"),
        ),
        BookingLine(
            account_number="1600",
            side=EntrySide.CREDIT,
            amount=Decimal("8000.00"),
        ),
    )

    assert transfer_bookings[1].lines == (
        BookingLine(
            account_number="9000",
            side=EntrySide.DEBIT,
            amount=Decimal("17000.00"),
        ),
        BookingLine(
            account_number="1800",
            side=EntrySide.CREDIT,
            amount=Decimal("17000.00"),
        ),
    )

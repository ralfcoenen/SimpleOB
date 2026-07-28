"""
Unit-Tests für den PostingService.
"""

from datetime import date
from decimal import Decimal

import pytest

from openbilanz.accounting.ledger import Ledger
from openbilanz.domain.booking import Booking
from openbilanz.domain.booking_line import BookingLine
from openbilanz.domain.entry_side import EntrySide
from openbilanz.services.posting_service import PostingService
from tests.factories import create_booking


class TestPostingService:
    """Tests für den PostingService."""

    def test_post_booking_transfers_booking_to_ledger(self) -> None:
        """Eine einfache Buchung wird vollständig übertragen."""
        booking = create_booking()
        ledger = Ledger()

        PostingService().post_booking(
            booking=booking,
            ledger=ledger,
        )

        assert ledger.debit_total == Decimal("100.00")
        assert ledger.credit_total == Decimal("100.00")
        assert ledger.is_balanced

        assert ledger.get_account("1200").debit == Decimal("100.00")

        assert ledger.get_account("8400").credit == Decimal("100.00")

    def test_post_booking_transfers_split_credit_booking(self) -> None:
        """Eine Sollzeile wird auf mehrere Habenzeilen verteilt."""
        booking = Booking(
            booking_date=date(2026, 1, 2),
            voucher_no="TEST-002",
            description="Splittbuchung Haben",
            lines=(
                BookingLine(
                    account_no="1200",
                    side=EntrySide.DEBIT,
                    amount=Decimal("150.00"),
                ),
                BookingLine(
                    account_no="8400",
                    side=EntrySide.CREDIT,
                    amount=Decimal("100.00"),
                ),
                BookingLine(
                    account_no="8300",
                    side=EntrySide.CREDIT,
                    amount=Decimal("50.00"),
                ),
            ),
        )

        ledger = Ledger()

        PostingService().post_booking(
            booking=booking,
            ledger=ledger,
        )

        assert ledger.debit_total == Decimal("150.00")
        assert ledger.credit_total == Decimal("150.00")
        assert ledger.is_balanced

        assert ledger.get_account("1200").debit == Decimal("150.00")

        assert ledger.get_account("8400").credit == Decimal("100.00")

        assert ledger.get_account("8300").credit == Decimal("50.00")

    def test_post_booking_transfers_split_debit_booking(self) -> None:
        """Mehrere Sollzeilen werden einer Habenzeile zugeordnet."""
        booking = Booking(
            booking_date=date(2026, 1, 3),
            voucher_no="TEST-003",
            description="Splittbuchung Soll",
            lines=(
                BookingLine(
                    account_no="1200",
                    side=EntrySide.DEBIT,
                    amount=Decimal("70.00"),
                ),
                BookingLine(
                    account_no="1400",
                    side=EntrySide.DEBIT,
                    amount=Decimal("30.00"),
                ),
                BookingLine(
                    account_no="8400",
                    side=EntrySide.CREDIT,
                    amount=Decimal("100.00"),
                ),
            ),
        )

        ledger = Ledger()

        PostingService().post_booking(
            booking=booking,
            ledger=ledger,
        )

        assert ledger.debit_total == Decimal("100.00")
        assert ledger.credit_total == Decimal("100.00")
        assert ledger.is_balanced

        assert ledger.get_account("1200").debit == Decimal("70.00")

        assert ledger.get_account("1400").debit == Decimal("30.00")

        assert ledger.get_account("8400").credit == Decimal("100.00")

    def test_post_booking_transfers_multiple_debit_and_credit_lines(
        self,
    ) -> None:
        """Mehrere Soll- und Habenzeilen werden vollständig verarbeitet."""
        booking = Booking(
            booking_date=date(2026, 1, 4),
            voucher_no="TEST-004",
            description="Mehrseitige Splittbuchung",
            lines=(
                BookingLine(
                    account_no="1200",
                    side=EntrySide.DEBIT,
                    amount=Decimal("70.00"),
                ),
                BookingLine(
                    account_no="1400",
                    side=EntrySide.DEBIT,
                    amount=Decimal("30.00"),
                ),
                BookingLine(
                    account_no="8400",
                    side=EntrySide.CREDIT,
                    amount=Decimal("60.00"),
                ),
                BookingLine(
                    account_no="8300",
                    side=EntrySide.CREDIT,
                    amount=Decimal("40.00"),
                ),
            ),
        )

        ledger = Ledger()

        PostingService().post_booking(
            booking=booking,
            ledger=ledger,
        )

        assert ledger.debit_total == Decimal("100.00")
        assert ledger.credit_total == Decimal("100.00")
        assert ledger.is_balanced

        assert ledger.get_account("1200").debit == Decimal("70.00")

        assert ledger.get_account("1400").debit == Decimal("30.00")

        assert ledger.get_account("8400").credit == Decimal("60.00")

        assert ledger.get_account("8300").credit == Decimal("40.00")

    @pytest.mark.parametrize(
        "invalid_booking",
        [
            None,
            object(),
            123,
            "booking",
        ],
    )
    def test_post_booking_rejects_invalid_booking(
        self,
        invalid_booking: object,
    ) -> None:
        """Ungültige Booking-Objekte werden zurückgewiesen."""
        with pytest.raises(
            TypeError,
            match="booking muss eine Booking sein",
        ):
            PostingService().post_booking(
                booking=invalid_booking,
                ledger=Ledger(),
            )

    @pytest.mark.parametrize(
        "invalid_ledger",
        [
            None,
            object(),
            123,
            "ledger",
        ],
    )
    def test_post_booking_rejects_invalid_ledger(
        self,
        invalid_ledger: object,
    ) -> None:
        """Ungültige Ledger-Objekte werden zurückgewiesen."""
        with pytest.raises(
            TypeError,
            match="ledger muss ein Ledger sein",
        ):
            PostingService().post_booking(
                booking=create_booking(),
                ledger=invalid_ledger,
            )

    def test_post_booking_does_not_modify_booking(self) -> None:
        """Der PostingService verändert die Buchung nicht."""
        booking = create_booking()

        original_state = (
            booking.booking_id,
            booking.booking_date,
            booking.voucher_no,
            booking.description,
            booking.lines,
            booking.debit_total,
            booking.credit_total,
        )

        PostingService().post_booking(
            booking=booking,
            ledger=Ledger(),
        )

        assert (
            booking.booking_id,
            booking.booking_date,
            booking.voucher_no,
            booking.description,
            booking.lines,
            booking.debit_total,
            booking.credit_total,
        ) == original_state

"""Tests für vollständige Buchungen."""

from dataclasses import FrozenInstanceError
from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from simpleob.domain import (
Booking,
BookingLine,
EntrySide,
UnbalancedBookingError,
)
from simpleob.domain.booking_type import BookingType


def create_balanced_lines() -> tuple[BookingLine, BookingLine]:
    """Erzeugt einen einfachen ausgeglichenen Buchungssatz."""
    return (
        BookingLine(
            account_number="1200",
            side=EntrySide.DEBIT,
            amount="119.00",
        ),
        BookingLine(
            account_number="1600",
            side=EntrySide.CREDIT,
            amount="119.00",
        ),
    )


def test_booking_is_created() -> None:
    booking = Booking(
        booking_date=date(2026, 7, 27),
        voucher_no="RE-1001",
        description="Wareneinkauf",
        lines=create_balanced_lines(),
    )

    assert booking.booking_date == date(2026, 7, 27)
    assert booking.voucher_no == "RE-1001"
    assert booking.description == "Wareneinkauf"
    assert isinstance(booking.booking_id, UUID)
    assert len(booking.lines) == 2

def test_booking_uses_regular_booking_type_by_default() -> None:
    """Normale Buchungen erhalten standardmäßig den Typ REGULAR."""

    booking = Booking(
        booking_date=date(2026, 7, 27),
        lines=create_balanced_lines(),
    )

    assert booking.booking_type is BookingType.REGULAR


def test_booking_accepts_explicit_booking_type() -> None:
    """Ein Buchungstyp kann ausdrücklich angegeben werden."""

    booking = Booking(
        booking_date=date(2026, 7, 27),
        lines=create_balanced_lines(),
        booking_type=BookingType.CLOSING,
    )

    assert booking.booking_type is BookingType.CLOSING


def test_invalid_booking_type_is_rejected() -> None:
    """Ungültige Buchungstypen werden abgelehnt."""

    with pytest.raises(TypeError, match="Buchungstyp"):
        Booking(
            booking_date=date(2026, 7, 27),
            lines=create_balanced_lines(),
            booking_type="CLOSING",  # type: ignore[arg-type]
        )


def test_booking_accepts_list_of_lines() -> None:
    booking = Booking(
        booking_date=date(2026, 7, 27),
        lines=list(create_balanced_lines()),
    )

    assert isinstance(booking.lines, tuple)
    assert len(booking.lines) == 2


def test_booking_uses_given_uuid() -> None:
    booking_id = uuid4()

    booking = Booking(
        booking_id=booking_id,
        booking_date=date(2026, 7, 27),
        lines=create_balanced_lines(),
    )

    assert booking.booking_id == booking_id


def test_booking_calculates_totals() -> None:
    booking = Booking(
        booking_date=date(2026, 7, 27),
        lines=create_balanced_lines(),
    )

    assert booking.debit_total == Decimal("119.00")
    assert booking.credit_total == Decimal("119.00")
    assert booking.is_balanced


def test_booking_supports_split_booking() -> None:
    booking = Booking(
        booking_date=date(2026, 7, 27),
        lines=(
            BookingLine(
                account_number="1200",
                side=EntrySide.DEBIT,
                amount="119.00",
            ),
            BookingLine(
                account_number="8400",
                side=EntrySide.CREDIT,
                amount="100.00",
            ),
            BookingLine(
                account_number="1776",
                side=EntrySide.CREDIT,
                amount="19.00",
            ),
        ),
    )

    assert booking.debit_total == Decimal("119.00")
    assert booking.credit_total == Decimal("119.00")
    assert len(booking.debit_lines) == 1
    assert len(booking.credit_lines) == 2


def test_booking_is_iterable() -> None:
    lines = create_balanced_lines()

    booking = Booking(
        booking_date=date(2026, 7, 27),
        lines=lines,
    )

    assert tuple(booking) == lines


def test_booking_length_is_number_of_lines() -> None:
    booking = Booking(
        booking_date=date(2026, 7, 27),
        lines=create_balanced_lines(),
    )

    assert len(booking) == 2


def test_optional_text_is_trimmed() -> None:
    booking = Booking(
        booking_date=date(2026, 7, 27),
        voucher_no="  RE-1001  ",
        description="  Wareneinkauf  ",
        lines=create_balanced_lines(),
    )

    assert booking.voucher_no == "RE-1001"
    assert booking.description == "Wareneinkauf"


def test_empty_optional_text_becomes_none() -> None:
    booking = Booking(
        booking_date=date(2026, 7, 27),
        voucher_no="   ",
        description="",
        lines=create_balanced_lines(),
    )

    assert booking.voucher_no is None
    assert booking.description is None


def test_unbalanced_booking_is_rejected() -> None:
    with pytest.raises(
        UnbalancedBookingError,
        match="Soll- und Habensumme",
    ):
        Booking(
            booking_date=date(2026, 7, 27),
            lines=(
                BookingLine(
                    account_number="1200",
                    side=EntrySide.DEBIT,
                    amount="100.00",
                ),
                BookingLine(
                    account_number="1600",
                    side=EntrySide.CREDIT,
                    amount="90.00",
                ),
            ),
        )


def test_booking_with_less_than_two_lines_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="mindestens zwei",
    ):
        Booking(
            booking_date=date(2026, 7, 27),
            lines=(
                BookingLine(
                    account_number="1200",
                    side=EntrySide.DEBIT,
                    amount="100.00",
                ),
            ),
        )


def test_booking_without_debit_line_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="Sollzeile",
    ):
        Booking(
            booking_date=date(2026, 7, 27),
            lines=(
                BookingLine(
                    account_number="1600",
                    side=EntrySide.CREDIT,
                    amount="50.00",
                ),
                BookingLine(
                    account_number="8400",
                    side=EntrySide.CREDIT,
                    amount="50.00",
                ),
            ),
        )


def test_booking_without_credit_line_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="Habenzeile",
    ):
        Booking(
            booking_date=date(2026, 7, 27),
            lines=(
                BookingLine(
                    account_number="1200",
                    side=EntrySide.DEBIT,
                    amount="50.00",
                ),
                BookingLine(
                    account_number="1400",
                    side=EntrySide.DEBIT,
                    amount="50.00",
                ),
            ),
        )


def test_invalid_booking_date_is_rejected() -> None:
    with pytest.raises(TypeError, match="Buchungsdatum"):
        Booking(
            booking_date="2026-07-27",  # type: ignore[arg-type]
            lines=create_balanced_lines(),
        )


def test_invalid_booking_id_is_rejected() -> None:
    with pytest.raises(TypeError, match="UUID"):
        Booking(
            booking_id="123",  # type: ignore[arg-type]
            booking_date=date(2026, 7, 27),
            lines=create_balanced_lines(),
        )


def test_non_booking_line_is_rejected() -> None:
    with pytest.raises(TypeError, match="BookingLine"):
        Booking(
            booking_date=date(2026, 7, 27),
            lines=(
                create_balanced_lines()[0],
                "invalid",  # type: ignore[arg-type]
            ),
        )


def test_non_iterable_lines_are_rejected() -> None:
    with pytest.raises(TypeError, match="iterierbar"):
        Booking(
            booking_date=date(2026, 7, 27),
            lines=123,  # type: ignore[arg-type]
        )


def test_invalid_voucher_number_is_rejected() -> None:
    with pytest.raises(TypeError, match="Belegnummer"):
        Booking(
            booking_date=date(2026, 7, 27),
            voucher_no=1001,  # type: ignore[arg-type]
            lines=create_balanced_lines(),
        )


def test_invalid_description_is_rejected() -> None:
    with pytest.raises(TypeError, match="Buchungstext"):
        Booking(
            booking_date=date(2026, 7, 27),
            description=123,  # type: ignore[arg-type]
            lines=create_balanced_lines(),
        )




def test_booking_is_immutable() -> None:
    booking = Booking(
        booking_date=date(2026, 7, 27),
        lines=create_balanced_lines(),
    )

    with pytest.raises(FrozenInstanceError):
        booking.description = "Geändert"  # type: ignore[misc]


def test_booking_lines_are_immutable_collection() -> None:
    booking = Booking(
        booking_date=date(2026, 7, 27),
        lines=create_balanced_lines(),
    )

    with pytest.raises(TypeError):
        booking.lines[0] = create_balanced_lines()[1]  # type: ignore[index]

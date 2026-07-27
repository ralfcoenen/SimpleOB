"""Tests für das Journal."""

from datetime import date
from uuid import uuid4

import pytest

from openbilanz.domain import (
    Booking,
    BookingLine,
    EntrySide,
    Journal,
)


def create_booking(
    *,
    booking_date: date = date(2026, 7, 27),
    voucher_no: str | None = "RE-1001",
    amount: str = "119.00",
) -> Booking:
    """Erzeugt eine gültige Testbuchung."""
    return Booking(
        booking_date=booking_date,
        voucher_no=voucher_no,
        description="Testbuchung",
        lines=(
            BookingLine(
                account_no="1200",
                side=EntrySide.DEBIT,
                amount=amount,
            ),
            BookingLine(
                account_no="1600",
                side=EntrySide.CREDIT,
                amount=amount,
            ),
        ),
    )


def test_new_journal_is_empty() -> None:
    journal = Journal()

    assert len(journal) == 0
    assert journal.bookings == ()
    assert not journal


def test_booking_can_be_added() -> None:
    journal = Journal()
    booking = create_booking()

    journal.add(booking)

    assert len(journal) == 1
    assert journal.bookings == (booking,)
    assert journal


def test_multiple_bookings_preserve_insertion_order() -> None:
    journal = Journal()
    first = create_booking(voucher_no="RE-1001")
    second = create_booking(voucher_no="RE-1002")

    journal.add(first)
    journal.add(second)

    assert journal.bookings == (first, second)
    assert tuple(journal) == (first, second)


def test_booking_can_be_retrieved_by_id() -> None:
    journal = Journal()
    booking = create_booking()
    journal.add(booking)

    result = journal.get(booking.booking_id)

    assert result is booking


def test_booking_id_membership() -> None:
    journal = Journal()
    booking = create_booking()
    journal.add(booking)

    assert booking.booking_id in journal
    assert uuid4() not in journal


def test_duplicate_booking_id_is_rejected() -> None:
    journal = Journal()
    booking = create_booking()

    journal.add(booking)

    with pytest.raises(
        ValueError,
        match="bereits im Journal",
    ):
        journal.add(booking)


def test_non_booking_object_is_rejected() -> None:
    journal = Journal()

    with pytest.raises(TypeError, match="Booking-Objekte"):
        journal.add("invalid")  # type: ignore[arg-type]


def test_unknown_booking_id_raises_key_error() -> None:
    journal = Journal()
    unknown_id = uuid4()

    with pytest.raises(KeyError, match="Keine Buchung"):
        journal.get(unknown_id)


def test_invalid_booking_id_is_rejected() -> None:
    journal = Journal()

    with pytest.raises(TypeError, match="UUID"):
        journal.get("invalid")  # type: ignore[arg-type]


def test_find_by_voucher_number() -> None:
    journal = Journal()
    first = create_booking(voucher_no="RE-1001")
    second = create_booking(voucher_no="RE-1002")

    journal.add(first)
    journal.add(second)

    result = journal.find_by_voucher_no("RE-1002")

    assert result == (second,)


def test_voucher_number_search_is_case_insensitive() -> None:
    journal = Journal()
    booking = create_booking(voucher_no="Re-1001")
    journal.add(booking)

    result = journal.find_by_voucher_no("re-1001")

    assert result == (booking,)


def test_voucher_number_search_trims_input() -> None:
    journal = Journal()
    booking = create_booking(voucher_no="RE-1001")
    journal.add(booking)

    result = journal.find_by_voucher_no("  RE-1001  ")

    assert result == (booking,)


def test_find_by_voucher_number_returns_all_matches() -> None:
    journal = Journal()
    first = create_booking(voucher_no="RE-1001")
    second = create_booking(voucher_no="RE-1001")

    journal.add(first)
    journal.add(second)

    result = journal.find_by_voucher_no("RE-1001")

    assert result == (first, second)


def test_find_by_voucher_number_ignores_none() -> None:
    journal = Journal()
    booking = create_booking(voucher_no=None)
    journal.add(booking)

    result = journal.find_by_voucher_no("RE-1001")

    assert result == ()


def test_empty_voucher_search_is_rejected() -> None:
    journal = Journal()

    with pytest.raises(ValueError, match="darf nicht leer"):
        journal.find_by_voucher_no("   ")


def test_invalid_voucher_search_is_rejected() -> None:
    journal = Journal()

    with pytest.raises(TypeError, match="Zeichenkette"):
        journal.find_by_voucher_no(1001)  # type: ignore[arg-type]


def test_find_by_date() -> None:
    journal = Journal()
    first = create_booking(
        booking_date=date(2026, 7, 27),
        voucher_no="RE-1001",
    )
    second = create_booking(
        booking_date=date(2026, 7, 28),
        voucher_no="RE-1002",
    )

    journal.add(first)
    journal.add(second)

    result = journal.find_by_date(date(2026, 7, 28))

    assert result == (second,)


def test_find_by_date_returns_all_matches() -> None:
    journal = Journal()
    first = create_booking(
        booking_date=date(2026, 7, 27),
        voucher_no="RE-1001",
    )
    second = create_booking(
        booking_date=date(2026, 7, 27),
        voucher_no="RE-1002",
    )

    journal.add(first)
    journal.add(second)

    result = journal.find_by_date(date(2026, 7, 27))

    assert result == (first, second)


def test_invalid_search_date_is_rejected() -> None:
    journal = Journal()

    with pytest.raises(TypeError, match="Buchungsdatum"):
        journal.find_by_date("2026-07-27")  # type: ignore[arg-type]


def test_find_by_date_range() -> None:
    journal = Journal()
    first = create_booking(
        booking_date=date(2026, 7, 26),
        voucher_no="RE-1001",
    )
    second = create_booking(
        booking_date=date(2026, 7, 27),
        voucher_no="RE-1002",
    )
    third = create_booking(
        booking_date=date(2026, 7, 28),
        voucher_no="RE-1003",
    )

    journal.add(first)
    journal.add(second)
    journal.add(third)

    result = journal.find_by_date_range(
        date(2026, 7, 27),
        date(2026, 7, 28),
    )

    assert result == (second, third)


def test_date_range_includes_start_and_end_date() -> None:
    journal = Journal()
    first = create_booking(
        booking_date=date(2026, 7, 27),
        voucher_no="RE-1001",
    )
    second = create_booking(
        booking_date=date(2026, 7, 28),
        voucher_no="RE-1002",
    )

    journal.add(first)
    journal.add(second)

    result = journal.find_by_date_range(
        date(2026, 7, 27),
        date(2026, 7, 28),
    )

    assert result == (first, second)


def test_invalid_date_range_is_rejected() -> None:
    journal = Journal()

    with pytest.raises(
        ValueError,
        match="Anfangsdatum",
    ):
        journal.find_by_date_range(
            date(2026, 7, 28),
            date(2026, 7, 27),
        )


def test_invalid_start_date_is_rejected() -> None:
    journal = Journal()

    with pytest.raises(TypeError, match="Anfangsdatum"):
        journal.find_by_date_range(
            "2026-07-27",  # type: ignore[arg-type]
            date(2026, 7, 28),
        )


def test_invalid_end_date_is_rejected() -> None:
    journal = Journal()

    with pytest.raises(TypeError, match="Enddatum"):
        journal.find_by_date_range(
            date(2026, 7, 27),
            "2026-07-28",  # type: ignore[arg-type]
        )


def test_bookings_property_does_not_expose_internal_list() -> None:
    journal = Journal()
    booking = create_booking()
    journal.add(booking)

    result = journal.bookings

    assert isinstance(result, tuple)

    with pytest.raises(TypeError):
        result[0] = booking  # type: ignore[index]
        
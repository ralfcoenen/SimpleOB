"""Tests für Buchungszeilen."""

from dataclasses import FrozenInstanceError
from decimal import Decimal

import pytest

from simpleob.domain import BookingLine, EntrySide


def test_debit_booking_line_is_created() -> None:
    line = BookingLine(
    account_number="1200",
    side=EntrySide.DEBIT,
    amount=Decimal("100.00"),
    )

    
    assert line.account_number == "1200"
    assert line.side is EntrySide.DEBIT
    assert line.amount == Decimal("100.00")
    assert line.is_debit
    assert not line.is_credit

def test_credit_booking_line_is_created() -> None:
    line = BookingLine(
    account_number="8400",
    side=EntrySide.CREDIT,
    amount=Decimal("250.00"),
    )

    assert line.side is EntrySide.CREDIT
    assert line.is_credit
    assert not line.is_debit


def test_account_number_is_trimmed() -> None:
    line = BookingLine(
    account_number=" 1200 ",
    side=EntrySide.DEBIT,
    amount="100.00",
    )


    assert line.account_number == "1200"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
    ("DEBIT", EntrySide.DEBIT),
    ("debit", EntrySide.DEBIT),
    ("SOLL", EntrySide.DEBIT),
    ("soll", EntrySide.DEBIT),
    ("CREDIT", EntrySide.CREDIT),
    ("credit", EntrySide.CREDIT),
    ("HABEN", EntrySide.CREDIT),
    ("haben", EntrySide.CREDIT),
    ],
    )
def test_side_is_normalized(
    value: str,
    expected: EntrySide,
    ) -> None:
    line = BookingLine(
    account_number="1200",
    side=value,  # type: ignore[arg-type]
    amount="100.00",
    )


    assert line.side is expected
    

def test_string_amount_is_converted_to_decimal() -> None:
    line = BookingLine(
    account_number="1200",
    side=EntrySide.DEBIT,
    amount="100.50",
    )

    assert line.amount == Decimal("100.50")


def test_integer_amount_is_converted_to_decimal() -> None:
    line = BookingLine(
    account_number="1200",
    side=EntrySide.DEBIT,
    amount=100,  # type: ignore[arg-type]
    )


    assert line.amount == Decimal("100.00")


def test_amount_is_rounded_to_two_decimal_places() -> None:
    line = BookingLine(
    account_number="1200",
    side=EntrySide.DEBIT,
    amount="12.345",
    )


    assert line.amount == Decimal("12.34")


@pytest.mark.parametrize(
    "amount",
    [
    "0.00",
    "-0.01",
    -10,
    ],
    )
def test_non_positive_amount_is_rejected(
    amount: str | int,
    ) -> None:
    with pytest.raises(ValueError, match="größer als 0,00"):
        BookingLine(
        account_number="1200",
        side=EntrySide.DEBIT,
        amount=amount,  # type: ignore[arg-type]
        )

def test_float_amount_is_rejected() -> None:
    with pytest.raises(TypeError, match="Float"):
        BookingLine(
        account_number="1200",
        side=EntrySide.DEBIT,
        amount=10.50,  # type: ignore[arg-type]
        )

def test_empty_account_number_is_rejected() -> None:
    with pytest.raises(ValueError, match="Kontonummer"):
        BookingLine(
        account_number="   ",
        side=EntrySide.DEBIT,
        amount="100.00",
        )

def test_non_string_account_number_is_rejected() -> None:
    with pytest.raises(TypeError, match="Zeichenkette"):
        BookingLine(
        account_number=1200,  # type: ignore[arg-type]
        side=EntrySide.DEBIT,
        amount="100.00",
        )

def test_invalid_side_is_rejected() -> None:
    with pytest.raises(ValueError, match="gültige Buchungsseite"):
        BookingLine(
        account_number="1200",
        side="LEFT",  # type: ignore[arg-type]
        amount="100.00",
        )

def test_booking_line_is_immutable() -> None:
    line = BookingLine(
    account_number="1200",
    side=EntrySide.DEBIT,
    amount="100.00",
    )


    with pytest.raises(FrozenInstanceError):
        line.amount = Decimal("200.00")  # type: ignore[misc]


def test_equal_booking_lines_are_equal() -> None:
    first = BookingLine(
    account_number="1200",
    side=EntrySide.DEBIT,
    amount="100.00",
    )
    second = BookingLine(
    account_number="1200",
    side=EntrySide.DEBIT,
    amount=Decimal("100.00"),
    )


    assert first == second


def test_booking_line_can_be_used_in_set() -> None:
    line = BookingLine(
    account_number="1200",
    side=EntrySide.DEBIT,
    amount="100.00",
    )


    assert {line} == {line}


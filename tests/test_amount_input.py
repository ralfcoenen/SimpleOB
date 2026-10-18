"""Tests für deutsche Betragseingaben."""

from decimal import Decimal

import pytest

from simpleob.amount_input import (
    format_german_amount,
    normalize_german_amount,
    parse_german_amount,
)


@pytest.mark.parametrize(
    ("text", "expected"),
    (
        ("1234,56", Decimal("1234.56")),
        ("1.234,56", Decimal("1234.56")),
        ("0,00", Decimal("0.00")),
        ("-1.234,56", Decimal("-1234.56")),
        (" 1234,50 ", Decimal("1234.50")),
    ),
)
def test_parses_german_amount(
    text: str,
    expected: Decimal,
) -> None:
    assert parse_german_amount(text) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    (
        (Decimal("0"), "0,00"),
        (Decimal("1234.5"), "1.234,50"),
        (Decimal("1234567.89"), "1.234.567,89"),
        (Decimal("-1234.5"), "-1.234,50"),
    ),
)
def test_formats_german_amount(
    value: Decimal,
    expected: str,
) -> None:
    assert format_german_amount(value) == expected


def test_normalizes_german_amount() -> None:
    assert (
        normalize_german_amount("1234,5")
        == "1.234,50"
    )


@pytest.mark.parametrize(
    "text",
    (
        "",
        "   ",
        "abc",
        "12,34,56",
    ),
)
def test_rejects_invalid_german_amount(
    text: str,
) -> None:
    with pytest.raises(ValueError):
        parse_german_amount(text)

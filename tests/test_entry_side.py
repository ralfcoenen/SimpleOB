"""Tests für die Buchungsseiten."""

import pytest

from simpleob.domain import EntrySide


def test_debit_has_expected_value() -> None:
    assert EntrySide.DEBIT.value == "DEBIT"


def test_credit_has_expected_value() -> None:
    assert EntrySide.CREDIT.value == "CREDIT"


def test_debit_has_german_name() -> None:
    assert EntrySide.DEBIT.german_name == "Soll"


def test_credit_has_german_name() -> None:
    assert EntrySide.CREDIT.german_name == "Haben"


def test_entry_side_is_also_a_string() -> None:
    assert isinstance(EntrySide.DEBIT, str)
    assert EntrySide.DEBIT == "DEBIT"


def test_string_representation_uses_technical_value() -> None:
    assert str(EntrySide.DEBIT) == "DEBIT"
    assert str(EntrySide.CREDIT) == "CREDIT"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("DEBIT", EntrySide.DEBIT),
        ("debit", EntrySide.DEBIT),
        (" Debit ", EntrySide.DEBIT),
        ("SOLL", EntrySide.DEBIT),
        ("soll", EntrySide.DEBIT),
        ("CREDIT", EntrySide.CREDIT),
        ("credit", EntrySide.CREDIT),
        (" Credit ", EntrySide.CREDIT),
        ("HABEN", EntrySide.CREDIT),
        ("haben", EntrySide.CREDIT),
    ],
)
def test_from_value_accepts_supported_strings(
    value: str,
    expected: EntrySide,
) -> None:
    assert EntrySide.from_value(value) is expected


def test_from_value_accepts_existing_entry_side() -> None:
    assert EntrySide.from_value(EntrySide.DEBIT) is EntrySide.DEBIT
    assert EntrySide.from_value(EntrySide.CREDIT) is EntrySide.CREDIT


@pytest.mark.parametrize(
    "value",
    [
        "",
        " ",
        "D",
        "C",
        "links",
        "rechts",
        "unknown",
    ],
)
def test_invalid_string_is_rejected(value: str) -> None:
    with pytest.raises(ValueError, match="gültige Buchungsseite"):
        EntrySide.from_value(value)


@pytest.mark.parametrize(
    "value",
    [
        None,
        1,
        True,
        object(),
    ],
)
def test_invalid_type_is_rejected(value: object) -> None:
    with pytest.raises(TypeError, match="EntrySide oder str"):
        EntrySide.from_value(value)  # type: ignore[arg-type]

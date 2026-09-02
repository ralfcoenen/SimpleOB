"""Tests für TaxNumberNormalizer."""

import pytest

from openbilanz.domain.tax_number_normalizer import (
    TaxNumberNormalizer,
)


@pytest.mark.parametrize(
    (
        "federal_state",
        "tax_number",
        "expected",
    ),
    (
        ("BW", "12/345/67890", "2812034567890"),
        ("BY", "123/456/78901", "9123045678901"),
        ("BE", "12/345/67890", "1112034567890"),
        ("BB", "123/456/78901", "3123045678901"),
        ("HB", "12/345/67890", "2412034567890"),
        ("HH", "12/345/67890", "2212034567890"),
        ("HE", "012/345/67890", "2612034567890"),
        ("MV", "123/456/78901", "4123045678901"),
        ("NI", "12/345/67890", "2312034567890"),
        ("NW", "123/4567/8901", "5123045678901"),
        ("RP", "12/345/67890", "2712034567890"),
        ("SL", "123/456/78901", "1123045678901"),
        ("SN", "123/456/78901", "3123045678901"),
        ("ST", "123/456/78901", "3123045678901"),
        ("SH", "12/345/67890", "2112034567890"),
        ("TH", "123/456/78901", "4123045678901"),
    ),
)
def test_normalizes_tax_number_for_all_federal_states(
    federal_state: str,
    tax_number: str,
    expected: str,
) -> None:
    result = TaxNumberNormalizer().normalize(
        federal_state=federal_state,
        tax_number=tax_number,
    )

    assert result == expected
    assert len(result) == 13
    assert result.isdigit()
    assert result[4] == "0"


def test_accepts_nrw_tax_number_without_separators() -> None:
    result = TaxNumberNormalizer().normalize(
        federal_state="NW",
        tax_number="12345678901",
    )

    assert result == "5123045678901"


def test_accepts_common_separators() -> None:
    normalizer = TaxNumberNormalizer()

    assert (
        normalizer.normalize(
            federal_state="NW",
            tax_number="123-4567-8901",
        )
        == "5123045678901"
    )

    assert (
        normalizer.normalize(
            federal_state="NW",
            tax_number="123 4567 8901",
        )
        == "5123045678901"
    )


def test_rejects_invalid_nrw_tax_number() -> None:
    with pytest.raises(
        ValueError,
        match="Ungültige Steuernummer für Nordrhein-Westfalen",
    ):
        TaxNumberNormalizer().normalize(
            federal_state="NW",
            tax_number="1234/5678/9012",
        )


def test_rejects_hesse_without_leading_zero() -> None:
    with pytest.raises(
        ValueError,
        match="Ungültige Steuernummer für Hessen",
    ):
        TaxNumberNormalizer().normalize(
            federal_state="HE",
            tax_number="12/345/67890",
        )


def test_rejects_invalid_characters() -> None:
    with pytest.raises(
        ValueError,
        match="Steuernummer darf nur Ziffern",
    ):
        TaxNumberNormalizer().normalize(
            federal_state="NW",
            tax_number="123/4567/A901",
        )


def test_rejects_unsupported_federal_state() -> None:
    with pytest.raises(
        ValueError,
        match="Bundesland wird nicht unterstützt",
    ):
        TaxNumberNormalizer().normalize(
            federal_state="XX",
            tax_number="123/4567/8901",
        )

"""Tests für Unternehmenskennungen der GCD-Taxonomie."""

import pytest

from openbilanz.taxonomy.gcd_company_identifiers import (
    GcdCompanyIdentifiers,
)


def test_gcd_company_identifiers_accept_standard_identifiers() -> None:
    """Der Standardfall akzeptiert die steuerlichen Unternehmenskennungen."""

    identifiers = GcdCompanyIdentifiers(
        tax_number_13="1234567890123",
        tax_id="12345678901",
        tax_economic_id="DE123456789",
        bf4="1234",
    )

    assert identifiers.tax_number_13 == "1234567890123"
    assert identifiers.tax_id == "12345678901"
    assert identifiers.tax_economic_id == "DE123456789"
    assert identifiers.bf4 == "1234"


@pytest.mark.parametrize(
    "tax_number_13",
    (
        "",
        " ",
        "123456789012",
        "12345678901234",
        "ABCDEFGHIJKLM",
    ),
)
def test_gcd_company_identifiers_reject_invalid_st13(
    tax_number_13: str,
) -> None:
    """ST13 muss exakt 13 Ziffern enthalten."""

    with pytest.raises(
        ValueError,
        match="tax_number_13 must contain exactly 13 digits",
    ):
        GcdCompanyIdentifiers(
            tax_number_13=tax_number_13,
        )


@pytest.mark.parametrize(
    "bf4",
    (
        "",
        " ",
        "123",
        "12345",
        "ABCD",
    ),
)
def test_gcd_company_identifiers_reject_invalid_bf4(
    bf4: str,
) -> None:
    """BF4 muss, falls gesetzt, exakt vier Ziffern enthalten."""

    with pytest.raises(
        ValueError,
        match="bf4 must contain exactly 4 digits",
    ):
        GcdCompanyIdentifiers(
            tax_number_13="1234567890123",
            bf4=bf4,
        )


def test_gcd_company_identifiers_accept_optional_stid_and_stwid() -> None:
    """STID und STWID sind im Datenmodell optional."""

    identifiers = GcdCompanyIdentifiers(
        tax_number_13="1234567890123",
    )

    assert identifiers.tax_id is None
    assert identifiers.tax_economic_id is None
    assert identifiers.bf4 is None

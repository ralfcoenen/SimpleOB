"""Tests für GCD-Gesellschafterdaten."""

import pytest

from simpleob.taxonomy.gcd_shareholder import (
    GcdShareDivideKey,
    GcdShareholder,
    GcdShareholderGroup,
    GcdShareholderLegalStatus,
)


def test_gcd_share_divide_key_accepts_valid_fraction() -> None:
    """Beteiligungsquoten werden als Zähler/Nenner abgebildet."""

    key = GcdShareDivideKey(
        numerator="25",
        denominator="100",
    )

    assert key.numerator == "25"
    assert key.denominator == "100"


@pytest.mark.parametrize(
    "numerator",
    (
        "",
        " ",
        "A",
        "12345678901234567",
    ),
)
def test_gcd_share_divide_key_rejects_invalid_numerator(
    numerator: str,
) -> None:
    """Der Zähler muss 1 bis 16 Ziffern enthalten."""

    with pytest.raises(
        ValueError,
        match="numerator must contain 1 to 16 digits",
    ):
        GcdShareDivideKey(
            numerator=numerator,
            denominator="100",
        )


@pytest.mark.parametrize(
    "denominator",
    (
        "",
        " ",
        "0",
        "01",
        "A",
        "12345678901234567",
    ),
)
def test_gcd_share_divide_key_rejects_invalid_denominator(
    denominator: str,
) -> None:
    """Der Nenner muss positiv und höchstens 16-stellig sein."""

    with pytest.raises(
        ValueError,
        match="denominator must contain 1 to 16 digits and must not start with zero",
    ):
        GcdShareDivideKey(
            numerator="25",
            denominator=denominator,
        )


@pytest.mark.parametrize(
    "value",
    (
        GcdShareholderLegalStatus.NATURAL_PERSON,
        GcdShareholderLegalStatus.LEGAL_ENTITY,
        GcdShareholderLegalStatus.PARTNERSHIP,
        GcdShareholderLegalStatus.PUBLIC_LAW_ENTITY,
    ),
)
def test_gcd_shareholder_accepts_legal_status(
    value: GcdShareholderLegalStatus,
) -> None:
    """Die Taxonomie-Rechtsformen werden typisiert abgebildet."""

    shareholder = GcdShareholder(
        name="Mustermann",
        shareholder_id="1",
        tax_number="1234567890123",
        tax_id="12345678901",
        wid="WID-1",
        legal_status=value,
        share_divide_key=GcdShareDivideKey(
            numerator="100",
            denominator="100",
        ),
    )

    assert shareholder.legal_status is value


@pytest.mark.parametrize(
    "group",
    (
        GcdShareholderGroup.FULLY_LIABLE,
        GcdShareholderGroup.OTHER,
        GcdShareholderGroup.INDIRECT,
        GcdShareholderGroup.LIMITED,
    ),
)
def test_gcd_shareholder_accepts_group(
    group: GcdShareholderGroup,
) -> None:
    """Gesellschaftergruppen werden typisiert abgebildet."""

    shareholder = GcdShareholder(
        name="Mustermann",
        shareholder_id="1",
        tax_number="1234567890123",
        tax_id="12345678901",
        wid="WID-1",
        legal_status=GcdShareholderLegalStatus.NATURAL_PERSON,
        share_divide_key=GcdShareDivideKey(
            numerator="100",
            denominator="100",
        ),
        group=group,
    )

    assert shareholder.group is group


def test_gcd_shareholder_requires_name() -> None:
    """Der Gesellschaftername darf nicht leer sein."""

    with pytest.raises(
        ValueError,
        match="name must not be blank",
    ):
        GcdShareholder(
            name=" ",
            shareholder_id="1",
            tax_number="1234567890123",
            tax_id="12345678901",
            wid="WID-1",
            legal_status=GcdShareholderLegalStatus.NATURAL_PERSON,
            share_divide_key=GcdShareDivideKey(
                numerator="100",
                denominator="100",
            ),
        )


def test_gcd_shareholder_validates_tax_number() -> None:
    """Die Gesellschafter-Steuernummer muss 13-stellig sein."""

    with pytest.raises(
        ValueError,
        match="tax_number must contain exactly 13 digits",
    ):
        GcdShareholder(
            name="Mustermann",
            shareholder_id="1",
            tax_number="123",
            tax_id="12345678901",
            wid="WID-1",
            legal_status=GcdShareholderLegalStatus.NATURAL_PERSON,
            share_divide_key=GcdShareDivideKey(
                numerator="100",
                denominator="100",
            ),
        )
    
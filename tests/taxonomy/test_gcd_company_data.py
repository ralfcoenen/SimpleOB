"""Tests für die Unternehmensstammdaten der GCD-Taxonomie."""

from uuid import uuid4

import pytest

from simpleob.domain.company import Company
from simpleob.taxonomy.gcd_company_data import GcdCompanyData


def test_gcd_company_data_contains_company_identity() -> None:
    """GCD-Stammdaten verbinden Unternehmen und steuerliche Identität."""

    company = Company(
        company_id=uuid4(),
        name="Muster UG (haftungsbeschränkt)",
    )

    data = GcdCompanyData(
        company=company,
        tax_number="1234567890123",
        legal_form="UG (haftungsbeschränkt)",
    )

    assert data.company is company
    assert data.company.name == (
        "Muster UG (haftungsbeschränkt)"
    )
    assert data.tax_number == "1234567890123"
    assert data.legal_form == "UG (haftungsbeschränkt)"


@pytest.mark.parametrize(
    "tax_number",
    (
        "",
        " ",
        "   ",
    ),
)
def test_gcd_company_data_rejects_blank_tax_number(
    tax_number: str,
) -> None:
    """Die Steuernummer darf nicht leer sein."""

    company = Company(
        company_id=uuid4(),
        name="Muster UG (haftungsbeschränkt)",
    )

    with pytest.raises(
        ValueError,
        match="tax_number must not be blank",
    ):
        GcdCompanyData(
            company=company,
            tax_number=tax_number,
            legal_form="UG (haftungsbeschränkt)",
        )


def test_gcd_company_data_requires_company() -> None:
    """Das GCD-Datenobjekt benötigt ein fachliches Unternehmen."""

    with pytest.raises(
        TypeError,
        match="company must be a Company",
    ):
        GcdCompanyData(
            company="Muster UG",  # type: ignore[arg-type]
            tax_number="123/4567/8901",
            legal_form="UG (haftungsbeschränkt)",
        )


@pytest.mark.parametrize(
    "tax_number",
    (
        "123/4567/8901",
        "12345678901",
        "123456789012",
        "12345678901234",
        "ABCDEFGHIJKLM",
    ),
)
def test_gcd_company_data_rejects_invalid_tax_number(
    tax_number: str,
) -> None:
    """Die GCD-Steuernummer muss 13-stellig numerisch sein."""

    company = Company(
        company_id=uuid4(),
        name="Muster UG (haftungsbeschränkt)",
    )

    with pytest.raises(
        ValueError,
        match="tax_number must contain exactly 13 digits",
    ):
        GcdCompanyData(
            company=company,
            tax_number=tax_number,
            legal_form="UG (haftungsbeschränkt)",
        )
def test_gcd_company_data_accepts_13_digit_tax_number() -> None:
    """Eine 13-stellige Steuernummer wird akzeptiert."""

    company = Company(
        company_id=uuid4(),
        name="Muster UG (haftungsbeschränkt)",
    )

    data = GcdCompanyData(
        company=company,
        tax_number="1234567890123",
        legal_form="UG (haftungsbeschränkt)",
    )

    assert data.tax_number == "1234567890123"


def test_gcd_company_data_contains_required_company_details() -> None:
    """GCD-Stammdaten enthalten die erforderlichen Unternehmensangaben."""

    company = Company(
        company_id=uuid4(),
        name="Muster UG (haftungsbeschränkt)",
    )

    data = GcdCompanyData(
        company=company,
        tax_number="1234567890123",
        legal_form="UG (haftungsbeschränkt)",
        street="Musterstraße",
        house_number="12a",
        postal_code="12345",
        city="Musterstadt",
        country="DE",
        business="Softwareentwicklung",
    )

    assert data.street == "Musterstraße"
    assert data.house_number == "12a"
    assert data.postal_code == "12345"
    assert data.city == "Musterstadt"
    assert data.country == "DE"
    assert data.business == "Softwareentwicklung"
    
        
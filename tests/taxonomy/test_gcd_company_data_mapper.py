"""Tests für GcdCompanyDataMapper."""

from uuid import uuid4

import pytest

from openbilanz.domain.company import Company
from openbilanz.domain.company_master_data import (
    CompanyMasterData,
)
from openbilanz.taxonomy.gcd_company_data_mapper import (
    GcdCompanyDataMapper,
)


def _company() -> Company:
    return Company(
        company_id=uuid4(),
        name="Muster UG",
    )


def test_maps_complete_company_master_data() -> None:
    master_data = CompanyMasterData(
        company=_company(),
        legal_form="UG (haftungsbeschränkt)",
        tax_number="1234567890123",
        tax_office="Finanzamt Musterstadt",
        tax_id="12345678901",
        tax_economic_id="DE123456789",
        bf4="1234",
        street="Musterstraße",
        house_number="12a",
        postal_code="12345",
        city="Musterstadt",
        country="DE",
        business="Softwareentwicklung",
    )

    result = GcdCompanyDataMapper().map(
        master_data
    )

    assert result.company_data.company == (
        master_data.company
    )
    assert (
        result.company_data.tax_number
        == "1234567890123"
    )
    assert (
        result.company_data.legal_form
        == "UG (haftungsbeschränkt)"
    )
    assert result.company_data.street == "Musterstraße"
    assert result.company_data.house_number == "12a"
    assert result.company_data.postal_code == "12345"
    assert result.company_data.city == "Musterstadt"
    assert result.company_data.country == "DE"
    assert (
        result.company_data.business
        == "Softwareentwicklung"
    )

    assert (
        result.identifiers.tax_number_13
        == "1234567890123"
    )
    assert result.identifiers.tax_id == "12345678901"
    assert (
        result.identifiers.tax_economic_id
        == "DE123456789"
    )
    assert result.identifiers.bf4 == "1234"


def test_maps_empty_optional_identifiers_to_none() -> None:
    master_data = CompanyMasterData(
        company=_company(),
        legal_form="UG (haftungsbeschränkt)",
        tax_number="1234567890123",
    )

    result = GcdCompanyDataMapper().map(
        master_data
    )

    assert result.identifiers.tax_id is None
    assert result.identifiers.tax_economic_id is None
    assert result.identifiers.bf4 is None


def test_rejects_incomplete_master_data() -> None:
    master_data = CompanyMasterData(
        company=_company(),
    )

    with pytest.raises(
        ValueError,
        match=(
            "Die Unternehmensstammdaten sind für "
            "die E-Bilanz noch unvollständig."
        ),
    ):
        GcdCompanyDataMapper().map(
            master_data
        )


def test_rejects_wrong_type() -> None:
    with pytest.raises(
        TypeError,
        match=(
            "master_data must be a CompanyMasterData"
        ),
    ):
        GcdCompanyDataMapper().map(
            object()  # type: ignore[arg-type]
        )

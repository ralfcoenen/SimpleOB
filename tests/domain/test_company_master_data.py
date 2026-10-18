"""Tests für CompanyMasterData."""

from uuid import uuid4

import pytest

from simpleob.domain.company import Company
from simpleob.domain.company_master_data import (
    LEGAL_FORM_GMBH,
    LEGAL_FORM_SOLE_PROPRIETORSHIP_GBR,
    LEGAL_FORM_UG,
    CompanyMasterData,
)


def _company() -> Company:
    return Company(
        company_id=uuid4(),
        name="Test UG",
    )


def _complete_master_data(
    **overrides: str,
) -> CompanyMasterData:
    values = {
        "legal_form": "UG (haftungsbeschränkt)",
        "tax_number": "123/4567/8901",
        "federal_state": "NW",
        "street": "Musterstraße",
        "house_number": "12a",
        "postal_code": "12345",
        "city": "Musterstadt",
        "country": "DE",
        "business": "Softwareentwicklung",
    }

    values.update(overrides)

    return CompanyMasterData(
        company=_company(),
        **values,
    )


def test_allows_incomplete_master_data() -> None:
    master_data = CompanyMasterData(
        company=_company(),
    )

    assert master_data.is_e_bilanz_ready is False


def test_is_e_bilanz_ready_with_required_data() -> None:
    master_data = _complete_master_data()

    assert master_data.is_e_bilanz_ready is True


@pytest.mark.parametrize(
    "field_name",
    (
        "legal_form",
        "tax_number",
        "federal_state",
        "street",
        "house_number",
        "postal_code",
        "city",
        "country",
        "business",
    ),
)
def test_is_not_e_bilanz_ready_when_required_field_is_blank(
    field_name: str,
) -> None:
    master_data = _complete_master_data(
        **{field_name: ""},
    )

    assert master_data.is_e_bilanz_ready is False


def test_validate_e_bilanz_ready_accepts_complete_master_data() -> None:
    master_data = _complete_master_data()

    master_data.validate_e_bilanz_ready()


def test_validate_e_bilanz_ready_reports_missing_fields() -> None:
    master_data = _complete_master_data(
        street="",
        postal_code="",
        business="",
    )

    with pytest.raises(
        ValueError,
        match=(
            "Für die E-Bilanz fehlen folgende "
            "Unternehmensstammdaten: "
            "Straße, PLZ, Geschäftstätigkeit"
        ),
    ):
        master_data.validate_e_bilanz_ready()


def test_validate_e_bilanz_ready_rejects_invalid_tax_number() -> None:
    master_data = _complete_master_data(
        tax_number="1234/5678/9012",
    )

    with pytest.raises(
        ValueError,
        match="Ungültige Steuernummer für Nordrhein-Westfalen",
    ):
        master_data.validate_e_bilanz_ready()


def test_allows_state_specific_tax_number_format() -> None:
    master_data = CompanyMasterData(
        company=_company(),
        tax_number="123/4567/8901",
        federal_state="NW",
    )

    assert master_data.tax_number == "123/4567/8901"


def test_rejects_invalid_bf4() -> None:
    with pytest.raises(
        ValueError,
        match="bf4 must contain exactly 4 digits",
    ):
        CompanyMasterData(
            company=_company(),
            bf4="123",
        )


def test_rejects_surrounding_whitespace() -> None:
    with pytest.raises(
        ValueError,
        match="city must not contain surrounding whitespace",
    ):
        CompanyMasterData(
            company=_company(),
            city=" Berlin ",
        )


def test_accepts_federal_state() -> None:
    master_data = CompanyMasterData(
        company=_company(),
        federal_state="NW",
    )

    assert master_data.federal_state == "NW"


def test_rejects_invalid_federal_state() -> None:
    with pytest.raises(
        ValueError,
        match="federal_state must be a valid German federal state code",
    ):
        CompanyMasterData(
            company=_company(),
            federal_state="XX",
        )


def test_is_not_e_bilanz_ready_without_federal_state() -> None:
    master_data = _complete_master_data(
        federal_state="",
    )

    assert master_data.is_e_bilanz_ready is False

def test_supported_corporate_legal_forms_support_e_bilanz() -> None:
    ug_master_data = _complete_master_data(
        legal_form=LEGAL_FORM_UG,
    )
    gmbh_master_data = _complete_master_data(
        legal_form=LEGAL_FORM_GMBH,
    )

    assert ug_master_data.supports_e_bilanz is True
    assert gmbh_master_data.supports_e_bilanz is True


def test_sole_proprietorship_gbr_does_not_support_e_bilanz() -> None:
    master_data = _complete_master_data(
        legal_form=LEGAL_FORM_SOLE_PROPRIETORSHIP_GBR,
    )

    assert master_data.supports_e_bilanz is False
    assert master_data.is_e_bilanz_ready is False

    with pytest.raises(
        ValueError,
        match="Die Rechtsform wird vom E-Bilanz-Pfad nicht unterstützt",
    ):
        master_data.validate_e_bilanz_ready()

"""Tests für CompanyMasterData."""

from uuid import uuid4

import pytest

from openbilanz.domain.company import Company
from openbilanz.domain.company_master_data import (
    CompanyMasterData,
)


def _company() -> Company:
    return Company(
        company_id=uuid4(),
        name="Test UG",
    )


def test_allows_incomplete_master_data() -> None:
    master_data = CompanyMasterData(
        company=_company(),
    )

    assert master_data.is_e_bilanz_ready is False

def test_is_e_bilanz_ready_with_required_data() -> None:
    master_data = CompanyMasterData(
        company=_company(),
        legal_form="UG (haftungsbeschränkt)",
        tax_number="123/4567/8901",
        federal_state="NW",
    )

    assert master_data.is_e_bilanz_ready is True

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
    master_data = CompanyMasterData(
        company=_company(),
        legal_form="UG (haftungsbeschränkt)",
        tax_number="123/4567/8901",
    )

    assert master_data.is_e_bilanz_ready is False
    


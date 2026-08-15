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
        tax_number="1234567890123",
    )

    assert master_data.is_e_bilanz_ready is True


def test_rejects_invalid_tax_number() -> None:
    with pytest.raises(
        ValueError,
        match="tax_number must contain exactly 13 digits",
    ):
        CompanyMasterData(
            company=_company(),
            tax_number="12345",
        )


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

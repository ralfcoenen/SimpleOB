"""Tests für Gesellschafter."""

from uuid import UUID, uuid4

import pytest

from openbilanz.domain.shareholder import Shareholder


def test_shareholder_accepts_valid_data() -> None:
    company_id = uuid4()

    shareholder = Shareholder(
        company_id=company_id,
        shareholder_number="1",
        name="Muster",
        first_name="Max",
        legal_status="NPP",
        share_numerator="1",
        share_denominator="2",
        tax_number="1234567890123",
        tax_id="12345678901",
        wid="DE123456789",
        tax_number_federal_state="NW",
    )

    assert shareholder.company_id == company_id
    assert isinstance(
        shareholder.shareholder_id,
        UUID,
    )
    assert shareholder.shareholder_number == "1"
    assert shareholder.name == "Muster"
    assert shareholder.first_name == "Max"
    assert shareholder.legal_status == "NPP"
    assert shareholder.share_numerator == "1"
    assert shareholder.share_denominator == "2"
    assert shareholder.tax_number == "1234567890123"
    assert shareholder.tax_id == "12345678901"
    assert shareholder.wid == "DE123456789"
    assert shareholder.tax_number_federal_state == "NW"



def test_shareholder_accepts_missing_optional_data() -> None:
    shareholder = Shareholder(
        company_id=uuid4(),
        shareholder_number="1",
        name="Muster GmbH",
        legal_status="NPB",
        share_numerator="1",
        share_denominator="1",
    )

    assert shareholder.first_name == ""
    assert shareholder.tax_number == ""
    assert shareholder.tax_id == ""
    assert shareholder.wid == ""
    assert shareholder.tax_number_federal_state == ""


def test_shareholder_normalizes_text() -> None:
    shareholder = Shareholder(
        company_id=uuid4(),
        shareholder_number=" 1 ",
        name=" Muster ",
        first_name=" Max ",
        legal_status=" NPP ",
        share_numerator=" 1 ",
        share_denominator=" 2 ",
        tax_number=" 1234567890123 ",
        tax_id=" 12345678901 ",
        wid=" DE123456789 ",
    )

    assert shareholder.shareholder_number == "1"
    assert shareholder.name == "Muster"
    assert shareholder.first_name == "Max"
    assert shareholder.legal_status == "NPP"
    assert shareholder.share_numerator == "1"
    assert shareholder.share_denominator == "2"
    assert shareholder.tax_number == "1234567890123"
    assert shareholder.tax_id == "12345678901"
    assert shareholder.wid == "DE123456789"


def test_shareholder_rejects_invalid_company_id() -> None:
    with pytest.raises(
        TypeError,
        match="company_id must be a UUID",
    ):
        Shareholder(
            company_id="company",  # type: ignore[arg-type]
            shareholder_number="1",
            name="Muster",
            legal_status="NPP",
            share_numerator="1",
            share_denominator="1",
        )


def test_shareholder_rejects_invalid_shareholder_id() -> None:
    with pytest.raises(
        TypeError,
        match="shareholder_id must be a UUID",
    ):
        Shareholder(
            company_id=uuid4(),
            shareholder_number="1",
            name="Muster",
            legal_status="NPP",
            share_numerator="1",
            share_denominator="1",
            shareholder_id="shareholder",  # type: ignore[arg-type]
        )


@pytest.mark.parametrize(
    ("field_name", "field_value"),
    (
        ("shareholder_number", ""),
        ("name", ""),
        ("legal_status", ""),
        ("share_numerator", ""),
        ("share_denominator", ""),
    ),
)
def test_shareholder_rejects_blank_required_text(
    field_name: str,
    field_value: str,
) -> None:
    values = {
        "company_id": uuid4(),
        "shareholder_number": "1",
        "name": "Muster",
        "legal_status": "NPP",
        "share_numerator": "1",
        "share_denominator": "1",
    }
    values[field_name] = field_value

    with pytest.raises(
        ValueError,
        match=f"{field_name} must not be blank",
    ):
        Shareholder(**values)


def test_shareholder_rejects_non_numeric_share_numerator() -> None:
    with pytest.raises(
        ValueError,
        match="share_numerator must contain digits only",
    ):
        Shareholder(
            company_id=uuid4(),
            shareholder_number="1",
            name="Muster",
            legal_status="NPP",
            share_numerator="1a",
            share_denominator="2",
        )


def test_shareholder_rejects_non_numeric_share_denominator() -> None:
    with pytest.raises(
        ValueError,
        match="share_denominator must contain digits only",
    ):
        Shareholder(
            company_id=uuid4(),
            shareholder_number="1",
            name="Muster",
            legal_status="NPP",
            share_numerator="1",
            share_denominator="2a",
        )


def test_shareholder_rejects_zero_share_denominator() -> None:
    with pytest.raises(
        ValueError,
        match="share_denominator must be greater than zero",
    ):
        Shareholder(
            company_id=uuid4(),
            shareholder_number="1",
            name="Muster",
            legal_status="NPP",
            share_numerator="1",
            share_denominator="0",
        )


@pytest.mark.parametrize(
    "tax_number",
    (
        "123456789012",
        "12345678901234",
        "123456789012A",
    ),
)
def test_shareholder_rejects_invalid_tax_number(
    tax_number: str,
) -> None:
    with pytest.raises(
        ValueError,
        match="tax_number must contain exactly 13 digits",
    ):
        Shareholder(
            company_id=uuid4(),
            shareholder_number="1",
            name="Muster",
            legal_status="NPP",
            share_numerator="1",
            share_denominator="1",
            tax_number=tax_number,
        )

def test_shareholder_normalizes_north_rhine_westphalia_tax_number() -> None:
    shareholder = Shareholder(
        company_id=uuid4(),
        shareholder_number="1",
        name="Muster",
        legal_status="NPP",
        share_numerator="1",
        share_denominator="1",
        tax_number="123/4567/8901",
        tax_number_federal_state="NW",
    )

    assert shareholder.tax_number == "5123045678901"
    assert shareholder.tax_number_federal_state == "NW"


def test_shareholder_normalizes_bavarian_tax_number() -> None:
    shareholder = Shareholder(
        company_id=uuid4(),
        shareholder_number="1",
        name="Muster",
        legal_status="NPP",
        share_numerator="1",
        share_denominator="1",
        tax_number="123/456/78901",
        tax_number_federal_state="BY",
    )

    assert shareholder.tax_number == "9123045678901"
    assert shareholder.tax_number_federal_state == "BY"

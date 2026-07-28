"""Tests für die Domänenentität Company."""

from dataclasses import FrozenInstanceError
from uuid import UUID, uuid4

import pytest

from openbilanz.domain import Company


def test_company_accepts_valid_values() -> None:
    company_id = uuid4()

    company = Company(
        company_id=company_id,
        name="Muster UG (haftungsbeschränkt)",
    )

    assert company.company_id == company_id
    assert company.name == "Muster UG (haftungsbeschränkt)"


@pytest.mark.parametrize(
    "company_id",
    [
        None,
        "550e8400-e29b-41d4-a716-446655440000",
        123,
        object(),
    ],
)
def test_company_rejects_invalid_company_id_type(
    company_id: object,
) -> None:
    with pytest.raises(TypeError, match="company_id"):
        Company(
            company_id=company_id,  # type: ignore[arg-type]
            name="Muster UG",
        )


@pytest.mark.parametrize(
    "name",
    [
        None,
        123,
        object(),
    ],
)
def test_company_rejects_invalid_name_type(
    name: object,
) -> None:
    with pytest.raises(TypeError, match="name"):
        Company(
            company_id=uuid4(),
            name=name,  # type: ignore[arg-type]
        )


@pytest.mark.parametrize(
    "name",
    [
        "",
        " ",
        "   ",
        "\t",
        "\n",
    ],
)
def test_company_rejects_blank_name(name: str) -> None:
    with pytest.raises(ValueError, match="name"):
        Company(
            company_id=uuid4(),
            name=name,
        )


@pytest.mark.parametrize(
    "name",
    [
        " Muster UG",
        "Muster UG ",
        " Muster UG ",
        "\tMuster UG",
        "Muster UG\n",
    ],
)
def test_company_rejects_surrounding_whitespace(name: str) -> None:
    with pytest.raises(ValueError, match="name"):
        Company(
            company_id=uuid4(),
            name=name,
        )


def test_company_is_immutable() -> None:
    company = Company(
        company_id=uuid4(),
        name="Muster UG",
    )

    with pytest.raises(FrozenInstanceError):
        company.name = "Andere UG"  # type: ignore[misc]


def test_companies_with_same_id_are_equal() -> None:
    company_id = uuid4()

    first = Company(
        company_id=company_id,
        name="Muster UG",
    )
    second = Company(
        company_id=company_id,
        name="Muster UG",
    )

    assert first == second


def test_company_name_does_not_affect_equality() -> None:
    company_id = uuid4()

    first = Company(
        company_id=company_id,
        name="Muster UG",
    )
    second = Company(
        company_id=company_id,
        name="Muster UG (haftungsbeschränkt)",
    )

    assert first == second


def test_companies_with_different_ids_are_not_equal() -> None:
    first = Company(
        company_id=uuid4(),
        name="Muster UG",
    )
    second = Company(
        company_id=uuid4(),
        name="Muster UG",
    )

    assert first != second


def test_company_is_not_equal_to_other_object_type() -> None:
    company = Company(
        company_id=uuid4(),
        name="Muster UG",
    )

    assert company != company.company_id
    assert company != "Muster UG"
    assert company != object()


def test_equal_companies_have_equal_hashes() -> None:
    company_id = uuid4()

    first = Company(
        company_id=company_id,
        name="Muster UG",
    )
    second = Company(
        company_id=company_id,
        name="Anderer Unternehmensname",
    )

    assert hash(first) == hash(second)


def test_company_is_hashable() -> None:
    company = Company(
        company_id=uuid4(),
        name="Muster UG",
    )

    companies = {company}

    assert company in companies


def test_company_can_be_created_with_known_uuid() -> None:
    company_id = UUID("550e8400-e29b-41d4-a716-446655440000")

    company = Company(
        company_id=company_id,
        name="Muster UG",
    )

    assert company.company_id == company_id

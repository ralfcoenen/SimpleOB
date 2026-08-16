"""Tests für die technische XBRL-Entitätskennung."""

from uuid import UUID

from openbilanz.domain.company import Company
from openbilanz.taxonomy.entity_identifier import (
    EntityIdentifier,
)


def test_creates_entity_identifier_from_company() -> None:
    company = Company(
        company_id=UUID(
            "12345678-1234-5678-1234-567812345678"
        ),
        name="Muster UG",
    )

    identifier = EntityIdentifier.from_company(
        company
    )

    assert (
        identifier.value
        == "12345678-1234-5678-1234-567812345678"
    )
    assert (
        identifier.scheme
        == "urn:openbilanz:company-id"
    )
    

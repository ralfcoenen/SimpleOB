"""Technische Identifikation der berichtenden XBRL-Entität."""

from dataclasses import dataclass

from simpleob.domain.company import Company

OPENBILANZ_ENTITY_SCHEME = (
    "urn:openbilanz:company-id"
)


@dataclass(frozen=True, slots=True)
class EntityIdentifier:
    """Identifiziert ein Unternehmen in XBRL-Kontexten."""

    value: str
    scheme: str = OPENBILANZ_ENTITY_SCHEME

    def __post_init__(self) -> None:
        if not isinstance(
            self.value,
            str,
        ):
            raise TypeError(
                "value must be a string"
            )

        if not self.value.strip():
            raise ValueError(
                "value must not be blank"
            )

        if not isinstance(
            self.scheme,
            str,
        ):
            raise TypeError(
                "scheme must be a string"
            )

        if not self.scheme.strip():
            raise ValueError(
                "scheme must not be blank"
            )

    @classmethod
    def from_company(
        cls,
        company: Company,
    ) -> "EntityIdentifier":
        """Erzeugt die Kennung aus der stabilen Unternehmens-ID."""

        if not isinstance(
            company,
            Company,
        ):
            raise TypeError(
                "company must be a Company"
            )

        return cls(
            value=str(company.company_id),
        )

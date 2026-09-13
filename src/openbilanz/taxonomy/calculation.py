"""Calculation-Beziehungen einer XBRL-Taxonomie."""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class TaxonomyCalculationRelation:
    """Summation-Item-Beziehung einer Calculation-Linkbase."""

    parent_concept_id: str
    child_concept_id: str
    order: Decimal
    weight: Decimal
    role_uri: str

    def __post_init__(self) -> None:
        if not isinstance(
            self.parent_concept_id,
            str,
        ):
            raise TypeError(
                "parent_concept_id must be a string"
            )

        if not self.parent_concept_id.strip():
            raise ValueError(
                "parent_concept_id must not be blank"
            )

        if not isinstance(
            self.child_concept_id,
            str,
        ):
            raise TypeError(
                "child_concept_id must be a string"
            )

        if not self.child_concept_id.strip():
            raise ValueError(
                "child_concept_id must not be blank"
            )

        if not isinstance(
            self.order,
            Decimal,
        ):
            raise TypeError(
                "order must be a Decimal"
            )

        if not isinstance(
            self.weight,
            Decimal,
        ):
            raise TypeError(
                "weight must be a Decimal"
            )

        if not isinstance(
            self.role_uri,
            str,
        ):
            raise TypeError(
                "role_uri must be a string"
            )

        if not self.role_uri.strip():
            raise ValueError(
                "role_uri must not be blank"
            )

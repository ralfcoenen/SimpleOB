"""Taxonomischer Fact."""

from dataclasses import dataclass
from decimal import Decimal

from simpleob.taxonomy.concept import TaxonomyConcept
from simpleob.taxonomy.context import TaxonomyContext
from simpleob.taxonomy.unit import TaxonomyUnit


@dataclass(frozen=True, slots=True)
class TaxonomyFact:
    """Verknüpft Concept, Wert, XBRL-Kontext und Einheit."""

    concept: TaxonomyConcept
    amount: Decimal
    context: TaxonomyContext
    unit: TaxonomyUnit
    decimals: int | str = 2

    def __post_init__(self) -> None:
        if not isinstance(
            self.concept,
            TaxonomyConcept,
        ):
            raise TypeError(
                "concept must be a TaxonomyConcept"
            )

        if not isinstance(
            self.amount,
            Decimal,
        ):
            raise TypeError(
                "amount must be a Decimal"
            )

        if not isinstance(
            self.context,
            TaxonomyContext,
        ):
            raise TypeError(
                "context must be a TaxonomyContext"
            )

        if not isinstance(
            self.unit,
            TaxonomyUnit,
        ):
            raise TypeError(
                "unit must be a TaxonomyUnit"
            )
            
        if not (
            isinstance(
                self.decimals,
                int,
            )
            or self.decimals == "INF"
        ):
            raise TypeError(
                'decimals must be an int or "INF"'
            )

        if not self.concept.is_numeric:
            raise ValueError(
                "concept is not numeric"
            )

        if (
            self.context.period_type
            is not self.concept.period_type
        ):
            raise ValueError(
                "context period type does not match concept"
            )

        if (
            self.concept.type_name == "xbrli:monetaryItemType"
            and not self.unit.measure.startswith("iso4217:")
        ):
            raise ValueError(
                "monetary concept requires ISO 4217 unit"
            )

        if (
            self.concept.type_name == "xbrli:pureItemType"
            and self.unit.measure != "xbrli:pure"
        ):
            raise ValueError(
                "pure concept requires xbrli:pure unit"
            )


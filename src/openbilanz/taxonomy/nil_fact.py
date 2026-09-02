"""Taxonomischer NIL-Fact."""

from dataclasses import dataclass

from openbilanz.taxonomy.concept import TaxonomyConcept
from openbilanz.taxonomy.context import TaxonomyContext
from openbilanz.taxonomy.unit import TaxonomyUnit


@dataclass(frozen=True, slots=True)
class TaxonomyNilFact:
    """Repräsentiert einen numerischen XBRL-Fact ohne ableitbaren Wert."""

    concept: TaxonomyConcept
    context: TaxonomyContext
    unit: TaxonomyUnit

    def __post_init__(self) -> None:
        if not isinstance(
            self.concept,
            TaxonomyConcept,
        ):
            raise TypeError(
                "concept must be a TaxonomyConcept"
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

        if not self.concept.is_numeric:
            raise ValueError(
                "concept is not numeric"
            )

        if not self.concept.nillable:
            raise ValueError(
                "concept is not nillable"
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

"""Nichtnumerischer taxonomischer Text-Fact."""

from dataclasses import dataclass

from simpleob.taxonomy.concept import TaxonomyConcept
from simpleob.taxonomy.context import TaxonomyContext


@dataclass(frozen=True, slots=True)
class TaxonomyTextFact:
    """Verknüpft ein Text-Concept mit Wert und XBRL-Kontext."""

    concept: TaxonomyConcept
    value: str
    context: TaxonomyContext


    def __post_init__(self) -> None:
        if not isinstance(
            self.concept,
            TaxonomyConcept,
        ):
            raise TypeError(
                "concept must be a TaxonomyConcept"
            )

        if not isinstance(
            self.value,
            str,
        ):
            raise TypeError(
                "value must be a string"
            )

        if not isinstance(
            self.context,
            TaxonomyContext,
        ):
            raise TypeError(
                "context must be a TaxonomyContext"
            )

        if self.concept.is_numeric:
            raise ValueError(
                "concept must not be numeric"
            )

        if (
            self.context.period_type
            is not self.concept.period_type
        ):
            raise ValueError(
                "context period type does not match concept"
            )
            
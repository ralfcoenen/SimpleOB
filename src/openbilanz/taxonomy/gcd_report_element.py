"""GCD-Berichtsbestandteile innerhalb des Report-Element-Tuples."""

from dataclasses import dataclass

from openbilanz.taxonomy.text_fact import TaxonomyTextFact


@dataclass(frozen=True, slots=True)
class GcdReportElement:
    """Enthält die GCD-Facts eines Report-Element-Tuples."""

    facts: tuple[TaxonomyTextFact, ...]

    def __post_init__(self) -> None:
        if not all(
            isinstance(
                fact,
                TaxonomyTextFact,
            )
            for fact in self.facts
        ):
            raise TypeError(
                "facts must contain only "
                "TaxonomyTextFact objects"
            )

        if not self.facts:
            return

        context = self.facts[0].context

        if not all(
            fact.context is context
            for fact in self.facts
        ):
            raise ValueError(
                "facts must use the same context"
            )

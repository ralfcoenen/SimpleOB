"""GCD-Tuple für Unternehmenskennungen."""

from dataclasses import dataclass

from simpleob.taxonomy.text_fact import TaxonomyTextFact


@dataclass(frozen=True, slots=True)
class GcdCompanyIdNo:
    """Enthält die Facts des GCD-idNo-Tuples."""

    facts: tuple[TaxonomyTextFact, ...]

    def __post_init__(self) -> None:
        if not isinstance(
            self.facts,
            tuple,
        ):
            raise TypeError(
                "facts must be a tuple"
            )

        if not self.facts:
            raise ValueError(
                "facts must not be empty"
            )

        for fact in self.facts:
            if not isinstance(
                fact,
                TaxonomyTextFact,
            ):
                raise TypeError(
                    "facts must contain only TaxonomyTextFact"
                )

        contexts = {
            fact.context
            for fact in self.facts
        }

        if len(contexts) != 1:
            raise ValueError(
                "facts must use the same context"
            )

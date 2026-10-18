"""Abfrage von Labels einer XBRL-Taxonomie."""

from dataclasses import dataclass

from simpleob.taxonomy.label import (
    TaxonomyLabel,
    TaxonomyLabelRole,
)


@dataclass(frozen=True, slots=True)
class TaxonomyLabelSet:
    """Enthält und filtert Labels einer Taxonomie."""

    labels: tuple[TaxonomyLabel, ...]

    def __post_init__(self) -> None:
        if not isinstance(
            self.labels,
            tuple,
        ):
            raise TypeError(
                "labels must be a tuple"
            )

        if not all(
            isinstance(
                label,
                TaxonomyLabel,
            )
            for label in self.labels
        ):
            raise TypeError(
                "labels must contain only "
                "TaxonomyLabel objects"
            )

    def for_concept(
        self,
        concept_id: str,
        *,
        language: str | None = None,
        role: TaxonomyLabelRole | None = None,
    ) -> tuple[TaxonomyLabel, ...]:
        """Liefert passende Labels eines Concepts."""

        return tuple(
            label
            for label in self.labels
            if label.concept_id == concept_id
            and (
                language is None
                or label.language == language
            )
            and (
                role is None
                or label.role is role
            )
        )
"""Vergleich von Taxonomieversionen."""

from dataclasses import dataclass

from simpleob.taxonomy.model import TaxonomyModel


@dataclass(frozen=True, slots=True)
class TaxonomyVersionComparison:
    """Beschreibt Concept-Änderungen zwischen zwei Taxonomiemodellen."""

    added_concept_names: tuple[str, ...]
    removed_concept_names: tuple[str, ...]
    unchanged_concept_names: tuple[str, ...]

    @property
    def added_count(self) -> int:
        """Anzahl neu hinzugekommener Concepts."""

        return len(
            self.added_concept_names
        )

    @property
    def removed_count(self) -> int:
        """Anzahl entfallener Concepts."""

        return len(
            self.removed_concept_names
        )

    @classmethod
    def compare(
        cls,
        *,
        old_model: TaxonomyModel,
        new_model: TaxonomyModel,
    ) -> "TaxonomyVersionComparison":
        """Vergleicht zwei Taxonomiemodelle anhand ihrer Concept-Namen."""

        if not isinstance(
            old_model,
            TaxonomyModel,
        ):
            raise TypeError(
                "old_model must be a TaxonomyModel"
            )

        if not isinstance(
            new_model,
            TaxonomyModel,
        ):
            raise TypeError(
                "new_model must be a TaxonomyModel"
            )

        old_names = {
            concept.name
            for concept in old_model.concepts.concepts
        }

        new_names = {
            concept.name
            for concept in new_model.concepts.concepts
        }

        return cls(
            added_concept_names=tuple(
                sorted(
                    new_names - old_names
                )
            ),
            removed_concept_names=tuple(
                sorted(
                    old_names - new_names
                )
            ),
            unchanged_concept_names=tuple(
                sorted(
                    old_names & new_names
                )
            ),
        )
        

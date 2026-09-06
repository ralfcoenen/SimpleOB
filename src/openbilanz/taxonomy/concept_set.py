"""Abfrage von Concepts einer XBRL-Taxonomie."""

from dataclasses import dataclass
from pathlib import Path

from openbilanz.taxonomy.concept import TaxonomyConcept


@dataclass(frozen=True, slots=True)
class TaxonomyConceptSet:
    """Enthält und durchsucht Concepts einer Taxonomie."""

    concepts: tuple[TaxonomyConcept, ...]

    def __post_init__(self) -> None:
        if not isinstance(
            self.concepts,
            tuple,
        ):
            raise TypeError(
                "concepts must be a tuple"
            )

        if not all(
            isinstance(
                concept,
                TaxonomyConcept,
            )
            for concept in self.concepts
        ):
            raise TypeError(
                "concepts must contain only "
                "TaxonomyConcept objects"
            )

        concept_ids = [
            concept.concept_id
            for concept in self.concepts
        ]

        if len(concept_ids) != len(set(concept_ids)):
            raise ValueError(
                "duplicate concept ids are not allowed"
            )

    def by_id(
        self,
        concept_id: str,
    ) -> TaxonomyConcept | None:
        """Liefert ein Concept anhand seiner XSD-ID."""

        for concept in self.concepts:
            if concept.concept_id == concept_id:
                return concept

        return None

    def by_name(
        self,
        concept_name: str,
    ) -> TaxonomyConcept | None:
        """Liefert ein eindeutig bestimmbares Concept anhand seines Namens."""

        if not isinstance(concept_name, str):
            raise TypeError(
                "concept_name must be a string"
            )

        if not concept_name.strip():
            raise ValueError(
                "concept_name must not be blank"
            )

        matches = tuple(
            concept
            for concept in self.concepts
            if concept.name == concept_name
        )

        if not matches:
            return None

        if len(matches) > 1:
            raise ValueError(
                f"concept name is ambiguous: {concept_name}"
            )

        return matches[0]

    @classmethod
    def from_schemas(
        cls,
        *,
        paths: tuple[Path, ...],
    ) -> "TaxonomyConceptSet":
        """Lädt Concepts aus mehreren XSD-Schemas."""

        if not isinstance(paths, tuple):
            raise TypeError(
                "paths must be a tuple"
            )

        concepts = tuple(
            concept
            for path in paths
            for concept in TaxonomyConcept.from_schema(
                path
            )
        )

        return cls(
            concepts=concepts
        )

"""Geladenes Modell einer XBRL-Taxonomie."""

from dataclasses import dataclass, field

from simpleob.taxonomy.concept import TaxonomyConcept
from simpleob.taxonomy.concept_set import TaxonomyConceptSet
from simpleob.taxonomy.calculation_set import (
    TaxonomyCalculationSet,
)
from simpleob.taxonomy.label import (
    TaxonomyLabel,
    TaxonomyLabelRole,
)
from simpleob.taxonomy.label_set import TaxonomyLabelSet
from simpleob.taxonomy.presentation_set import (
    TaxonomyPresentationSet,
)


@dataclass(frozen=True, slots=True)
class TaxonomyModel:
    """Verbindet Concepts, Labels, Presentation und Calculation."""

    concepts: TaxonomyConceptSet
    labels: TaxonomyLabelSet
    presentation: TaxonomyPresentationSet
    calculation: TaxonomyCalculationSet = field(
        default_factory=lambda: TaxonomyCalculationSet(
            relations=()
        )
    )

    def __post_init__(self) -> None:
        if not isinstance(
            self.concepts,
            TaxonomyConceptSet,
        ):
            raise TypeError(
                "concepts must be a TaxonomyConceptSet"
            )

        if not isinstance(
            self.labels,
            TaxonomyLabelSet,
        ):
            raise TypeError(
                "labels must be a TaxonomyLabelSet"
            )

        if not isinstance(
            self.presentation,
            TaxonomyPresentationSet,
        ):
            raise TypeError(
                "presentation must be a TaxonomyPresentationSet"
            )

        if not isinstance(
            self.calculation,
            TaxonomyCalculationSet,
        ):
            raise TypeError(
                "calculation must be a TaxonomyCalculationSet"
            )

        for label in self.labels.labels:
            if self.concepts.by_id(
                label.concept_id
            ) is None:
                raise ValueError(
                    "label references unknown concept"
                )

        for relation in self.presentation.relations:
            if self.concepts.by_id(
                relation.parent_concept_id
            ) is None:
                raise ValueError(
                    "presentation references unknown parent concept"
                )

            if self.concepts.by_id(
                relation.child_concept_id
            ) is None:
                raise ValueError(
                    "presentation references unknown child concept"
                )

        for relation in self.calculation.relations:
            if self.concepts.by_id(
                relation.parent_concept_id
            ) is None:
                raise ValueError(
                    "calculation references unknown parent concept"
                )

            if self.concepts.by_id(
                relation.child_concept_id
            ) is None:
                raise ValueError(
                    "calculation references unknown child concept"
                )

    def labels_for(
        self,
        concept_id: str,
    ) -> tuple[TaxonomyLabel, ...]:
        """Liefert alle Labels eines Concepts."""

        return self.labels.for_concept(
            concept_id
        )

    def children_for(
        self,
        concept_id: str,
        *,
        role_uri: str,
    ) -> tuple[TaxonomyConcept, ...]:
        """Liefert die Child-Concepts in Presentation-Reihenfolge."""

        relations = self.presentation.children_of(
            concept_id,
            role_uri=role_uri,
        )

        children: list[TaxonomyConcept] = []

        for relation in relations:
            concept = self.concepts.by_id(
                relation.child_concept_id
            )

            if concept is not None:
                children.append(concept)

        return tuple(children)

    def label_for(
        self,
        concept_id: str,
    ) -> str | None:
        """Liefert bevorzugt das deutsche Standardlabel eines Concepts."""

        labels = self.labels_for(
            concept_id
        )

        for label in labels:
            if (
                label.language == "de"
                and label.role is TaxonomyLabelRole.LABEL
            ):
                return label.text

        for label in labels:
            if label.language == "de":
                return label.text

        return None

"""Abfrage von Presentation-Beziehungen einer XBRL-Taxonomie."""

from dataclasses import dataclass

from openbilanz.taxonomy.presentation import (
    TaxonomyPresentationRelation,
)


@dataclass(frozen=True, slots=True)
class TaxonomyPresentationSet:
    """Enthält und filtert Presentation-Beziehungen."""

    relations: tuple[TaxonomyPresentationRelation, ...]

    def __post_init__(self) -> None:
        if not isinstance(
            self.relations,
            tuple,
        ):
            raise TypeError(
                "relations must be a tuple"
            )

        if not all(
            isinstance(
                relation,
                TaxonomyPresentationRelation,
            )
            for relation in self.relations
        ):
            raise TypeError(
                "relations must contain only "
                "TaxonomyPresentationRelation objects"
            )

    def relations_for_role(
        self,
        role_uri: str,
    ) -> tuple[TaxonomyPresentationRelation, ...]:
        """Liefert alle Presentation-Beziehungen einer Rolle."""

        return tuple(
            relation
            for relation in self.relations
            if relation.role_uri == role_uri
        )

    def children_of(
        self,
        parent_concept_id: str,
        *,
        role_uri: str,
    ) -> tuple[TaxonomyPresentationRelation, ...]:
        """Liefert die Kinder eines Concepts nach Presentation-Order."""

        relations = (
            relation
            for relation in self.relations
            if (
                relation.parent_concept_id == parent_concept_id
                and relation.role_uri == role_uri
            )
        )

        return tuple(
            sorted(
                relations,
                key=lambda relation: relation.order,
            )
        )
        
    def root_concepts_for_role(
        self,
        role_uri: str,
    ) -> tuple[str, ...]:
        """Liefert die Wurzel-Concepts einer Presentation-Rolle."""

        relations = self.relations_for_role(
            role_uri
        )

        parents = {
            relation.parent_concept_id
            for relation in relations
        }

        children = {
            relation.child_concept_id
            for relation in relations
        }

        roots = parents - children

        return tuple(
            sorted(roots)
        )

"""Abfrage von Calculation-Beziehungen einer XBRL-Taxonomie."""

from dataclasses import dataclass

from openbilanz.taxonomy.calculation import (
    TaxonomyCalculationRelation,
)


@dataclass(frozen=True, slots=True)
class TaxonomyCalculationSet:
    """Enthält und filtert Calculation-Beziehungen."""

    relations: tuple[TaxonomyCalculationRelation, ...]

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
                TaxonomyCalculationRelation,
            )
            for relation in self.relations
        ):
            raise TypeError(
                "relations must contain only "
                "TaxonomyCalculationRelation objects"
            )

    def relations_for_role(
        self,
        role_uri: str,
    ) -> tuple[TaxonomyCalculationRelation, ...]:
        """Liefert alle Calculation-Beziehungen einer Rolle."""

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
    ) -> tuple[TaxonomyCalculationRelation, ...]:
        """Liefert die rechnerischen Kinder eines Concepts."""

        relations = (
            relation
            for relation in self.relations
            if (
                relation.parent_concept_id
                == parent_concept_id
                and relation.role_uri == role_uri
            )
        )

        return tuple(
            sorted(
                relations,
                key=lambda relation: relation.order,
            )
        )

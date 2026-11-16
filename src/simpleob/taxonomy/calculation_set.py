"""Abfrage von Calculation-Beziehungen einer XBRL-Taxonomie."""

from dataclasses import dataclass

from simpleob.taxonomy.calculation import (
    TaxonomyCalculationRelation,
)
from simpleob.taxonomy.errors import (
    AmbiguousCalculationPathError,
    CalculationPathNotFoundError,
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

    def parents_of(
        self,
        child_concept_id: str,
        *,
        role_uri: str,
    ) -> tuple[TaxonomyCalculationRelation, ...]:
        """Liefert die rechnerischen Eltern eines Concepts."""

        relations = (
            relation
            for relation in self.relations
            if (
                relation.child_concept_id
                == child_concept_id
                and relation.role_uri == role_uri
            )
        )

        return tuple(
            sorted(
                relations,
                key=lambda relation: (
                    relation.parent_concept_id,
                    relation.order,
                ),
            )
        )

    def descendants_of(
        self,
        parent_concept_id: str,
    ) -> tuple[str, ...]:
        """Liefert alle Calculation-Nachfolger über alle Rollen hinweg.

        Die Traversierung bleibt jeweils innerhalb einer Calculation-Rolle;
        Beziehungen aus verschiedenen Rollen werden nicht zu einem
        künstlichen Pfad zusammengesetzt.
        """

        if not isinstance(parent_concept_id, str):
            raise TypeError("parent_concept_id must be a string")

        role_uris = sorted(
            {relation.role_uri for relation in self.relations}
        )
        descendants: set[str] = set()

        for role_uri in role_uris:
            pending = [parent_concept_id]
            visited = {parent_concept_id}

            while pending:
                current_id = pending.pop()

                for relation in self.children_of(
                    current_id,
                    role_uri=role_uri,
                ):
                    child_id = relation.child_concept_id

                    if child_id in visited:
                        continue

                    visited.add(child_id)
                    descendants.add(child_id)
                    pending.append(child_id)

        return tuple(sorted(descendants))

    def paths_between(
        self,
        parent_concept_id: str,
        descendant_concept_id: str,
    ) -> tuple[tuple[TaxonomyCalculationRelation, ...], ...]:
        """Liefert Calculation-Pfade zwischen zwei Concepts.

        Jeder Pfad verwendet genau eine Rolle. Der Aufrufer kann dadurch
        sowohl die Abstammung als auch die Calculation-Gewichte prüfen.
        """

        if not isinstance(parent_concept_id, str):
            raise TypeError("parent_concept_id must be a string")

        if not isinstance(descendant_concept_id, str):
            raise TypeError("descendant_concept_id must be a string")

        if parent_concept_id == descendant_concept_id:
            return ()

        role_uris = sorted(
            {relation.role_uri for relation in self.relations}
        )
        paths: list[tuple[TaxonomyCalculationRelation, ...]] = []

        for role_uri in role_uris:
            pending: list[
                tuple[
                    str,
                    tuple[TaxonomyCalculationRelation, ...],
                    frozenset[str],
                ]
            ] = [
                (
                    parent_concept_id,
                    (),
                    frozenset((parent_concept_id,)),
                )
            ]

            while pending:
                current_id, path, visited = pending.pop()

                for relation in self.children_of(
                    current_id,
                    role_uri=role_uri,
                ):
                    child_id = relation.child_concept_id

                    if child_id in visited:
                        continue

                    child_path = (*path, relation)

                    if child_id == descendant_concept_id:
                        paths.append(child_path)
                        continue

                    pending.append(
                        (
                            child_id,
                            child_path,
                            visited | {child_id},
                        )
                    )

        unique_paths = {
            tuple(
                (
                    relation.parent_concept_id,
                    relation.child_concept_id,
                    relation.weight,
                )
                for relation in path
            ): path
            for path in paths
        }

        return tuple(
            unique_paths[key]
            for key in sorted(unique_paths)
        )

    def unique_path_between(
        self,
        parent_concept_id: str,
        descendant_concept_id: str,
    ) -> tuple[TaxonomyCalculationRelation, ...]:
        """Liefert nur einen eindeutigen Calculation-Pfad.

        Die E-Bilanz-Auswahl und der Erzeugungspfad verwenden dieselbe
        Eindeutigkeitsregel: kein Pfad und mehrere Pfade sind ungültig.
        """

        paths = self.paths_between(
            parent_concept_id,
            descendant_concept_id,
        )

        if not paths:
            raise CalculationPathNotFoundError(
                "Zwischen der HGB-Position und dem Taxonomie-Concept besteht "
                "kein Calculation-Pfad."
            )

        if len(paths) != 1:
            raise AmbiguousCalculationPathError(
                "Zwischen der HGB-Position und dem Taxonomie-Concept bestehen "
                f"mehrere Calculation-Pfade ({len(paths)})."
            )

        return paths[0]

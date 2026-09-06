"""Versionierbare Profile für die E-Bilanz-Fact-Plan-Erzeugung."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from openbilanz.eric.bilanz_generation.fact_plan import (
    FactPlan,
    FactPlanNode,
)


class ProfileChangeType(Enum):
    """Art einer Änderung innerhalb eines Profil-Deltas."""

    ADD = "add"
    REPLACE = "replace"
    REMOVE = "remove"


@dataclass(frozen=True, slots=True)
class ProfileChange:
    """Eine Änderung gegenüber dem vorherigen E-Bilanz-Profil."""

    change_type: ProfileChangeType
    concept_name: str
    node: FactPlanNode | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.change_type, ProfileChangeType):
            raise TypeError(
                "change_type must be a ProfileChangeType"
            )

        if not isinstance(self.concept_name, str):
            raise TypeError("concept_name must be a string")

        if not self.concept_name.strip():
            raise ValueError("concept_name must not be blank")

        if self.change_type in (
            ProfileChangeType.ADD,
            ProfileChangeType.REPLACE,
        ):
            if not isinstance(self.node, FactPlanNode):
                raise TypeError(
                    "ADD and REPLACE changes require a FactPlanNode"
                )

            if self.node.concept_name != self.concept_name:
                raise ValueError(
                    "node concept_name must match change concept_name"
                )

        elif self.node is not None:
            raise ValueError(
                "REMOVE change must not contain a node"
            )


@dataclass(frozen=True, slots=True)
class BilanzProfile:
    """Effektives E-Bilanz-Profil einer Taxonomieversion."""

    taxonomy_version: str
    fact_plan: FactPlan

    def __post_init__(self) -> None:
        if not isinstance(self.taxonomy_version, str):
            raise TypeError("taxonomy_version must be a string")

        if not self.taxonomy_version.strip():
            raise ValueError(
                "taxonomy_version must not be blank"
            )

        if not isinstance(self.fact_plan, FactPlan):
            raise TypeError("fact_plan must be a FactPlan")


@dataclass(frozen=True, slots=True)
class BilanzProfileDelta:
    """Änderungen für eine konkrete Taxonomieversion."""

    taxonomy_version: str
    changes: tuple[ProfileChange, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.taxonomy_version, str):
            raise TypeError("taxonomy_version must be a string")

        if not self.taxonomy_version.strip():
            raise ValueError(
                "taxonomy_version must not be blank"
            )

        if not isinstance(self.changes, tuple):
            raise TypeError("changes must be a tuple")

        if not all(
            isinstance(change, ProfileChange)
            for change in self.changes
        ):
            raise TypeError(
                "changes must contain only ProfileChange objects"
            )

        concept_names = tuple(
            change.concept_name
            for change in self.changes
        )

        if len(concept_names) != len(set(concept_names)):
            raise ValueError(
                "delta concept names must be unique"
            )


class BilanzProfileResolver:
    """Erzeugt aus Basisprofil und Delta ein effektives Profil."""

    @classmethod
    def apply_delta(
        cls,
        *,
        base_plan: FactPlan,
        delta: BilanzProfileDelta,
    ) -> BilanzProfile:
        if not isinstance(base_plan, FactPlan):
            raise TypeError("base_plan must be a FactPlan")

        if not isinstance(delta, BilanzProfileDelta):
            raise TypeError(
                "delta must be a BilanzProfileDelta"
            )

        nodes = list(base_plan.nodes)

        for change in delta.changes:
            index = cls._top_level_index(
                nodes=nodes,
                concept_name=change.concept_name,
            )

            if change.change_type is ProfileChangeType.ADD:
                if index is not None:
                    raise ValueError(
                        "ADD change requires a new concept: "
                        f"{change.concept_name}"
                    )

                assert change.node is not None
                nodes.append(change.node)
                continue

            if change.change_type is ProfileChangeType.REPLACE:
                if index is None:
                    raise ValueError(
                        "REPLACE change requires an existing concept: "
                        f"{change.concept_name}"
                    )

                assert change.node is not None
                nodes[index] = change.node
                continue

            if index is None:
                raise ValueError(
                    "REMOVE change requires an existing concept: "
                    f"{change.concept_name}"
                )

            del nodes[index]

        return BilanzProfile(
            taxonomy_version=delta.taxonomy_version,
            fact_plan=FactPlan(nodes=tuple(nodes)),
        )

    @staticmethod
    def _top_level_index(
        *,
        nodes: list[FactPlanNode],
        concept_name: str,
    ) -> int | None:
        for index, node in enumerate(nodes):
            if node.concept_name == concept_name:
                return index

        return None

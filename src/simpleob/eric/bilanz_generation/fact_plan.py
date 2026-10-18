"""Taxonomieunabhängiger Plan für die E-Bilanz-Fact-Erzeugung."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class FactPlanState(Enum):
    """Fachlicher Zustand eines E-Bilanz-Concepts."""

    VALUE = "value"
    NIL = "nil"
    VALUE_OR_NIL = "value_or_nil"
    CONDITIONAL = "conditional"
    REQUIRED_NIL_TUPLE = "required_nil_tuple"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True, slots=True)
class FactPlanNode:
    """Ein Knoten innerhalb eines strukturierten E-Bilanz-Fact-Plans."""

    concept_name: str
    state: FactPlanState
    children: tuple["FactPlanNode", ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.concept_name, str):
            raise TypeError("concept_name must be a string")

        if not self.concept_name.strip():
            raise ValueError("concept_name must not be blank")

        if not isinstance(self.state, FactPlanState):
            raise TypeError("state must be a FactPlanState")

        if not isinstance(self.children, tuple):
            raise TypeError("children must be a tuple")

        if not all(
            isinstance(child, FactPlanNode)
            for child in self.children
        ):
            raise TypeError(
                "children must contain only FactPlanNode objects"
            )

        child_names = tuple(
            child.concept_name
            for child in self.children
        )

        if len(child_names) != len(set(child_names)):
            raise ValueError(
                "child concept names must be unique"
            )

        if (
            self.state is FactPlanState.REQUIRED_NIL_TUPLE
            and not self.children
        ):
            raise ValueError(
                "required NIL tuple must contain children"
            )


@dataclass(frozen=True, slots=True)
class FactPlan:
    """Strukturierter fachlicher Plan einer E-Bilanz."""

    nodes: tuple[FactPlanNode, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.nodes, tuple):
            raise TypeError("nodes must be a tuple")

        if not all(
            isinstance(node, FactPlanNode)
            for node in self.nodes
        ):
            raise TypeError(
                "nodes must contain only FactPlanNode objects"
            )

        concept_names = tuple(
            node.concept_name
            for node in self.nodes
        )

        if len(concept_names) != len(set(concept_names)):
            raise ValueError(
                "top-level concept names must be unique"
            )

    def node_for(
        self,
        concept_name: str,
    ) -> FactPlanNode | None:
        """Sucht einen eindeutig vorkommenden Knoten nach Concept-Namen."""

        self._validate_concept_name(concept_name)

        matches: list[FactPlanNode] = []

        for node in self.nodes:
            self._collect_nodes(
                node=node,
                concept_name=concept_name,
                matches=matches,
            )

        if not matches:
            return None

        if len(matches) > 1:
            raise ValueError(
                f"concept name is ambiguous: {concept_name}"
            )

        return matches[0]

    def node_for_path(
        self,
        *concept_names: str,
    ) -> FactPlanNode | None:
        """Sucht einen Knoten anhand seines strukturellen FactPlan-Pfads."""

        if not concept_names:
            raise ValueError(
                "concept path must not be empty"
            )

        for concept_name in concept_names:
            self._validate_concept_name(concept_name)

        current_nodes = self.nodes
        current_node: FactPlanNode | None = None

        for concept_name in concept_names:
            current_node = next(
                (
                    node
                    for node in current_nodes
                    if node.concept_name == concept_name
                ),
                None,
            )

            if current_node is None:
                return None

            current_nodes = current_node.children

        return current_node

    def path_for(
        self,
        concept_name: str,
    ) -> tuple[str, ...] | None:
        """Liefert den eindeutigen strukturellen Pfad eines Concepts."""

        self._validate_concept_name(concept_name)

        matches: list[tuple[str, ...]] = []

        def collect(
            *,
            node: FactPlanNode,
            path: tuple[str, ...],
        ) -> None:
            current_path = (
                *path,
                node.concept_name,
            )

            if node.concept_name == concept_name:
                matches.append(current_path)

            for child in node.children:
                collect(
                    node=child,
                    path=current_path,
                )

        for node in self.nodes:
            collect(
                node=node,
                path=(),
            )

        if not matches:
            return None

        if len(matches) > 1:
            raise ValueError(
                f"concept name is ambiguous: {concept_name}"
            )

        return matches[0]

    def with_state(
        self,
        *,
        concept_name: str,
        state: FactPlanState,
    ) -> "FactPlan":
        """Ersetzt den Zustand eines eindeutig vorkommenden Knotens."""

        self._validate_concept_name(concept_name)

        if not isinstance(state, FactPlanState):
            raise TypeError("state must be a FactPlanState")

        if self.node_for(concept_name) is None:
            raise ValueError(
                "concept not found in fact plan: "
                f"{concept_name}"
            )

        def replace_state(
            node: FactPlanNode,
        ) -> FactPlanNode:
            children = tuple(
                replace_state(child)
                for child in node.children
            )

            if node.concept_name == concept_name:
                return FactPlanNode(
                    concept_name=node.concept_name,
                    state=state,
                    children=children,
                )

            if children == node.children:
                return node

            return FactPlanNode(
                concept_name=node.concept_name,
                state=node.state,
                children=children,
            )

        return FactPlan(
            nodes=tuple(
                replace_state(node)
                for node in self.nodes
            )
        )

    def with_conditional_child(
        self,
        *,
        parent_concept_name: str,
        child_concept_name: str,
    ) -> "FactPlan":
        """Ergänzt genau einen CONDITIONAL-Child unter einem vorhandenen Knoten."""

        self._validate_concept_name(
            parent_concept_name
        )
        self._validate_concept_name(
            child_concept_name
        )

        if self.node_for(
            child_concept_name
        ) is not None:
            raise ValueError(
                "child concept already exists in fact plan: "
                f"{child_concept_name}"
            )

        parent_matches: list[
            FactPlanNode
        ] = []

        for node in self.nodes:
            self._collect_nodes(
                node=node,
                concept_name=parent_concept_name,
                matches=parent_matches,
            )

        if not parent_matches:
            raise ValueError(
                "parent concept not found in fact plan: "
                f"{parent_concept_name}"
            )

        if len(parent_matches) > 1:
            raise ValueError(
                "parent concept is ambiguous in fact plan: "
                f"{parent_concept_name}"
            )

        child = FactPlanNode(
            concept_name=child_concept_name,
            state=FactPlanState.CONDITIONAL,
        )

        def replace_node(
            node: FactPlanNode,
        ) -> FactPlanNode:
            if node.concept_name == parent_concept_name:
                return FactPlanNode(
                    concept_name=node.concept_name,
                    state=node.state,
                    children=(
                        *node.children,
                        child,
                    ),
                )

            return FactPlanNode(
                concept_name=node.concept_name,
                state=node.state,
                children=tuple(
                    replace_node(
                        existing_child
                    )
                    for existing_child in node.children
                ),
            )

        return FactPlan(
            nodes=tuple(
                replace_node(node)
                for node in self.nodes
            )
        )

    @classmethod
    def _collect_nodes(
        cls,
        *,
        node: FactPlanNode,
        concept_name: str,
        matches: list[FactPlanNode],
    ) -> None:
        if node.concept_name == concept_name:
            matches.append(node)

        for child in node.children:
            cls._collect_nodes(
                node=child,
                concept_name=concept_name,
                matches=matches,
            )

    @staticmethod
    def _validate_concept_name(
        concept_name: str,
    ) -> None:
        if not isinstance(concept_name, str):
            raise TypeError(
                "concept_name must be a string"
            )

        if not concept_name.strip():
            raise ValueError(
                "concept_name must not be blank"
            )

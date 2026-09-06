"""Auflösung eines E-Bilanz-Fact-Plans in konkrete Taxonomie-Facts."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal

from openbilanz.eric.bilanz_generation.fact_plan import (
    FactPlan,
    FactPlanNode,
    FactPlanState,
)
from openbilanz.taxonomy.concept import (
    TaxonomyConcept,
    TaxonomyPeriodType,
)
from openbilanz.taxonomy.concept_set import TaxonomyConceptSet
from openbilanz.taxonomy.context import TaxonomyContext
from openbilanz.taxonomy.fact import TaxonomyFact
from openbilanz.taxonomy.nil_fact import TaxonomyNilFact
from openbilanz.taxonomy.text_fact import TaxonomyTextFact
from openbilanz.taxonomy.unit import TaxonomyUnit

FactPlanPath = tuple[str, ...]
FactPlanValue = str | Decimal
ResolvedTaxonomyFact = (
    TaxonomyFact
    | TaxonomyTextFact
    | TaxonomyNilFact
)


@dataclass(frozen=True, slots=True)
class ResolvedFactPlanNode:
    """Ein fachlich aufgelöster Knoten des E-Bilanz-Fact-Plans."""

    plan_node: FactPlanNode
    concept: TaxonomyConcept
    fact: ResolvedTaxonomyFact | None
    children: tuple["ResolvedFactPlanNode", ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(
            self.plan_node,
            FactPlanNode,
        ):
            raise TypeError(
                "plan_node must be a FactPlanNode"
            )

        if not isinstance(
            self.concept,
            TaxonomyConcept,
        ):
            raise TypeError(
                "concept must be a TaxonomyConcept"
            )

        if (
            self.fact is not None
            and not isinstance(
                self.fact,
                (
                    TaxonomyFact,
                    TaxonomyTextFact,
                    TaxonomyNilFact,
                ),
            )
        ):
            raise TypeError(
                "fact must be a supported taxonomy fact or None"
            )

        if not isinstance(
            self.children,
            tuple,
        ):
            raise TypeError(
                "children must be a tuple"
            )

        if not all(
            isinstance(
                child,
                ResolvedFactPlanNode,
            )
            for child in self.children
        ):
            raise TypeError(
                "children must contain only "
                "ResolvedFactPlanNode objects"
            )


@dataclass(frozen=True, slots=True)
class ResolvedFactPlan:
    """Strukturierter, mit konkreten Facts aufgelöster FactPlan."""

    nodes: tuple[ResolvedFactPlanNode, ...]

    def __post_init__(self) -> None:
        if not isinstance(
            self.nodes,
            tuple,
        ):
            raise TypeError(
                "nodes must be a tuple"
            )

        if not all(
            isinstance(
                node,
                ResolvedFactPlanNode,
            )
            for node in self.nodes
        ):
            raise TypeError(
                "nodes must contain only "
                "ResolvedFactPlanNode objects"
            )


class FactPlanResolver:
    """Löst einen FactPlan anhand konkreter Eingabewerte auf."""

    @classmethod
    def resolve(
        cls,
        *,
        fact_plan: FactPlan,
        concepts: TaxonomyConceptSet,
        contexts: Mapping[
            TaxonomyPeriodType,
            TaxonomyContext,
        ],
        values: Mapping[
            FactPlanPath,
            FactPlanValue,
        ],
    ) -> ResolvedFactPlan:
        """Erzeugt einen strukturierten Plan mit konkreten Taxonomie-Facts."""

        if not isinstance(
            fact_plan,
            FactPlan,
        ):
            raise TypeError(
                "fact_plan must be a FactPlan"
            )

        if not isinstance(
            concepts,
            TaxonomyConceptSet,
        ):
            raise TypeError(
                "concepts must be a TaxonomyConceptSet"
            )

        cls._validate_contexts(
            contexts
        )
        cls._validate_values(
            values
        )

        consumed_paths: set[FactPlanPath] = set()
        resolved_nodes: list[ResolvedFactPlanNode] = []

        for node in fact_plan.nodes:
            resolved = cls._resolve_node(
                node=node,
                path=(node.concept_name,),
                concepts=concepts,
                contexts=contexts,
                values=values,
                consumed_paths=consumed_paths,
            )

            if resolved is not None:
                resolved_nodes.append(
                    resolved
                )

        unused_paths = set(values) - consumed_paths

        if unused_paths:
            unused_path = sorted(
                unused_paths
            )[0]

            raise ValueError(
                "value path is not part of the resolved fact plan: "
                f"{cls._format_path(unused_path)}"
            )

        return ResolvedFactPlan(
            nodes=tuple(
                resolved_nodes
            )
        )

    @classmethod
    def _resolve_node(
        cls,
        *,
        node: FactPlanNode,
        path: FactPlanPath,
        concepts: TaxonomyConceptSet,
        contexts: Mapping[
            TaxonomyPeriodType,
            TaxonomyContext,
        ],
        values: Mapping[
            FactPlanPath,
            FactPlanValue,
        ],
        consumed_paths: set[FactPlanPath],
    ) -> ResolvedFactPlanNode | None:
        state = node.state

        if state is FactPlanState.UNSUPPORTED:
            if cls._has_value_in_subtree(
                path=path,
                values=values,
            ):
                raise ValueError(
                    "unsupported fact plan node received data: "
                    f"{cls._format_path(path)}"
                )

            return None

        if (
            state is FactPlanState.CONDITIONAL
            and not cls._has_value_in_subtree(
                path=path,
                values=values,
            )
        ):
            return None

        concept = concepts.by_name(
            node.concept_name
        )

        if concept is None:
            raise ValueError(
                "taxonomy concept not found: "
                f"{node.concept_name}"
            )

        if state is FactPlanState.REQUIRED_NIL_TUPLE:
            if path in values:
                raise ValueError(
                    "required NIL tuple must not receive a value: "
                    f"{cls._format_path(path)}"
                )

            children = cls._resolve_children(
                node=node,
                path=path,
                concepts=concepts,
                contexts=contexts,
                values=values,
                consumed_paths=consumed_paths,
            )

            return ResolvedFactPlanNode(
                plan_node=node,
                concept=concept,
                fact=None,
                children=children,
            )

        if state is FactPlanState.NIL:
            if path in values:
                raise ValueError(
                    "NIL fact must not receive a value: "
                    f"{cls._format_path(path)}"
                )

            fact = cls._build_nil_fact(
                concept=concept,
                contexts=contexts,
            )

            return ResolvedFactPlanNode(
                plan_node=node,
                concept=concept,
                fact=fact,
            )

        if state is FactPlanState.VALUE:
            if path not in values:
                raise ValueError(
                    "required fact value is missing: "
                    f"{cls._format_path(path)}"
                )

            value = values[path]
            consumed_paths.add(
                path
            )

            fact = cls._build_value_fact(
                concept=concept,
                value=value,
                contexts=contexts,
            )

            children = cls._resolve_children(
                node=node,
                path=path,
                concepts=concepts,
                contexts=contexts,
                values=values,
                consumed_paths=consumed_paths,
            )

            return ResolvedFactPlanNode(
                plan_node=node,
                concept=concept,
                fact=fact,
                children=children,
            )

        if state is FactPlanState.VALUE_OR_NIL:
            if path in values:
                value = values[path]
                consumed_paths.add(
                    path
                )

                fact = cls._build_value_fact(
                    concept=concept,
                    value=value,
                    contexts=contexts,
                )
            else:
                fact = cls._build_nil_fact(
                    concept=concept,
                    contexts=contexts,
                )

            children = cls._resolve_children(
                node=node,
                path=path,
                concepts=concepts,
                contexts=contexts,
                values=values,
                consumed_paths=consumed_paths,
            )

            return ResolvedFactPlanNode(
                plan_node=node,
                concept=concept,
                fact=fact,
                children=children,
            )

        if state is FactPlanState.CONDITIONAL:
            fact: ResolvedTaxonomyFact | None = None

            if path in values:
                value = values[path]
                consumed_paths.add(
                    path
                )

                fact = cls._build_value_fact(
                    concept=concept,
                    value=value,
                    contexts=contexts,
                )

            children = cls._resolve_children(
                node=node,
                path=path,
                concepts=concepts,
                contexts=contexts,
                values=values,
                consumed_paths=consumed_paths,
            )

            return ResolvedFactPlanNode(
                plan_node=node,
                concept=concept,
                fact=fact,
                children=children,
            )

        raise ValueError(
            f"unsupported fact plan state: {state}"
        )

    @classmethod
    def _resolve_children(
        cls,
        *,
        node: FactPlanNode,
        path: FactPlanPath,
        concepts: TaxonomyConceptSet,
        contexts: Mapping[
            TaxonomyPeriodType,
            TaxonomyContext,
        ],
        values: Mapping[
            FactPlanPath,
            FactPlanValue,
        ],
        consumed_paths: set[FactPlanPath],
    ) -> tuple[ResolvedFactPlanNode, ...]:
        resolved_children: list[
            ResolvedFactPlanNode
        ] = []

        for child in node.children:
            child_path = (
                *path,
                child.concept_name,
            )

            resolved = cls._resolve_node(
                node=child,
                path=child_path,
                concepts=concepts,
                contexts=contexts,
                values=values,
                consumed_paths=consumed_paths,
            )

            if resolved is not None:
                resolved_children.append(
                    resolved
                )

        return tuple(
            resolved_children
        )

    @classmethod
    def _build_value_fact(
        cls,
        *,
        concept: TaxonomyConcept,
        value: FactPlanValue,
        contexts: Mapping[
            TaxonomyPeriodType,
            TaxonomyContext,
        ],
    ) -> TaxonomyFact | TaxonomyTextFact:
        context = cls._context_for(
            concept=concept,
            contexts=contexts,
        )

        if concept.is_numeric:
            if not isinstance(
                value,
                Decimal,
            ):
                raise TypeError(
                    "numeric fact value must be a Decimal: "
                    f"{concept.name}"
                )

            return TaxonomyFact(
                concept=concept,
                amount=value,
                context=context,
                unit=cls._unit_for(
                    concept
                ),
                decimals=cls._decimals_for(
                    concept
                ),
            )

        if not isinstance(
            value,
            str,
        ):
            raise TypeError(
                "non-numeric fact value must be a string: "
                f"{concept.name}"
            )

        return TaxonomyTextFact(
            concept=concept,
            value=value,
            context=context,
        )

    @classmethod
    def _build_nil_fact(
        cls,
        *,
        concept: TaxonomyConcept,
        contexts: Mapping[
            TaxonomyPeriodType,
            TaxonomyContext,
        ],
    ) -> TaxonomyNilFact:
        context = cls._context_for(
            concept=concept,
            contexts=contexts,
        )

        unit = (
            cls._unit_for(
                concept
            )
            if concept.is_numeric
            else None
        )

        return TaxonomyNilFact(
            concept=concept,
            context=context,
            unit=unit,
        )

    @staticmethod
    def _unit_for(
        concept: TaxonomyConcept,
    ) -> TaxonomyUnit:
        if concept.type_name == "xbrli:monetaryItemType":
            return TaxonomyUnit.eur()

        if concept.type_name in (
            "xbrli:decimalItemType",
            "xbrli:pureItemType",
            "xbrli:longItemType",
            "xbrli:positiveIntegerItemType",
        ):
            return TaxonomyUnit.pure()

        raise ValueError(
            "unsupported numeric taxonomy concept type: "
            f"{concept.type_name}"
        )

    @staticmethod
    def _decimals_for(
        concept: TaxonomyConcept,
    ) -> int | str:
        if concept.type_name == "xbrli:monetaryItemType":
            return 2

        return "INF"

    @staticmethod
    def _context_for(
        *,
        concept: TaxonomyConcept,
        contexts: Mapping[
            TaxonomyPeriodType,
            TaxonomyContext,
        ],
    ) -> TaxonomyContext:
        context = contexts.get(
            concept.period_type
        )

        if context is None:
            raise ValueError(
                "taxonomy context not found for period type: "
                f"{concept.period_type.value}"
            )

        return context

    @staticmethod
    def _has_value_in_subtree(
        *,
        path: FactPlanPath,
        values: Mapping[
            FactPlanPath,
            FactPlanValue,
        ],
    ) -> bool:
        path_length = len(
            path
        )

        return any(
            candidate_path[:path_length] == path
            for candidate_path in values
        )

    @staticmethod
    def _validate_contexts(
        contexts: Mapping[
            TaxonomyPeriodType,
            TaxonomyContext,
        ],
    ) -> None:
        if not isinstance(
            contexts,
            Mapping,
        ):
            raise TypeError(
                "contexts must be a mapping"
            )

        for period_type, context in contexts.items():
            if not isinstance(
                period_type,
                TaxonomyPeriodType,
            ):
                raise TypeError(
                    "context keys must be TaxonomyPeriodType values"
                )

            if not isinstance(
                context,
                TaxonomyContext,
            ):
                raise TypeError(
                    "context values must be TaxonomyContext objects"
                )

            if context.period_type is not period_type:
                raise ValueError(
                    "context period type must match its mapping key"
                )

    @staticmethod
    def _validate_values(
        values: Mapping[
            FactPlanPath,
            FactPlanValue,
        ],
    ) -> None:
        if not isinstance(
            values,
            Mapping,
        ):
            raise TypeError(
                "values must be a mapping"
            )

        for path, value in values.items():
            if not isinstance(
                path,
                tuple,
            ):
                raise TypeError(
                    "fact plan value paths must be tuples"
                )

            if not path:
                raise ValueError(
                    "fact plan value path must not be empty"
                )

            if not all(
                isinstance(
                    part,
                    str,
                )
                and part.strip()
                for part in path
            ):
                raise ValueError(
                    "fact plan value path parts "
                    "must be non-blank strings"
                )

            if not isinstance(
                value,
                (
                    str,
                    Decimal,
                ),
            ):
                raise TypeError(
                    "fact plan values must be strings or Decimals"
                )

    @staticmethod
    def _format_path(
        path: FactPlanPath,
    ) -> str:
        return " -> ".join(
            path
        )

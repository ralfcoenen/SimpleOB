"""Serialisierung eines aufgelösten E-Bilanz-Fact-Plans als XBRL."""

from __future__ import annotations

from xml.etree import ElementTree as ET

from simpleob.eric.bilanz_generation.fact_plan_resolver import (
    ResolvedFactPlan,
    ResolvedFactPlanNode,
    ResolvedTaxonomyFact,
)
from simpleob.taxonomy.context import TaxonomyContext
from simpleob.taxonomy.fact import TaxonomyFact
from simpleob.taxonomy.nil_fact import TaxonomyNilFact
from simpleob.taxonomy.text_fact import TaxonomyTextFact
from simpleob.taxonomy.unit import TaxonomyUnit
from simpleob.taxonomy.xbrl_writer import TaxonomyXbrlWriter


class ResolvedFactPlanXbrlSerializer:
    """Serialisiert einen ResolvedFactPlan mit dem bestehenden XBRL-Writer."""

    def __init__(
        self,
        *,
        writer: TaxonomyXbrlWriter | None = None,
    ) -> None:
        if (
            writer is not None
            and not isinstance(
                writer,
                TaxonomyXbrlWriter,
            )
        ):
            raise TypeError(
                "writer must be a TaxonomyXbrlWriter or None"
            )

        self._writer = (
            writer
            if writer is not None
            else TaxonomyXbrlWriter()
        )

    def serialize(
        self,
        *,
        resolved_fact_plan: ResolvedFactPlan,
        contexts: dict[str, TaxonomyContext],
        units: dict[str, TaxonomyUnit],
        taxonomy_namespace: str,
        taxonomy_namespaces: dict[str, str] | None = None,
    ) -> tuple[ET.Element, ...]:
        """Serialisiert alle Top-Level-Knoten des aufgelösten Fact-Plans."""

        if not isinstance(
            resolved_fact_plan,
            ResolvedFactPlan,
        ):
            raise TypeError(
                "resolved_fact_plan must be a ResolvedFactPlan"
            )

        elements: list[ET.Element] = []

        for node in resolved_fact_plan.nodes:
            elements.extend(
                self._node_elements(
                    node=node,
                    contexts=contexts,
                    units=units,
                    taxonomy_namespace=taxonomy_namespace,
                    taxonomy_namespaces=taxonomy_namespaces,
                )
            )

        return tuple(elements)

    def _node_elements(
        self,
        *,
        node: ResolvedFactPlanNode,
        contexts: dict[str, TaxonomyContext],
        units: dict[str, TaxonomyUnit],
        taxonomy_namespace: str,
        taxonomy_namespaces: dict[str, str] | None,
    ) -> tuple[ET.Element, ...]:
        if node.fact is not None:
            elements = [
                self._fact_element(
                    fact=node.fact,
                    contexts=contexts,
                    units=units,
                    taxonomy_namespace=taxonomy_namespace,
                    taxonomy_namespaces=taxonomy_namespaces,
                )
            ]

            for child in node.children:
                elements.extend(
                    self._node_elements(
                        node=child,
                        contexts=contexts,
                        units=units,
                        taxonomy_namespace=taxonomy_namespace,
                        taxonomy_namespaces=taxonomy_namespaces,
                    )
                )

            return tuple(elements)

        if not node.children:
            raise ValueError(
                "structural resolved node must contain children: "
                f"{node.concept.name}"
            )

        namespace = self._writer.namespace_for(
            concept_id=node.concept.concept_id,
            taxonomy_namespace=taxonomy_namespace,
            taxonomy_namespaces=taxonomy_namespaces,
        )

        element = ET.Element(
            f"{{{namespace}}}{node.concept.name}"
        )

        for child in node.children:
            child_elements = self._node_elements(
                node=child,
                contexts=contexts,
                units=units,
                taxonomy_namespace=taxonomy_namespace,
                taxonomy_namespaces=taxonomy_namespaces,
            )

            for child_element in child_elements:
                element.append(
                    child_element
                )

        return (element,)

    def _fact_element(
        self,
        *,
        fact: ResolvedTaxonomyFact,
        contexts: dict[str, TaxonomyContext],
        units: dict[str, TaxonomyUnit],
        taxonomy_namespace: str,
        taxonomy_namespaces: dict[str, str] | None,
    ) -> ET.Element:
        context_id = self._writer.context_id_for(
            context=fact.context,
            contexts=contexts,
        )

        namespace = self._writer.namespace_for(
            concept_id=fact.concept.concept_id,
            taxonomy_namespace=taxonomy_namespace,
            taxonomy_namespaces=taxonomy_namespaces,
        )

        if isinstance(
            fact,
            TaxonomyTextFact,
        ):
            return self._writer.text_fact_element(
                fact=fact,
                context_id=context_id,
                namespace=namespace,
            )

        if isinstance(
            fact,
            TaxonomyFact,
        ):
            unit_id = self._writer.unit_id_for(
                unit=fact.unit,
                units=units,
            )

            return self._writer.fact_element(
                fact=fact,
                context_id=context_id,
                unit_id=unit_id,
                namespace=namespace,
            )

        if isinstance(
            fact,
            TaxonomyNilFact,
        ):
            unit_id = (
                self._writer.unit_id_for(
                    unit=fact.unit,
                    units=units,
                )
                if fact.unit is not None
                else None
            )

            return self._writer.nil_fact_element(
                fact=fact,
                context_id=context_id,
                unit_id=unit_id,
                namespace=namespace,
            )

        raise TypeError(
            "unsupported resolved taxonomy fact"
        )

"""Erzeugung einer vollständigen XBRL-Instanz für Taxonomie 6.9."""

from __future__ import annotations

from xml.etree import ElementTree as ET

from openbilanz.eric.bilanz_generation.fact_plan_resolver import (
    ResolvedFactPlan,
)
from openbilanz.eric.bilanz_generation.resolved_fact_plan_xbrl_serializer import (
    ResolvedFactPlanXbrlSerializer,
)
from openbilanz.taxonomy.context import TaxonomyContext
from openbilanz.taxonomy.entry_point import TaxonomyEntryPoint
from openbilanz.taxonomy.unit import TaxonomyUnit
from openbilanz.taxonomy.xbrl_writer import TaxonomyXbrlWriter

GCD_69_NAMESPACE = (
    "http://www.xbrl.de/taxonomies/"
    "de-gcd-2025-04-01"
)

GAAP_CI_69_NAMESPACE = (
    "http://www.xbrl.de/taxonomies/"
    "de-gaap-ci-2025-04-01"
)


class Taxonomy69XbrlDocumentBuilder:
    """Erzeugt die vollständige XBRL-Instanz des neuen 6.9-Pfads."""

    def __init__(
        self,
        *,
        writer: TaxonomyXbrlWriter | None = None,
        serializer: ResolvedFactPlanXbrlSerializer | None = None,
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

        if (
            serializer is not None
            and not isinstance(
                serializer,
                ResolvedFactPlanXbrlSerializer,
            )
        ):
            raise TypeError(
                "serializer must be a "
                "ResolvedFactPlanXbrlSerializer or None"
            )

        self._writer = (
            writer
            if writer is not None
            else TaxonomyXbrlWriter()
        )

        self._serializer = (
            serializer
            if serializer is not None
            else ResolvedFactPlanXbrlSerializer(
                writer=self._writer
            )
        )

    def build_element(
        self,
        *,
        resolved_fact_plan: ResolvedFactPlan,
        contexts: dict[str, TaxonomyContext],
        units: dict[str, TaxonomyUnit],
        entry_points: tuple[
            TaxonomyEntryPoint,
            ...,
        ],
    ) -> ET.Element:
        """Erzeugt das Root-Element der vollständigen 6.9-XBRL-Instanz."""

        if not isinstance(
            resolved_fact_plan,
            ResolvedFactPlan,
        ):
            raise TypeError(
                "resolved_fact_plan must be a ResolvedFactPlan"
            )

        root = self._writer.instance_element(
            contexts=contexts,
            units=units,
            facts=(),
            taxonomy_namespace=GAAP_CI_69_NAMESPACE,
            entry_points=entry_points,
            taxonomy_namespaces={
                "de-gcd": GCD_69_NAMESPACE,
                "de-gaap-ci": GAAP_CI_69_NAMESPACE,
            },
        )

        elements = self._serializer.serialize(
            resolved_fact_plan=resolved_fact_plan,
            contexts=contexts,
            units=units,
            taxonomy_namespace=GAAP_CI_69_NAMESPACE,
            taxonomy_namespaces={
                "de-gcd": GCD_69_NAMESPACE,
                "de-gaap-ci": GAAP_CI_69_NAMESPACE,
            },
        )

        for element in elements:
            root.append(
                element
            )

        return root

    def build_xml(
        self,
        *,
        resolved_fact_plan: ResolvedFactPlan,
        contexts: dict[str, TaxonomyContext],
        units: dict[str, TaxonomyUnit],
        entry_points: tuple[
            TaxonomyEntryPoint,
            ...,
        ],
    ) -> str:
        """Erzeugt die vollständige 6.9-XBRL-Instanz als XML-String."""

        root = self.build_element(
            resolved_fact_plan=resolved_fact_plan,
            contexts=contexts,
            units=units,
            entry_points=entry_points,
        )

        return self._writer.to_xml_string(
            root
        )

"""Erzeugung einer vollständigen XBRL-Instanz für Taxonomie 6.9."""

from __future__ import annotations

from xml.etree import ElementTree as ET

from openbilanz.eric.bilanz_generation.fact_plan_resolver import (
    ResolvedFactPlan,
)
from openbilanz.eric.bilanz_generation.resolved_fact_plan_xbrl_serializer import (
    ResolvedFactPlanXbrlSerializer,
)
from openbilanz.eric.bilanz_generation.tax_reconciliation import (
    TaxReconciliationTransfer,
)
from openbilanz.eric.bilanz_generation.taxonomy_6_9_tax_reconciliation_serializer import (
    Taxonomy69TaxReconciliationSerializer,
)
from openbilanz.taxonomy.account_balance_tuple import (
    TaxonomyAccountBalance,
)
from openbilanz.taxonomy.context import TaxonomyContext
from openbilanz.taxonomy.entry_point import TaxonomyEntryPoint
from openbilanz.taxonomy.fact import TaxonomyFact
from openbilanz.taxonomy.gcd_shareholder_tuple import (
    GcdShareholderTuple,
)
from openbilanz.taxonomy.nil_fact import TaxonomyNilFact
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
        shareholders: tuple[
            GcdShareholderTuple,
            ...,
        ] = (),
        nil_facts: tuple[
            TaxonomyNilFact,
            ...,
        ] = (),
        account_balances: tuple[
            TaxonomyAccountBalance,
            ...,
        ] = (),
        facts: tuple[TaxonomyFact, ...] = (),
        tax_reconciliation: (
            TaxReconciliationTransfer | None
        ) = None,
        tax_reconciliation_context_id: str | None = None,
        tax_reconciliation_unit_id: str | None = None,
    ) -> ET.Element:
        """Erzeugt das Root-Element der vollständigen 6.9-XBRL-Instanz."""

        if not isinstance(
            resolved_fact_plan,
            ResolvedFactPlan,
        ):
            raise TypeError(
                "resolved_fact_plan must be a ResolvedFactPlan"
            )

        self._validate_tax_reconciliation_arguments(
            tax_reconciliation=tax_reconciliation,
            context_id=tax_reconciliation_context_id,
            unit_id=tax_reconciliation_unit_id,
        )

        root = self._writer.instance_element(
            contexts=contexts,
            units=units,
            facts=facts,
            taxonomy_namespace=GAAP_CI_69_NAMESPACE,
            entry_points=entry_points,
            taxonomy_namespaces={
                "de-gcd": GCD_69_NAMESPACE,
                "de-gaap-ci": GAAP_CI_69_NAMESPACE,
            },
            shareholders=shareholders,
            nil_facts=nil_facts,
            account_balances=account_balances,
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

        if tax_reconciliation is not None:
            assert tax_reconciliation_context_id is not None
            assert tax_reconciliation_unit_id is not None

            root.append(
                Taxonomy69TaxReconciliationSerializer.serialize(
                    transfer=tax_reconciliation,
                    context_id=tax_reconciliation_context_id,
                    unit_id=tax_reconciliation_unit_id,
                )
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
        shareholders: tuple[
            GcdShareholderTuple,
            ...,
        ] = (),
        nil_facts: tuple[
            TaxonomyNilFact,
            ...,
        ] = (),
        account_balances: tuple[
            TaxonomyAccountBalance,
            ...,
        ] = (),
        facts: tuple[TaxonomyFact, ...] = (),
        tax_reconciliation: (
            TaxReconciliationTransfer | None
        ) = None,
        tax_reconciliation_context_id: str | None = None,
        tax_reconciliation_unit_id: str | None = None,
    ) -> str:
        """Erzeugt die vollständige 6.9-XBRL-Instanz als XML-String."""

        root = self.build_element(
            resolved_fact_plan=resolved_fact_plan,
            contexts=contexts,
            units=units,
            entry_points=entry_points,
            shareholders=shareholders,
            nil_facts=nil_facts,
            account_balances=account_balances,
            facts=facts,
            tax_reconciliation=tax_reconciliation,
            tax_reconciliation_context_id=(
                tax_reconciliation_context_id
            ),
            tax_reconciliation_unit_id=(
                tax_reconciliation_unit_id
            ),
        )

        return self._writer.to_xml_string(
            root
        )

    @staticmethod
    def _validate_tax_reconciliation_arguments(
        *,
        tax_reconciliation: TaxReconciliationTransfer | None,
        context_id: str | None,
        unit_id: str | None,
    ) -> None:
        if tax_reconciliation is None:
            if context_id is not None or unit_id is not None:
                raise ValueError(
                    "tax reconciliation context/unit ids "
                    "require a tax reconciliation"
                )
            return

        if not isinstance(
            tax_reconciliation,
            TaxReconciliationTransfer,
        ):
            raise TypeError(
                "tax_reconciliation must be a "
                "TaxReconciliationTransfer or None"
            )

        if context_id is None or not context_id.strip():
            raise ValueError(
                "tax_reconciliation_context_id is required "
                "for a tax reconciliation"
            )

        if unit_id is None or not unit_id.strip():
            raise ValueError(
                "tax_reconciliation_unit_id is required "
                "for a tax reconciliation"
            )

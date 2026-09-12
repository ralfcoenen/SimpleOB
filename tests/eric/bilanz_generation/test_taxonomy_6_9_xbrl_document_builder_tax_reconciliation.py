"""Tests für die HGBM-Anbindung des Taxonomy69XbrlDocumentBuilder."""

from decimal import Decimal

import pytest

from openbilanz.eric.bilanz_generation.fact_plan_resolver import (
    ResolvedFactPlan,
)
from openbilanz.eric.bilanz_generation.tax_reconciliation import (
    TaxReconciliationChange,
    TaxReconciliationKind,
    TaxReconciliationTransfer,
)
from openbilanz.eric.bilanz_generation.taxonomy_6_9_xbrl_document_builder import (
    GAAP_CI_69_NAMESPACE,
    Taxonomy69XbrlDocumentBuilder,
)


def _transfer() -> TaxReconciliationTransfer:
    return TaxReconciliationTransfer(
        kind=TaxReconciliationKind.CHANGE_VALUE,
        asset_changes=(
            TaxReconciliationChange(
                concept_name=(
                    "bs.ass.fixAss.tan."
                    "otherEquipm.otherbga"
                ),
                actual_period=Decimal("-13.26"),
            ),
        ),
    )


def test_build_element_without_tax_reconciliation_is_unchanged() -> None:
    builder = Taxonomy69XbrlDocumentBuilder()

    root = builder.build_element(
        resolved_fact_plan=ResolvedFactPlan(
            nodes=()
        ),
        contexts={},
        units={},
        entry_points=(),
    )

    assert root.find(
        f"{{{GAAP_CI_69_NAMESPACE}}}hbst.transfer"
    ) is None

def test_build_element_appends_tax_reconciliation() -> None:
    builder = Taxonomy69XbrlDocumentBuilder()

    root = builder.build_element(
        resolved_fact_plan=ResolvedFactPlan(
            nodes=()
        ),
        contexts={},
        units={},
        entry_points=(),
        tax_reconciliation=_transfer(),
        tax_reconciliation_context_id="D-2026",
        tax_reconciliation_unit_id="EUR",
    )

    transfer = root.find(
        f"{{{GAAP_CI_69_NAMESPACE}}}hbst.transfer"
    )
    assert transfer is not None

    kind = transfer.find(
        f"{{{GAAP_CI_69_NAMESPACE}}}hbst.transfer.kind"
    )
    assert kind is not None

    kind_value = kind.find(
        (
            f"{{{GAAP_CI_69_NAMESPACE}}}"
            "hbst.transfer.kind.changeValue"
        )
    )
    assert kind_value is not None
    assert kind_value.attrib == {
        "contextRef": "D-2026",
    }
    assert kind_value.text == "true"

def test_tax_reconciliation_requires_context_and_unit_ids() -> None:
    builder = Taxonomy69XbrlDocumentBuilder()

    with pytest.raises(
        ValueError,
        match="context_id is required",
    ):
        builder.build_element(
            resolved_fact_plan=ResolvedFactPlan(
                nodes=()
            ),
            contexts={},
            units={},
            entry_points=(),
            tax_reconciliation=_transfer(),
            tax_reconciliation_unit_id="EUR",
        )

    with pytest.raises(
        ValueError,
        match="unit_id is required",
    ):
        builder.build_element(
            resolved_fact_plan=ResolvedFactPlan(
                nodes=()
            ),
            contexts={},
            units={},
            entry_points=(),
            tax_reconciliation=_transfer(),
            tax_reconciliation_context_id="D-2026",
        )


def test_tax_reconciliation_ids_without_transfer_are_rejected() -> None:
    builder = Taxonomy69XbrlDocumentBuilder()

    with pytest.raises(
        ValueError,
        match="require a tax reconciliation",
    ):
        builder.build_element(
            resolved_fact_plan=ResolvedFactPlan(
                nodes=()
            ),
            contexts={},
            units={},
            entry_points=(),
            tax_reconciliation_context_id="D-2026",
            tax_reconciliation_unit_id="EUR",
        )

"""Integrationstest für XBRL-Export und Arelle-Validierung."""

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from openbilanz.exporter.xbrl_export import XbrlExporter
from openbilanz.taxonomy.arelle_adapter import ArelleAdapter
from openbilanz.taxonomy.concept import (
    TaxonomyBalance,
    TaxonomyConcept,
    TaxonomyPeriodType,
)
from openbilanz.taxonomy.context import TaxonomyContext
from openbilanz.taxonomy.entry_point import TaxonomyEntryPoint
from openbilanz.taxonomy.fact import TaxonomyFact
from openbilanz.taxonomy.resolver import TaxonomyResolver
from openbilanz.taxonomy.taxonomy import TaxonomyVersion
from openbilanz.taxonomy.unit import TaxonomyUnit

TAXONOMY_ROOT = Path(
    "/tmp/openbilanz-taxonomy"
)

DE_GAAP_CI_NAMESPACE = (
    "http://www.xbrl.de/taxonomies/"
    "de-gaap-ci-2024-04-01"
)

TEST_ENTITY_SCHEME = (
    "http://www.bundesfinanzministerium.de"
)


def test_exported_xbrl_instance_is_validated_by_arelle(
    tmp_path: Path,
) -> None:
    """Eine von OpenbilanzUG erzeugte XBRL-Instanz wird von Arelle geprüft."""

    version_root = TAXONOMY_ROOT / "6.8"

    if not version_root.is_dir():
        pytest.skip(
            "Taxonomy 6.8 is not installed locally"
        )

    resolver = TaxonomyResolver(
        root=TAXONOMY_ROOT
    )

    entry_point_path = resolver.gaap_ci_fiscal_entry_point(
        TaxonomyVersion.V6_8
    )

    base_entry_point = TaxonomyEntryPoint.from_file(
        entry_point_path
    )

    entry_point = TaxonomyEntryPoint(
        path=base_entry_point.path,
        namespace=base_entry_point.namespace,
        schema_imports=base_entry_point.schema_imports,
        linkbase_references=base_entry_point.linkbase_references,
        schema_ref=entry_point_path.as_uri(),
    )

    concept = TaxonomyConcept(
        name="bs.ass.fixAss",
        concept_id="de-gaap-ci_bs.ass.fixAss",
        type_name="xbrli:monetaryItemType",
        substitution_group="xbrli:item",
        period_type=TaxonomyPeriodType.INSTANT,
        balance=TaxonomyBalance.DEBIT,
        abstract=False,
        nillable=True,
    )

    context = TaxonomyContext(
        entity_identifier="DE123456789",
        entity_scheme=TEST_ENTITY_SCHEME,
        period_type=TaxonomyPeriodType.INSTANT,
        start_date=None,
        end_date=date(2025, 12, 31),
    )

    unit = TaxonomyUnit.eur()

    fact = TaxonomyFact(
        concept=concept,
        amount=Decimal("125000.00"),
        context=context,
        unit=unit,
    )

    exporter = XbrlExporter()

    xml = exporter.export(
        contexts={
            "ctx-2025": context,
        },
        units={
            "EUR": unit,
        },
        facts=(fact,),
        taxonomy_namespace=DE_GAAP_CI_NAMESPACE,
        entry_points=(
            entry_point,
        ),
    )

    instance_path = (
        tmp_path
        / "openbilanz-test-instance.xbrl"
    )

    instance_path.write_text(
        xml,
        encoding="utf-8",
    )

    adapter = ArelleAdapter()

    try:
        result = adapter.validate(
        instance_path
    )
    finally:
        adapter.close()

    assert result.is_valid
    assert result.errors == ()


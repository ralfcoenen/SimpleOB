"""Tests für den XBRL-Export."""
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from openbilanz.exporter.xbrl_export import XbrlExporter
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

DE_GAAP_CI_NAMESPACE = (
    "http://www.xbrl.de/taxonomies/"
    "de-gaap-ci-2024-04-01"
)

TEST_ENTITY_SCHEME = (
    "http://www.bundesfinanzministerium.de"
)


def test_xbrl_exporter_serializes_instance() -> None:
    """Der Exporter erzeugt eine vollständige XBRL-Instanz."""

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

    entry_point = TaxonomyEntryPoint(
        path=Path(
            "de-gaap-ci-2024-04-01-shell-fiscal.xsd"
        ),
        namespace=(
            "http://www.xbrl.de/taxonomies/"
            "de-gaap-ci-2024-04-01/shell-fiscal"
        ),
        schema_imports=(),
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
        entry_points=(entry_point,),
    )

    assert xml.startswith(
        "<?xml version="
    )
    assert "encoding='utf-8'" in xml

    assert (
        "de-gaap-ci-2024-04-01-shell-fiscal.xsd"
        in xml
    )

    assert "bs.ass.fixAss" in xml
    assert "125000.00" in xml
    assert 'contextRef="ctx-2025"' in xml
    assert 'unitRef="EUR"' in xml


def test_xbrl_exporter_uses_real_taxonomy_entry_point() -> None:
    """Der Exporter verwendet Metadaten eines realen GAAP-CI-Entry-Points."""

    taxonomy_root = Path(
        "/tmp/openbilanz-taxonomy"
    )

    version_root = taxonomy_root / "6.8"

    if not version_root.is_dir():
        pytest.skip(
            "Taxonomy 6.8 is not installed locally"
        )

    resolver = TaxonomyResolver(
        root=taxonomy_root
    )

    entry_point_path = resolver.gaap_ci_fiscal_entry_point(
        TaxonomyVersion.V6_8
    )

    entry_point = TaxonomyEntryPoint.from_file(
        entry_point_path
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
        taxonomy_namespace=(
            "http://www.xbrl.de/taxonomies/"
            "de-gaap-ci-2024-04-01"
        ),
        entry_points=(
            entry_point,
        ),
    )

    assert entry_point.namespace == (
        "http://www.xbrl.de/taxonomies/"
        "de-gaap-ci-2024-04-01/shell-fiscal"
    )

    assert entry_point.schema_ref_uri in xml
    assert "bs.ass.fixAss" in xml
    assert "125000.00" in xml


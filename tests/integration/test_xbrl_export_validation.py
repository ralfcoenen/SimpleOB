"""Integrationstest für XBRL-Export und Arelle-Validierung."""

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from openbilanz.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
from openbilanz.accounting.statement_category import StatementCategory
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
from openbilanz.taxonomy.fact_builder import TaxonomyFactBuilder
from openbilanz.taxonomy.mapper import TaxonomyMapper
from openbilanz.taxonomy.mapping import TaxonomyMappingRule
from openbilanz.taxonomy.mapping_set import TaxonomyMappingSet
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

def test_exported_xbrl_instance_with_balance_sheet_and_income_statement(
    tmp_path: Path,
) -> None:
    """Bilanz- und GuV-Facts aus dem echten Taxonomiemodell sind valide."""

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

    adapter = ArelleAdapter()

    try:
        taxonomy_model = adapter.model(
            entry_point_path
        )

        concepts_by_name = {
            concept.name: concept
            for concept in taxonomy_model.concepts.concepts
        }

        fixed_assets_concept = concepts_by_name[
            "bs.ass.fixAss"
        ]

        net_income_concept = concepts_by_name[
            "is.netIncome"
        ]

        instant_context = TaxonomyContext(
            entity_identifier="DE123456789",
            entity_scheme=TEST_ENTITY_SCHEME,
            period_type=TaxonomyPeriodType.INSTANT,
            start_date=None,
            end_date=date(2025, 12, 31),
        )

        duration_context = TaxonomyContext(
            entity_identifier="DE123456789",
            entity_scheme=TEST_ENTITY_SCHEME,
            period_type=TaxonomyPeriodType.DURATION,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
        )

        unit = TaxonomyUnit.eur()

        fixed_assets_fact = TaxonomyFact(
            concept=fixed_assets_concept,
            amount=Decimal("125000.00"),
            context=instant_context,
            unit=unit,
        )

        net_income_fact = TaxonomyFact(
            concept=net_income_concept,
            amount=Decimal("15000.00"),
            context=duration_context,
            unit=unit,
        )

        exporter = XbrlExporter()

        xml = exporter.export(
            contexts={
                "ctx-instant-2025": instant_context,
                "ctx-duration-2025": duration_context,
            },
            units={
                "EUR": unit,
            },
            facts=(
                fixed_assets_fact,
                net_income_fact,
            ),
            taxonomy_namespace=DE_GAAP_CI_NAMESPACE,
            entry_points=(
                entry_point,
            ),
        )

        instance_path = (
            tmp_path
            / "openbilanz-balance-and-income.xbrl"
        )

        instance_path.write_text(
            xml,
            encoding="utf-8",
        )

        result = adapter.validate(
            instance_path
        )

    finally:
        adapter.close()

    assert result.is_valid
    assert result.errors == ()


def test_financial_statement_positions_are_exported_to_valid_xbrl(
    tmp_path: Path,
) -> None:
    """Abschlusspositionen werden über Mapping und FactBuilder valide exportiert."""

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

    fixed_assets_position = FinancialStatementPosition(
        code="HGB.266.AKTIVA.A",
        name="Anlagevermögen",
        category=StatementCategory.ASSET,
    )

    net_income_position = FinancialStatementPosition(
        code="HGB.275.JAHRESERGEBNIS",
        name="Jahresüberschuss/Jahresfehlbetrag",
        category=StatementCategory.RESULT,
    )

    adapter = ArelleAdapter()

    try:
        taxonomy_model = adapter.model(
            entry_point_path
        )

        mappings = TaxonomyMappingSet(
            rules=(
                TaxonomyMappingRule(
                    position=fixed_assets_position,
                    concept_name="bs.ass.fixAss",
                ),
                TaxonomyMappingRule(
                    position=net_income_position,
                    concept_name="is.netIncome",
                ),
            )
        )

        validation_result = mappings.validate(
            taxonomy_model
        )

        assert validation_result.is_valid

        mapper = TaxonomyMapper(
            mappings=mappings,
            taxonomy_model=taxonomy_model,
        )

        fact_builder = TaxonomyFactBuilder(
            mapper=mapper
        )

        instant_context = TaxonomyContext(
            entity_identifier="DE123456789",
            entity_scheme=TEST_ENTITY_SCHEME,
            period_type=TaxonomyPeriodType.INSTANT,
            start_date=None,
            end_date=date(2025, 12, 31),
        )

        duration_context = TaxonomyContext(
            entity_identifier="DE123456789",
            entity_scheme=TEST_ENTITY_SCHEME,
            period_type=TaxonomyPeriodType.DURATION,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
        )

        unit = TaxonomyUnit.eur()

        balance_sheet_facts = fact_builder.build(
            amounts={
                fixed_assets_position: Decimal("125000.00"),
            },
            context=instant_context,
            unit=unit,
        )

        income_statement_facts = fact_builder.build(
            amounts={
                net_income_position: Decimal("15000.00"),
            },
            context=duration_context,
            unit=unit,
        )

        facts = (
            balance_sheet_facts
            + income_statement_facts
        )

        assert len(facts) == 2

        exporter = XbrlExporter()

        xml = exporter.export(
            contexts={
                "ctx-instant-2025": instant_context,
                "ctx-duration-2025": duration_context,
            },
            units={
                "EUR": unit,
            },
            facts=facts,
            taxonomy_namespace=DE_GAAP_CI_NAMESPACE,
            entry_points=(
                entry_point,
            ),
        )

        instance_path = (
            tmp_path
            / "openbilanz-financial-statement.xbrl"
        )

        instance_path.write_text(
            xml,
            encoding="utf-8",
        )

        result = adapter.validate(
            instance_path
        )

    finally:
        adapter.close()

    assert result.is_valid
    assert result.errors == ()


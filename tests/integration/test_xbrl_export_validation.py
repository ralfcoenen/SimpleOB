"""Integrationstest für XBRL-Export und Arelle-Validierung."""

from datetime import date
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest

from openbilanz.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
from openbilanz.accounting.statement_category import StatementCategory
from openbilanz.domain.company import Company
from openbilanz.domain.fiscal_year import FiscalYear
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
from openbilanz.taxonomy.gcd_company_data import GcdCompanyData
from openbilanz.taxonomy.gcd_company_identifiers import (
    GcdCompanyIdentifiers,
)
from openbilanz.taxonomy.gcd_domestic_branch_of_foreign_company import (
    GcdDomesticBranchOfForeignCompanyType,
)
from openbilanz.taxonomy.gcd_entity_with_taxable_purpose_business import (
    GcdEntityWithTaxablePurposeBusinessType,
)
from openbilanz.taxonomy.gcd_fact_builder import GcdFactBuilder
from openbilanz.taxonomy.gcd_report_profile import (
    GcdReportProfile,
)
from openbilanz.taxonomy.gcd_shareholder import (
    GcdShareDivideKey,
    GcdShareholder,
    GcdShareholderGroup,
    GcdShareholderLegalStatus,
)
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

DE_GCD_NAMESPACE = (
    "http://www.xbrl.de/taxonomies/"
    "de-gcd-2024-04-01"
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

def test_combined_gcd_and_gaap_ci_instance_is_validated_by_arelle(
    tmp_path: Path,
) -> None:
    """GCD- und GAAP-CI-Facts werden gemeinsam valide exportiert."""

    version_root = TAXONOMY_ROOT / "6.8"

    if not version_root.is_dir():
        pytest.skip(
            "Taxonomy 6.8 is not installed locally"
        )

    resolver = TaxonomyResolver(
        root=TAXONOMY_ROOT
    )

    gcd_entry_point_path = resolver.gcd_entry_point(
        TaxonomyVersion.V6_8
    )

    gaap_entry_point_path = resolver.gaap_ci_fiscal_entry_point(
        TaxonomyVersion.V6_8
    )

    gcd_base_entry_point = TaxonomyEntryPoint.from_file(
        gcd_entry_point_path
    )

    gaap_base_entry_point = TaxonomyEntryPoint.from_file(
        gaap_entry_point_path
    )

    gcd_entry_point = TaxonomyEntryPoint(
        path=gcd_base_entry_point.path,
        namespace=gcd_base_entry_point.namespace,
        schema_imports=gcd_base_entry_point.schema_imports,
        linkbase_references=gcd_base_entry_point.linkbase_references,
        schema_ref=gcd_entry_point_path.as_uri(),
    )

    gaap_entry_point = TaxonomyEntryPoint(
        path=gaap_base_entry_point.path,
        namespace=gaap_base_entry_point.namespace,
        schema_imports=gaap_base_entry_point.schema_imports,
        linkbase_references=gaap_base_entry_point.linkbase_references,
        schema_ref=gaap_entry_point_path.as_uri(),
    )

    adapter = ArelleAdapter()

    try:
        gcd_model = adapter.model(
            gcd_entry_point_path
        )

        gaap_model = adapter.model(
            gaap_entry_point_path
        )

        company = Company(
            company_id=uuid4(),
            name="Muster UG (haftungsbeschränkt)",
        )

        company_data = GcdCompanyData(
            company=company,
            tax_number="1234567890123",
            legal_form="UG (haftungsbeschränkt)",
        )

        fiscal_year = FiscalYear(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
        )

        duration_context = TaxonomyContext(
            entity_identifier="DE123456789",
            entity_scheme=TEST_ENTITY_SCHEME,
            period_type=TaxonomyPeriodType.DURATION,
            start_date=fiscal_year.start_date,
            end_date=fiscal_year.end_date,
        )

        instant_context = TaxonomyContext(
            entity_identifier="DE123456789",
            entity_scheme=TEST_ENTITY_SCHEME,
            period_type=TaxonomyPeriodType.INSTANT,
            start_date=None,
            end_date=fiscal_year.end_date,
        )

        gcd_builder = GcdFactBuilder()

        gcd_facts = (
            gcd_builder.company_facts(
                data=company_data,
                taxonomy_model=gcd_model,
                context=duration_context,
            )
            + gcd_builder.fiscal_year_facts(
                fiscal_year=fiscal_year,
                taxonomy_model=gcd_model,
                context=duration_context,
            )
        )

        gaap_concepts_by_name = {
            concept.name: concept
            for concept in gaap_model.concepts.concepts
        }

        unit = TaxonomyUnit.eur()

        fixed_assets_fact = TaxonomyFact(
            concept=gaap_concepts_by_name[
                "bs.ass.fixAss"
            ],
            amount=Decimal("125000.00"),
            context=instant_context,
            unit=unit,
        )

        net_income_fact = TaxonomyFact(
            concept=gaap_concepts_by_name[
                "is.netIncome"
            ],
            amount=Decimal("15000.00"),
            context=duration_context,
            unit=unit,
        )

        facts = (
            gcd_facts
            + (
                fixed_assets_fact,
                net_income_fact,
            )
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
            facts=facts,
            taxonomy_namespace=DE_GAAP_CI_NAMESPACE,
            taxonomy_namespaces={
                "de-gcd": DE_GCD_NAMESPACE,
                "de-gaap-ci": DE_GAAP_CI_NAMESPACE,
            },
            entry_points=(
                gcd_entry_point,
                gaap_entry_point,
            ),
        )

        instance_path = (
            tmp_path
            / "openbilanz-gcd-and-gaap-ci.xbrl"
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
    
def test_combined_69_instance_with_report_element_is_validated_by_arelle(
    tmp_path: Path,
) -> None:
    """GCD-Tuple und GAAP-CI-Facts der Taxonomie 6.9 sind valide."""

    version_root = TAXONOMY_ROOT / "6.9"

    if not version_root.is_dir():
        pytest.skip(
            "Taxonomy 6.9 is not installed locally"
        )

    gcd_namespace = (
        "http://www.xbrl.de/taxonomies/"
        "de-gcd-2025-04-01"
    )

    gaap_namespace = (
        "http://www.xbrl.de/taxonomies/"
        "de-gaap-ci-2025-04-01"
    )

    resolver = TaxonomyResolver(
        root=TAXONOMY_ROOT
    )

    gcd_entry_point_path = resolver.gcd_entry_point(
        TaxonomyVersion.V6_9
    )

    gaap_entry_point_path = resolver.gaap_ci_fiscal_entry_point(
        TaxonomyVersion.V6_9
    )

    gcd_base_entry_point = TaxonomyEntryPoint.from_file(
        gcd_entry_point_path
    )

    gaap_base_entry_point = TaxonomyEntryPoint.from_file(
        gaap_entry_point_path
    )

    gcd_entry_point = TaxonomyEntryPoint(
        path=gcd_base_entry_point.path,
        namespace=gcd_base_entry_point.namespace,
        schema_imports=gcd_base_entry_point.schema_imports,
        linkbase_references=gcd_base_entry_point.linkbase_references,
        schema_ref=gcd_entry_point_path.as_uri(),
    )

    gaap_entry_point = TaxonomyEntryPoint(
        path=gaap_base_entry_point.path,
        namespace=gaap_base_entry_point.namespace,
        schema_imports=gaap_base_entry_point.schema_imports,
        linkbase_references=gaap_base_entry_point.linkbase_references,
        schema_ref=gaap_entry_point_path.as_uri(),
    )

    adapter = ArelleAdapter()

    try:
        gcd_model = adapter.model(
            gcd_entry_point_path
        )

        gaap_model = adapter.model(
            gaap_entry_point_path
        )

        company = Company(
            company_id=uuid4(),
            name="Muster UG (haftungsbeschränkt)",
        )

        company_data = GcdCompanyData(
            company=company,
            tax_number="1234567890123",
            legal_form="UG (haftungsbeschränkt)",
            street="Musterstraße",
            house_number="12a",
            postal_code="12345",
            city="Musterstadt",
            country="DE",
            business="Softwareentwicklung",
        )

        fiscal_year = FiscalYear(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )

        duration_context = TaxonomyContext(
            entity_identifier="DE123456789",
            entity_scheme=TEST_ENTITY_SCHEME,
            period_type=TaxonomyPeriodType.DURATION,
            start_date=fiscal_year.start_date,
            end_date=fiscal_year.end_date,
        )

        instant_context = TaxonomyContext(
            entity_identifier="DE123456789",
            entity_scheme=TEST_ENTITY_SCHEME,
            period_type=TaxonomyPeriodType.INSTANT,
            start_date=None,
            end_date=fiscal_year.end_date,
        )

        gcd_builder = GcdFactBuilder()
        
        branch = gcd_builder.domestic_branch_of_foreign_company(
            branch_type=GcdDomesticBranchOfForeignCompanyType.HGB,
            taxonomy_model=gcd_model,
            context=duration_context,
        )

        taxable_purpose_business = (
            gcd_builder.entity_with_taxable_purpose_business(
                business_type=(
                    GcdEntityWithTaxablePurposeBusinessType.NORMAL
                ),
                taxonomy_model=gcd_model,
                context=duration_context,
            )
        )

        shareholder_data = GcdShareholder(
            name="Mustermann",
            first_name="Max",
            shareholder_id="1",
            tax_number="1234567890123",
            tax_id="12345678901",
            wid="WID-1",
            group=GcdShareholderGroup.LIMITED,
            legal_status=(
                GcdShareholderLegalStatus.NATURAL_PERSON
            ),
            share_divide_key=GcdShareDivideKey(
                numerator="100",
                denominator="100",
            ),
            current_number=1,
            special_balance_required=False,
            extension_required=False,
            economic_id="BEWI-1",
            id_not_assigned="NO-ID",
        )

        shareholder = gcd_builder.shareholder(
            shareholder=shareholder_data,
            taxonomy_model=gcd_model,
            context=duration_context,
        )

        identifiers = GcdCompanyIdentifiers(
            tax_number_13="1234567890123",
            tax_id="12345678901",
            tax_economic_id="DE123456789",
            bf4="1234",
        )

        company_id_no = gcd_builder.company_id_no(
            identifiers=identifiers,
            taxonomy_model=gcd_model,
            context=duration_context,
        )

        previous_fiscal_year = FiscalYear(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
        )

        gcd_facts = (
            gcd_builder.company_facts(
                data=company_data,
                taxonomy_model=gcd_model,
                context=duration_context,
            )
            + gcd_builder.fiscal_year_facts(
                fiscal_year=fiscal_year,
                previous_fiscal_year=previous_fiscal_year,
                taxonomy_model=gcd_model,
                context=duration_context,
            )
        )

        profile = GcdReportProfile.standard()
        

        profile_facts = gcd_builder.report_profile_facts(
            profile=profile,
            taxonomy_model=gcd_model,
            context=duration_context,
        )
        
        report_element = gcd_builder.report_element(
            profile=profile,
            taxonomy_model=gcd_model,
            context=duration_context,
            version=TaxonomyVersion.V6_9,
        )

        gaap_concepts_by_name = {
            concept.name: concept
            for concept in gaap_model.concepts.concepts
        }

        unit = TaxonomyUnit.eur()
        pure_unit = TaxonomyUnit.pure()

        fixed_assets_fact = TaxonomyFact(
            concept=gaap_concepts_by_name[
                "bs.ass.fixAss"
            ],
            amount=Decimal("125000.00"),
            context=instant_context,
            unit=unit,
        )

        net_income_fact = TaxonomyFact(
            concept=gaap_concepts_by_name[
                "is.netIncome"
            ],
            amount=Decimal("15000.00"),
            context=duration_context,
            unit=unit,
        )

        facts = (
            gcd_facts
            + profile_facts
            + (
                fixed_assets_fact,
                net_income_fact,
            )
        )

        exporter = XbrlExporter()

        xml = exporter.export(
            contexts={
                "ctx-instant-2026": instant_context,
                "ctx-duration-2026": duration_context,
            },
            units={
                "EUR": unit,
                "PURE": pure_unit,
            },
            facts=facts,
            report_elements=(
                report_element,
            ),
            taxonomy_namespace=gaap_namespace,
            taxonomy_namespaces={
                "de-gcd": gcd_namespace,
                "de-gaap-ci": gaap_namespace,
            },
            entry_points=(
                gcd_entry_point,
                gaap_entry_point,
            ),
            company_id_nos=(
                company_id_no,
            ),
            shareholders=(
                shareholder,
            ),
            domestic_branches=(
                branch,
            ),
            taxable_purpose_businesses=(
                taxable_purpose_business,
            ),
        )

        instance_path = (
            tmp_path
            / "openbilanz-gcd-gaap-ci-69.xbrl"
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

def test_combined_610_instance_with_report_element_is_validated_by_arelle(
    tmp_path: Path,
) -> None:
    """GCD-Tuple und GAAP-CI-Facts der Taxonomie 6.10 sind valide."""

    version_root = TAXONOMY_ROOT / "6.10"

    if not version_root.is_dir():
        pytest.skip(
            "Taxonomy 6.10 is not installed locally"
        )

    gcd_namespace = (
        "http://www.xbrl.de/taxonomies/"
        "de-gcd-2026-04-01"
    )

    gaap_namespace = (
        "http://www.xbrl.de/taxonomies/"
        "de-gaap-ci-2026-04-01"
    )

    resolver = TaxonomyResolver(
        root=TAXONOMY_ROOT
    )

    gcd_entry_point_path = resolver.gcd_entry_point(
        TaxonomyVersion.V6_10
    )

    gaap_entry_point_path = resolver.gaap_ci_fiscal_entry_point(
        TaxonomyVersion.V6_10
    )

    gcd_base_entry_point = TaxonomyEntryPoint.from_file(
        gcd_entry_point_path
    )

    gaap_base_entry_point = TaxonomyEntryPoint.from_file(
        gaap_entry_point_path
    )

    gcd_entry_point = TaxonomyEntryPoint(
        path=gcd_base_entry_point.path,
        namespace=gcd_base_entry_point.namespace,
        schema_imports=gcd_base_entry_point.schema_imports,
        linkbase_references=gcd_base_entry_point.linkbase_references,
        schema_ref=gcd_entry_point_path.as_uri(),
    )

    gaap_entry_point = TaxonomyEntryPoint(
        path=gaap_base_entry_point.path,
        namespace=gaap_base_entry_point.namespace,
        schema_imports=gaap_base_entry_point.schema_imports,
        linkbase_references=gaap_base_entry_point.linkbase_references,
        schema_ref=gaap_entry_point_path.as_uri(),
    )

    adapter = ArelleAdapter()

    try:
        gcd_model = adapter.model(
            gcd_entry_point_path
        )

        gaap_model = adapter.model(
            gaap_entry_point_path
        )

        company = Company(
            company_id=uuid4(),
            name="Muster UG (haftungsbeschränkt)",
        )

        company_data = GcdCompanyData(
            company=company,
            tax_number="1234567890123",
            legal_form="UG (haftungsbeschränkt)",
            street="Musterstraße",
            house_number="12a",
            postal_code="12345",
            city="Musterstadt",
            country="DE",
            business="Softwareentwicklung",
        )

        fiscal_year = FiscalYear(
            start_date=date(2027, 1, 1),
            end_date=date(2027, 12, 31),
        )

        duration_context = TaxonomyContext(
            entity_identifier="DE123456789",
            entity_scheme=TEST_ENTITY_SCHEME,
            period_type=TaxonomyPeriodType.DURATION,
            start_date=fiscal_year.start_date,
            end_date=fiscal_year.end_date,
        )

        instant_context = TaxonomyContext(
            entity_identifier="DE123456789",
            entity_scheme=TEST_ENTITY_SCHEME,
            period_type=TaxonomyPeriodType.INSTANT,
            start_date=None,
            end_date=fiscal_year.end_date,
        )

        gcd_builder = GcdFactBuilder()
        
        branch = gcd_builder.domestic_branch_of_foreign_company(
            branch_type=GcdDomesticBranchOfForeignCompanyType.HGB,
            taxonomy_model=gcd_model,
            context=duration_context,
        )

        taxable_purpose_business = (
            gcd_builder.entity_with_taxable_purpose_business(
                business_type=(
                    GcdEntityWithTaxablePurposeBusinessType.NORMAL
                ),
                taxonomy_model=gcd_model,
                context=duration_context,
            )
        )
        
        shareholder_data = GcdShareholder(
            name="Mustermann",
            first_name="Max",
            shareholder_id="1",
            tax_number="1234567890123",
            tax_id="12345678901",
            wid="WID-1",
            group=GcdShareholderGroup.LIMITED,
            legal_status=(
                GcdShareholderLegalStatus.NATURAL_PERSON
            ),
            share_divide_key=GcdShareDivideKey(
                numerator="100",
                denominator="100",
            ),
            current_number=1,
            special_balance_required=False,
            extension_required=False,
            economic_id="BEWI-1",
            id_not_assigned="NO-ID",
        )

        shareholder = gcd_builder.shareholder(
            shareholder=shareholder_data,
            taxonomy_model=gcd_model,
            context=duration_context,
        )

        identifiers = GcdCompanyIdentifiers(
            tax_number_13="1234567890123",
            tax_id="12345678901",
            tax_economic_id="DE123456789",
            bf4="1234",
        )

        company_id_no = gcd_builder.company_id_no(
            identifiers=identifiers,
            taxonomy_model=gcd_model,
            context=duration_context,
        )

        gcd_facts = (
            gcd_builder.company_facts(
                data=company_data,
                taxonomy_model=gcd_model,
                context=duration_context,
            )
            + gcd_builder.fiscal_year_facts(
                fiscal_year=fiscal_year,
                taxonomy_model=gcd_model,
                context=duration_context,
            )
        )

        profile = GcdReportProfile.standard()
        

        profile_facts = gcd_builder.report_profile_facts(
            profile=profile,
            taxonomy_model=gcd_model,
            context=duration_context,
        )

        report_element = gcd_builder.report_element(
            profile=profile,
            taxonomy_model=gcd_model,
            context=duration_context,
            version=TaxonomyVersion.V6_10,
        )

        gaap_concepts_by_name = {
            concept.name: concept
            for concept in gaap_model.concepts.concepts
        }

        unit = TaxonomyUnit.eur()
        pure_unit = TaxonomyUnit.pure()

        fixed_assets_fact = TaxonomyFact(
            concept=gaap_concepts_by_name[
                "bs.ass.fixAss"
            ],
            amount=Decimal("125000.00"),
            context=instant_context,
            unit=unit,
        )

        net_income_fact = TaxonomyFact(
            concept=gaap_concepts_by_name[
                "is.netIncome"
            ],
            amount=Decimal("15000.00"),
            context=duration_context,
            unit=unit,
        )

        facts = (
            gcd_facts
            + profile_facts
            + (
                fixed_assets_fact,
                net_income_fact,
            )
        )

        exporter = XbrlExporter()

        xml = exporter.export(
            contexts={
                "ctx-instant-2027": instant_context,
                "ctx-duration-2027": duration_context,
            },
            units={
                "EUR": unit,
                "PURE": pure_unit,
            },
            facts=facts,
            report_elements=(
                report_element,
            ),
            taxonomy_namespace=gaap_namespace,
            taxonomy_namespaces={
                "de-gcd": gcd_namespace,
                "de-gaap-ci": gaap_namespace,
            },
            entry_points=(
                gcd_entry_point,
                gaap_entry_point,
            ),
            company_id_nos=(
                company_id_no,
            ),
            shareholders=(
                shareholder,
            ),
            domestic_branches=(
                branch,
            ),
            taxable_purpose_businesses=(
                taxable_purpose_business,
            ),
        )

        instance_path = (
            tmp_path
            / "openbilanz-gcd-gaap-ci-610.xbrl"
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
    

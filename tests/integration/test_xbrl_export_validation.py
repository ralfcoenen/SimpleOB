"""Integrationstest für XBRL-Export und Arelle-Validierung."""

from datetime import date
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest

from simpleob.accounting.account_balance import AccountBalance
from simpleob.accounting.financial_statement_builder import (
    FinancialStatementBuilder,
)
from simpleob.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
from simpleob.accounting.mapper import AccountMapper
from simpleob.accounting.statement_category import StatementCategory
from simpleob.domain.account_mapping_rule import AccountMappingRule
from simpleob.domain.account_type import AccountType
from simpleob.domain.chart_of_accounts_template import (
    ChartOfAccountsTemplate,
)
from simpleob.domain.company import Company
from simpleob.domain.fiscal_year import FiscalYear
from simpleob.domain.template_account import TemplateAccount
from simpleob.exporter.xbrl_export import XbrlExporter
from simpleob.hgb.balance_sheet_structure import (
    create_hgb_balance_sheet_structure,
)
from simpleob.hgb.income_statement_structure import (
    create_hgb_income_statement_structure,
)
from simpleob.taxonomy.arelle_adapter import ArelleAdapter
from simpleob.taxonomy.concept import (
    TaxonomyBalance,
    TaxonomyConcept,
    TaxonomyPeriodType,
)
from simpleob.taxonomy.context import TaxonomyContext
from simpleob.taxonomy.entry_point import TaxonomyEntryPoint
from simpleob.taxonomy.fact import TaxonomyFact
from simpleob.taxonomy.fact_builder import TaxonomyFactBuilder
from simpleob.taxonomy.gcd_company_data import GcdCompanyData
from simpleob.taxonomy.gcd_company_identifiers import (
    GcdCompanyIdentifiers,
)
from simpleob.taxonomy.gcd_domestic_branch_of_foreign_company import (
    GcdDomesticBranchOfForeignCompanyType,
)
from simpleob.taxonomy.gcd_entity_with_taxable_purpose_business import (
    GcdEntityWithTaxablePurposeBusinessType,
)
from simpleob.taxonomy.gcd_fact_builder import GcdFactBuilder
from simpleob.taxonomy.gcd_report_profile import (
    GcdReportProfile,
)
from simpleob.taxonomy.gcd_shareholder import (
    GcdShareDivideKey,
    GcdShareholder,
    GcdShareholderGroup,
    GcdShareholderLegalStatus,
)
from simpleob.taxonomy.hgb_gaap_ci_mapping import (
    create_hgb_gaap_ci_mapping,
)
from simpleob.taxonomy.mapper import TaxonomyMapper
from simpleob.taxonomy.mapping import TaxonomyMappingRule
from simpleob.taxonomy.mapping_set import TaxonomyMappingSet
from simpleob.taxonomy.resolver import TaxonomyResolver
from simpleob.taxonomy.taxonomy import TaxonomyVersion
from simpleob.taxonomy.unit import TaxonomyUnit

TAXONOMY_ROOT = Path(
    "data/taxonomy"
).resolve()

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
            tax_number=None,
            tax_id=None,
            wid=None,
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

        assert (
            "genInfo.company.id.shareholder.beWiNr"
            in xml
        )

        assert (
            'genInfo.company.id.shareholder.taxnumber '
            'contextRef="ctx-duration-2026" '
            'xsi:nil="true"'
            in xml
        )

        assert (
            'genInfo.company.id.shareholder.taxid '
            'contextRef="ctx-duration-2026" '
            'xsi:nil="true"'
            in xml
        )

        assert (
            'genInfo.company.id.shareholder.WID '
            'contextRef="ctx-duration-2026" '
            'xsi:nil="true"'
            in xml
        )
        assert (
            "genInfo.report.id.reportElement.reportElements.B"
            in xml
        )

        assert (
            "genInfo.report.id.reportElement.reportElements.GuV"
            in xml
        )

        assert (
            "genInfo.report.id.reportElement.reportElements.BAL"
            not in xml
        )

        assert (
            "genInfo.report.id.reportElement.reportElements.KS"
            not in xml
        )

        assert (
            "genInfo.company.id.domesticBranchOfForeignCompany.HGB"
            in xml
        )

        assert (
            "genInfo.company.id.entityWithTaxablePurposeBusiness.normal"
            in xml
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

        assert (
            "genInfo.company.id.shareholder.beWiNr"
            in xml
        )

        assert (
            "genInfo.company.id.shareholder.idNotAssigned"
            in xml
        )

        assert (
            "genInfo.report.id.reportElement.reportElements.B"
            in xml
        )

        assert (
            "genInfo.report.id.reportElement.reportElements.GuV"
            in xml
        )

        assert (
            "genInfo.report.id.reportElement.reportElements.BAL"
            not in xml
        )

        assert (
            "genInfo.report.id.reportElement.reportElements.KS"
            not in xml
        )

        assert (
            "genInfo.company.id.domesticBranchOfForeignCompany.HGB"
            in xml
        )

        assert (
            "genInfo.company.id.entityWithTaxablePurposeBusiness.normal"
            in xml
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

def test_gaap_ci_69_builds_facts_from_real_hgb_statement_pipeline(
    tmp_path: Path,
) -> None:
    """HGB-Abschlusswerte werden über das Mapping zu validem GAAP-CI-XBRL."""

    version_root = TAXONOMY_ROOT / "6.9"

    if not version_root.is_dir():
        pytest.skip(
            "Taxonomy 6.9 is not installed locally"
        )

    resolver = TaxonomyResolver(
        root=TAXONOMY_ROOT
    )

    entry_point_path = resolver.gaap_ci_fiscal_entry_point(
        TaxonomyVersion.V6_9
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

    taxonomy_namespace = (
        "http://www.xbrl.de/taxonomies/"
        "de-gaap-ci-2025-04-01"
    )

    assets, liabilities = (
        create_hgb_balance_sheet_structure()
    )

    income_statement = (
        create_hgb_income_statement_structure()
    )

    def find_position(
        root: FinancialStatementPosition,
        code: str,
    ) -> FinancialStatementPosition:
        if root.code == code:
            return root

        for child in root.children:
            try:
                return find_position(
                    child,
                    code,
                )
            except ValueError:
                pass

        raise ValueError(
            f"HGB position not found: {code}"
        )

    bank = find_position(
        assets,
        "HGB.266.AKTIVA.B.IV",
    )

    subscribed_capital = find_position(
        liabilities,
        "HGB.266.PASSIVA.A.I",
    )

    trade_liabilities = find_position(
        liabilities,
        "HGB.266.PASSIVA.C.4",
    )

    net_sales = find_position(
        income_statement,
        "HGB.275.GKV.1",
    )

    other_cost = find_position(
        income_statement,
        "HGB.275.GKV.8",
    )

    accounts = (
        TemplateAccount(
            account_number="1200",
            name="Bank",
            account_type=AccountType.ASSET,
        ),
        TemplateAccount(
            account_number="0800",
            name="Gezeichnetes Kapital",
            account_type=AccountType.EQUITY,
        ),
        TemplateAccount(
            account_number="1600",
            name="Verbindlichkeiten aus Lieferungen",
            account_type=AccountType.LIABILITY,
        ),
        TemplateAccount(
            account_number="8400",
            name="Umsatzerlöse",
            account_type=AccountType.REVENUE,
        ),
        TemplateAccount(
            account_number="4900",
            name="Sonstige betriebliche Aufwendungen",
            account_type=AccountType.EXPENSE,
        ),
    )

    chart_of_accounts = ChartOfAccountsTemplate(
        name="GAAP-CI-Integrationstest",
        accounts=accounts,
        account_mapping_rules=(
            AccountMappingRule(
                account_number="1200",
                debit_position=bank,
                credit_position=None,
            ),
            AccountMappingRule(
                account_number="0800",
                debit_position=None,
                credit_position=subscribed_capital,
            ),
            AccountMappingRule(
                account_number="1600",
                debit_position=None,
                credit_position=trade_liabilities,
            ),
            AccountMappingRule(
                account_number="8400",
                debit_position=None,
                credit_position=net_sales,
            ),
            AccountMappingRule(
                account_number="4900",
                debit_position=other_cost,
                credit_position=None,
            ),
        ),
    )

    balances = (
        AccountBalance(
            account_number="1200",
            debit=Decimal("10000.00"),
        ),
        AccountBalance(
            account_number="0800",
            credit=Decimal("1000.00"),
        ),
        AccountBalance(
            account_number="1600",
            credit=Decimal("9000.00"),
        ),
        AccountBalance(
            account_number="8400",
            credit=Decimal("5000.00"),
        ),
        AccountBalance(
            account_number="4900",
            debit=Decimal("2000.00"),
        ),
    )

    statement_builder = FinancialStatementBuilder(
        AccountMapper(
            chart_of_accounts
        )
    )

    amounts = statement_builder.build(
        balances=balances,
        root_positions=(
            assets,
            liabilities,
            income_statement,
        ),
    )

    assert amounts[assets] == Decimal("10000.00")
    assert amounts[liabilities] == Decimal("10000.00")

    assert amounts[net_sales] == Decimal("5000.00")
    assert amounts[other_cost] == Decimal("2000.00")

    mapping_set = create_hgb_gaap_ci_mapping(
        assets=assets,
        liabilities=liabilities,
        income_statement=income_statement,
    )

    adapter = ArelleAdapter()

    try:
        taxonomy_model = adapter.model(
            entry_point_path
        )

        validation_result = mapping_set.validate(
            taxonomy_model
        )

        assert validation_result.is_valid

        mapper = TaxonomyMapper(
            mappings=mapping_set,
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
            end_date=date(2026, 12, 31),
        )

        duration_context = TaxonomyContext(
            entity_identifier="DE123456789",
            entity_scheme=TEST_ENTITY_SCHEME,
            period_type=TaxonomyPeriodType.DURATION,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )

        unit = TaxonomyUnit.eur()

        def collect(
            root: FinancialStatementPosition,
        ) -> tuple[FinancialStatementPosition, ...]:
            result = [root]

            for child in root.children:
                result.extend(
                    collect(child)
                )

            return tuple(result)

        balance_positions = set(
            collect(assets)
            + collect(liabilities)
        )

        income_positions = set(
            collect(income_statement)
        )

        balance_amounts = {
            position: amount
            for position, amount in amounts.items()
            if (
                position in balance_positions
                and mapping_set.for_position(position)
                is not None
            )
        }

        income_amounts = {
            position: amount
            for position, amount in amounts.items()
            if (
                position in income_positions
                and mapping_set.for_position(position)
                is not None
            )
        }

        balance_facts = fact_builder.build(
            amounts=balance_amounts,
            context=instant_context,
            unit=unit,
        )

        income_facts = fact_builder.build(
            amounts=income_amounts,
            context=duration_context,
            unit=unit,
        )

        facts = (
            balance_facts
            + income_facts
        )

        concepts_by_name = {
            fact.concept.name: fact
            for fact in facts
        }

        assert concepts_by_name[
            "bs.ass.currAss.cashEquiv"
        ].amount == Decimal("10000.00")

        assert concepts_by_name[
            "bs.eqLiab.equity.subscribed"
        ].amount == Decimal("1000.00")

        assert concepts_by_name[
            "bs.eqLiab.liab.trade"
        ].amount == Decimal("9000.00")

        assert concepts_by_name[
            (
                "is.netIncome.regular.operatingTC."
                "grossTradingProfit.totalOutput.netSales"
            )
        ].amount == Decimal("5000.00")

        assert concepts_by_name[
            "is.netIncome.regular.operatingTC.otherCost"
        ].amount == Decimal("2000.00")

        exporter = XbrlExporter()

        xml = exporter.export(
            contexts={
                "ctx-instant-2026": instant_context,
                "ctx-duration-2026": duration_context,
            },
            units={
                "EUR": unit,
            },
            facts=facts,
            taxonomy_namespace=taxonomy_namespace,
            entry_points=(
                entry_point,
            ),
        )

        instance_path = (
            tmp_path
            / "openbilanz-gaap-ci-pipeline-69.xbrl"
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

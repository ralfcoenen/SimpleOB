"""Anwendungsservice zur Erzeugung einer E-Bilanz."""

import os
from collections.abc import Mapping
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory

from openbilanz.accounting.balance_sheet import BalanceSheet
from openbilanz.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
from openbilanz.accounting.income_statement import IncomeStatement
from openbilanz.domain.accounting_account_roles import AccountingAccountRoles
from openbilanz.domain.company_master_data import (
    CompanyMasterData,
)
from openbilanz.domain.e_bilanz_account_detail import (
    EBilanzAccountDetail,
)
from openbilanz.domain.fiscal_year import FiscalYear
from openbilanz.domain.shareholder import Shareholder
from openbilanz.domain.vat_accounts import VatAccounts
from openbilanz.eric.bilanz_generation.fact_plan_resolver import (
    FactPlanResolver,
)
from openbilanz.eric.bilanz_generation.gaap_ci_6_9_account_detail_values import (
    GaapCi69AccountDetailValueBuilder,
)
from openbilanz.eric.bilanz_generation.gaap_ci_6_9_balance_sheet_values import (
    GaapCi69BalanceSheetValueBuilder,
)
from openbilanz.eric.bilanz_generation.gaap_ci_6_9_income_statement_values import (
    GaapCi69IncomeStatementValueBuilder,
)
from openbilanz.eric.bilanz_generation.gaap_ci_6_9_values import (
    GaapCi69ValueCalculator,
)
from openbilanz.eric.bilanz_generation.taxonomy_6_9 import (
    create_profile_6_9,
)
from openbilanz.eric.bilanz_generation.taxonomy_6_9_values import (
    Taxonomy69ValueBuilder,
)
from openbilanz.eric.bilanz_generation.taxonomy_6_9_xbrl_document_builder import (
    Taxonomy69XbrlDocumentBuilder,
)
from openbilanz.eric.bilanz_generation.hgbm_fixed_asset_schedule_builder import (
    HgbmFixedAssetScheduleBuilder,
)
from openbilanz.eric.bilanz_generation.tax_depreciation_reconciliation_builder import (
    TaxDepreciationReconciliationBuilder,
)
from openbilanz.eric.bilanz_generation.bvv_value_builder import (
    BvvValueBuilder,
)
from openbilanz.services.closing_service import ClosingService
from openbilanz.services.fixed_asset_schedule_service import (
    FixedAssetSchedulePosition,
)
from openbilanz.taxonomy.account_balance_builder import AccountBalanceBuilder
from openbilanz.taxonomy.arelle_adapter import (
    ArelleAdapter,
    ArelleValidationResult,
)
from openbilanz.taxonomy.concept import TaxonomyPeriodType
from openbilanz.taxonomy.concept_set import TaxonomyConceptSet
from openbilanz.taxonomy.context import TaxonomyContext
from openbilanz.taxonomy.e_bilanz_builder import EBilanzDocument
from openbilanz.taxonomy.entry_point import (
    TaxonomyEntryPoint,
)
from openbilanz.taxonomy.fixed_asset_schedule_builder import (
    FixedAssetScheduleBuilder,
)
from openbilanz.taxonomy.fact import TaxonomyFact
from openbilanz.taxonomy.fiscal_requirement_reader import (
    FiscalRequirementReader,
)
from openbilanz.taxonomy.gaap_ci_mandatory_fact_completer import (
    GaapCiMandatoryFactCompleter,
)
from openbilanz.taxonomy.gcd_company_data_mapper import (
    GcdCompanyDataMapper,
)
from openbilanz.taxonomy.gcd_fact_builder import GcdFactBuilder
from openbilanz.taxonomy.gcd_report_profile import GcdReportProfile
from openbilanz.taxonomy.gcd_shareholder import (
    GcdShareDivideKey,
    GcdShareholder,
    GcdShareholderLegalStatus,
)
from openbilanz.taxonomy.hgb_gaap_ci_mapping import (
    create_hgb_gaap_ci_mapping,
)
from openbilanz.taxonomy.mapper import TaxonomyMapper
from openbilanz.taxonomy.nil_fact import TaxonomyNilFact
from openbilanz.taxonomy.resolver import TaxonomyResolver
from openbilanz.taxonomy.taxonomy import (
    TaxonomyVersion,
    taxonomy_version_for,
)
from openbilanz.taxonomy.unit import TaxonomyUnit

BALANCE_SHEET_ROLE = (
    "http://www.xbrl.de/taxonomies/de-gaap-ci/role/balanceSheet"
)

INCOME_STATEMENT_ROLE = (
    "http://www.xbrl.de/taxonomies/de-gaap-ci/role/incomeStatement"
)


class EBilanzService:
    """Erzeugt eine E-Bilanz aus produktiven Anwendungsdaten."""

    def __init__(
        self,
        *,
        resolver: TaxonomyResolver,
        adapter: ArelleAdapter,
        company_data_mapper: GcdCompanyDataMapper,
        assets: FinancialStatementPosition,
        liabilities: FinancialStatementPosition,
        income_statement: FinancialStatementPosition,
    ) -> None:
        self._resolver = resolver
        self._adapter = adapter
        self._company_data_mapper = company_data_mapper
        self._assets = assets
        self._liabilities = liabilities
        self._income_statement = income_statement

    def build(
        self,
        *,
        master_data: CompanyMasterData,
        fiscal_year: FiscalYear,
        amounts: Mapping[
            FinancialStatementPosition,
            Decimal,
        ],
        income_statement: IncomeStatement,
        balance_sheet: BalanceSheet,
        vat_accounts: VatAccounts,
        account_roles: AccountingAccountRoles,
        entity_identifier: str,
        entity_scheme: str,
        account_taxonomy_concepts: dict[str, str] | None = None,
        previous_fiscal_year: FiscalYear | None = None,
        account_details: tuple[
            EBilanzAccountDetail,
            ...
        ] = (),
        fixed_asset_schedule: tuple[
            FixedAssetSchedulePosition,
            ...
        ] = (),
        shareholders: tuple[
            Shareholder,
            ...
        ] = (),
        current_depreciation_difference: Decimal = Decimal("0.00"),
        previous_depreciation_difference: Decimal = Decimal("0.00"),
        previous_hgb_equity: Decimal | None = None,
        contribution: Decimal = Decimal("0.00"),
        withdrawal_distribution: Decimal = Decimal("0.00"),
    ) -> EBilanzDocument:
        """Erzeugt die E-Bilanz-XBRL-Instanz über den Taxonomie-6.9-FactPlan."""

        mapping = self._company_data_mapper.map(
            master_data
        )

        version = taxonomy_version_for(
            fiscal_year
        )

        if version is not TaxonomyVersion.V6_9:
            raise ValueError(
                "Der ERiC-konforme E-Bilanz-Erzeugungspfad "
                "unterstützt derzeit ausschließlich Taxonomie 6.9."
            )

        gcd_path = self._resolver.gcd_entry_point(
            version
        )

        gaap_ci_path = (
            self._resolver.gaap_ci_fiscal_entry_point(
                version
            )
        )

        gcd_entry_point = (
            TaxonomyEntryPoint.from_file(
                gcd_path
            )
        )

        gaap_ci_entry_point = (
            TaxonomyEntryPoint.from_file(
                gaap_ci_path
            )
        )

        gcd_model = self._adapter.model(
            gcd_path
        )

        gaap_ci_model = self._adapter.model(
            gaap_ci_path
        )

        concepts = TaxonomyConceptSet(
            concepts=(
                gcd_model.concepts.concepts
                + gaap_ci_model.concepts.concepts
            )
        )

        net_income = (
            ClosingService()
            .calculate_net_income(
                income_statement=income_statement,
            )
        )

        gaap_ci_values = (
            GaapCi69ValueCalculator.calculate(
                income_statement=income_statement,
                net_income=net_income,
            )
        )

        profile = create_profile_6_9()

        report_profile = (
            GcdReportProfile.standard()
        )

        if account_details:
            report_profile = replace(
                report_profile,
                report_elements=(
                    *report_profile.report_elements,
                    (
                        "genInfo.report.id.reportElement."
                        "reportElements.KS"
                    ),
                ),
            )

        balance_sheet_values = (
            GaapCi69BalanceSheetValueBuilder.build(
                balance_sheet=balance_sheet,
                income_statement=(
                    income_statement.income_statement
                ),
            )
        )

        income_statement_values = (
            GaapCi69IncomeStatementValueBuilder.build(
                income_statement=income_statement,
                assets=balance_sheet.assets,
                liabilities=balance_sheet.liabilities,
                fixed_asset_schedule=fixed_asset_schedule,
            )
        )

        account_detail_values = (
            GaapCi69AccountDetailValueBuilder.build(
                account_details=account_details,
                tax_liability_accounts=(
                    vat_accounts.output_tax_7,
                    vat_accounts.output_tax_19,
                ),
                general_rate_sales_accounts=(
                    account_roles.general_rate_sales_accounts
                ),
                cash_accounts=(
                    account_roles.cash_accounts
                ),
                bank_accounts=(
                    account_roles.bank_accounts
                ),
                input_tax_receivable_accounts=(
                    vat_accounts.input_tax_7,
                    vat_accounts.input_tax_19,
                ),
                account_taxonomy_concepts=(
                    account_taxonomy_concepts
                ),
            )
        )

        taxonomy_mapper = TaxonomyMapper(
            create_hgb_gaap_ci_mapping(
                assets=self._assets,
                liabilities=self._liabilities,
                income_statement=self._income_statement,
            ),
            gaap_ci_model,
        )

        effective_fact_plan = profile.fact_plan

        explicit_taxonomy_concepts = (
            account_taxonomy_concepts or {}
        )

        extended_concepts: set[str] = set()

        for detail in account_details:
            target_concept_name = (
                explicit_taxonomy_concepts.get(
                    detail.account_number
                )
            )

            if target_concept_name is None:
                continue

            if target_concept_name in extended_concepts:
                continue

            target_concept = (
                gaap_ci_model.concepts.by_name(
                    target_concept_name
                )
            )

            if target_concept is None:
                raise ValueError(
                    "account taxonomy concept not found: "
                    f"{target_concept_name}"
                )

            parent_concept = (
                taxonomy_mapper.concept_for(
                    detail.position
                )
            )

            candidate_roles = {
                relation.role_uri
                for relation
                in gaap_ci_model.calculation.relations
                if (
                    relation.child_concept_id
                    == target_concept.concept_id
                )
            }

            has_expected_parent = any(
                any(
                    relation.parent_concept_id
                    == parent_concept.concept_id
                    for relation
                    in gaap_ci_model.calculation.parents_of(
                        target_concept.concept_id,
                        role_uri=role_uri,
                    )
                )
                for role_uri in candidate_roles
            )

            if not has_expected_parent:
                raise ValueError(
                    "account taxonomy concept is not a direct "
                    "calculation child of the mapped HGB concept: "
                    f"account={detail.account_number}, "
                    f"parent={parent_concept.name}, "
                    f"child={target_concept_name}"
                )

            if (
                effective_fact_plan.node_for(
                    target_concept_name
                )
                is None
            ):
                effective_fact_plan = (
                    effective_fact_plan.with_conditional_child(
                        parent_concept_name=(
                            parent_concept.name
                        ),
                        child_concept_name=(
                            target_concept_name
                        ),
                    )
                )

            extended_concepts.add(
                target_concept_name
            )

        fixed_asset_schedule_xbrl = (
            FixedAssetScheduleBuilder(
                taxonomy_model=gaap_ci_model,
                taxonomy_mapper=taxonomy_mapper,
            ).build(
                positions=fixed_asset_schedule,
                entity_identifier=entity_identifier,
                entity_scheme=entity_scheme,
                fiscal_year_start=fiscal_year.start_date,
                fiscal_year_end=fiscal_year.end_date,
            )
        )

        if fixed_asset_schedule_xbrl.facts:
            report_profile = replace(
                report_profile,
                report_elements=(
                    *report_profile.report_elements,
                    (
                        "genInfo.report.id.reportElement."
                        "reportElements.BAL"
                    ),
                ),
            )

        hgbm_fixed_asset_schedule_xbrl = None
        tax_reconciliation = None
        bvv_values = {}

        if (
            fixed_asset_schedule_xbrl.facts
            and (
                current_depreciation_difference != Decimal("0.00")
                or previous_depreciation_difference != Decimal("0.00")
            )
        ):
            hgbm_fixed_asset_schedule_xbrl = (
                HgbmFixedAssetScheduleBuilder.build(
                    commercial_contexts=(
                        fixed_asset_schedule_xbrl.contexts
                    ),
                    commercial_facts=(
                        fixed_asset_schedule_xbrl.facts
                    ),
                    commercial_nil_facts=(
                        fixed_asset_schedule_xbrl.nil_facts
                    ),
                    current_depreciation_difference=(
                        current_depreciation_difference
                    ),
                    previous_depreciation_difference=(
                        previous_depreciation_difference
                    ),
                )
            )

            current_book_value_difference = (
                -current_depreciation_difference
            )
            previous_book_value_difference = (
                -previous_depreciation_difference
            )

            tax_reconciliation = (
                TaxDepreciationReconciliationBuilder.build(
                    current_book_value_difference=(
                        current_book_value_difference
                    ),
                    previous_book_value_difference=(
                        previous_book_value_difference
                    ),
                )
            )

            if previous_hgb_equity is None:
                raise ValueError(
                    "Für den Betriebsvermögensvergleich fehlt "
                    "das HGB-Vorjahreseigenkapital."
                )

            current_hgb_equity = (
                balance_sheet_values.get(
                    ("bs.eqLiab.equity",)
                )
            )

            if current_hgb_equity is None:
                raise ValueError(
                    "Für den Betriebsvermögensvergleich fehlt "
                    "das aktuelle HGB-Eigenkapital."
                )

            bvv_values = BvvValueBuilder.build(
                current_hgb_equity=current_hgb_equity,
                previous_hgb_equity=previous_hgb_equity,
                current_book_value_difference=(
                    current_book_value_difference
                ),
                previous_book_value_difference=(
                    previous_book_value_difference
                ),
                contribution=contribution,
                withdrawal_distribution=(
                    withdrawal_distribution
                ),
            )

            report_profile = (
                report_profile.with_report_element(
                    "genInfo.report.id.reportElement."
                    "reportElements.BVV"
                )
            )

            report_profile = (
                report_profile.with_report_element(
                    "genInfo.report.id.reportElement."
                    "reportElements.STU"
                )
            )
        instant_context = TaxonomyContext(
            entity_identifier=entity_identifier,
            entity_scheme=entity_scheme,
            period_type=TaxonomyPeriodType.INSTANT,
            start_date=None,
            end_date=fiscal_year.end_date,
        )

        duration_context = TaxonomyContext(
            entity_identifier=entity_identifier,
            entity_scheme=entity_scheme,
            period_type=TaxonomyPeriodType.DURATION,
            start_date=fiscal_year.start_date,
            end_date=fiscal_year.end_date,
        )

        contexts_by_period_type = {
            TaxonomyPeriodType.INSTANT: instant_context,
            TaxonomyPeriodType.DURATION: duration_context,
        }

        for target_concept_name in extended_concepts:
            source_path = (
                target_concept_name,
            )

            if source_path not in account_detail_values:
                continue

            target_path = effective_fact_plan.path_for(
                target_concept_name
            )

            if target_path is None:
                raise ValueError(
                    "account taxonomy concept is missing "
                    "from effective fact plan: "
                    f"{target_concept_name}"
                )

            if target_path == source_path:
                continue

            amount = account_detail_values.pop(
                source_path
            )

            previous = account_detail_values.get(
                target_path
            )

            if previous is None:
                account_detail_values[
                    target_path
                ] = amount
            else:
                account_detail_values[
                    target_path
                ] = previous + amount

        values = Taxonomy69ValueBuilder.build(
            company_data=mapping.company_data,
            identifiers=mapping.identifiers,
            fiscal_year=fiscal_year,
            report_profile=report_profile,
            gaap_ci_values=gaap_ci_values,
            previous_fiscal_year=previous_fiscal_year,
        )

        values.update(
            balance_sheet_values
        )

        values.update(
            income_statement_values
        )

        values.update(
            account_detail_values
        )

        values.update(
            bvv_values
        )

        resolved_fact_plan = (
            FactPlanResolver.resolve(
                fact_plan=effective_fact_plan,
                concepts=concepts,
                contexts=contexts_by_period_type,
                values=values,
            )
        )

        existing_numeric_or_nil_facts: list[
            TaxonomyFact | TaxonomyNilFact
        ] = []

        def collect_numeric_or_nil_facts(
            node,
        ) -> None:
            if isinstance(
                node.fact,
                (
                    TaxonomyFact,
                    TaxonomyNilFact,
                ),
            ):
                existing_numeric_or_nil_facts.append(
                    node.fact
                )

            for child in node.children:
                collect_numeric_or_nil_facts(
                    child
                )

        for node in resolved_fact_plan.nodes:
            collect_numeric_or_nil_facts(
                node
            )

        requirements = FiscalRequirementReader(
            gaap_ci_entry_point
        ).requirements()

        mandatory_nil_facts = (
            GaapCiMandatoryFactCompleter(
                taxonomy_model=gaap_ci_model
            ).build_missing_nil_facts(
                requirements=requirements,
                existing_facts=tuple(
                    existing_numeric_or_nil_facts
                ),
                instant_context=instant_context,
                duration_context=duration_context,
                unit=TaxonomyUnit.eur(),
                active_report_element_roles=(
                    BALANCE_SHEET_ROLE,
                    INCOME_STATEMENT_ROLE,
                ),
                excluded_concept_prefixes=(
                    "is.netIncome.regular.operatingCOGS",
                ),
            )
        )

        account_balance_builder = AccountBalanceBuilder(
            taxonomy_model=gaap_ci_model,
            taxonomy_mapper=taxonomy_mapper,
        )

        account_balances = tuple(
            account_balance_builder.build(
                detail=detail,
                context=duration_context,
            )
            for detail in account_details
        )

        gcd_shareholders = tuple(
            self._map_shareholder(
                shareholder
            )
            for shareholder in shareholders
        )

        gcd_fact_builder = GcdFactBuilder()

        shareholder_tuples = tuple(
            gcd_fact_builder.shareholder(
                shareholder=shareholder,
                taxonomy_model=gcd_model,
                context=duration_context,
            )
            for shareholder in gcd_shareholders
        )

        year = fiscal_year.end_date.year

        contexts = {
            f"ctx-instant-{year}": instant_context,
            f"ctx-duration-{year}": duration_context,
            **fixed_asset_schedule_xbrl.contexts,
        }

        if hgbm_fixed_asset_schedule_xbrl is not None:
            contexts.update(
                hgbm_fixed_asset_schedule_xbrl.contexts
            )

        units = {
            "EUR": TaxonomyUnit.eur(),
            "PURE": TaxonomyUnit.pure(),
        }

        additional_facts = list(
            fixed_asset_schedule_xbrl.facts
        )

        additional_nil_facts = list(
            fixed_asset_schedule_xbrl.nil_facts
        )

        if hgbm_fixed_asset_schedule_xbrl is not None:
            additional_facts.extend(
                hgbm_fixed_asset_schedule_xbrl.facts
            )

            additional_nil_facts.extend(
                hgbm_fixed_asset_schedule_xbrl.nil_facts
            )

        xml = (
            Taxonomy69XbrlDocumentBuilder()
            .build_xml(
                resolved_fact_plan=resolved_fact_plan,
                contexts=contexts,
                units=units,
                entry_points=(
                    gcd_entry_point,
                    gaap_ci_entry_point,
                ),
                shareholders=shareholder_tuples,
                nil_facts=(
                    *mandatory_nil_facts,
                    *additional_nil_facts,
                ),
                account_balances=account_balances,
                facts=tuple(
                    additional_facts
                ),
                tax_reconciliation=tax_reconciliation,
                tax_reconciliation_context_id=(
                    f"ctx-duration-{year}"
                    if tax_reconciliation is not None
                    else None
                ),
                tax_reconciliation_unit_id=(
                    "EUR"
                    if tax_reconciliation is not None
                    else None
                ),            )
        )

        return EBilanzDocument(
            xml=xml
        )

    @staticmethod
    def _map_shareholder(
        shareholder: Shareholder,
    ) -> GcdShareholder:
        """Überführt produktive Gesellschafterdaten in GCD-Daten."""

        if not isinstance(
            shareholder,
            Shareholder,
        ):
            raise TypeError(
                "shareholder must be a Shareholder"
            )

        return GcdShareholder(
            name=shareholder.name,
            first_name=(
                shareholder.first_name
                or None
            ),
            shareholder_id=(
                shareholder.shareholder_number
            ),
            tax_number=(
                shareholder.tax_number
                or None
            ),
            tax_id=(
                shareholder.tax_id
                or None
            ),
            wid=(
                shareholder.wid
                or None
            ),
            legal_status=(
                GcdShareholderLegalStatus(
                    shareholder.legal_status
                )
            ),
            share_divide_key=(
                GcdShareDivideKey(
                    numerator=(
                        shareholder.share_numerator
                    ),
                    denominator=(
                        shareholder.share_denominator
                    ),
                )
            ),
        )

    def validate(
        self,
        document: EBilanzDocument,
        *,
        fiscal_year: FiscalYear,
    ) -> ArelleValidationResult:
        """Validiert eine erzeugte E-Bilanz mit Arelle."""

        if not isinstance(
            document,
            EBilanzDocument,
        ):
            raise TypeError(
                "document muss ein EBilanzDocument sein."
            )

        if not isinstance(
            fiscal_year,
            FiscalYear,
        ):
            raise TypeError(
                "fiscal_year muss ein FiscalYear sein."
            )

        version = taxonomy_version_for(
            fiscal_year
        )

        gcd_path = self._resolver.gcd_entry_point(
            version
        )

        gaap_ci_path = (
            self._resolver.gaap_ci_fiscal_entry_point(
                version
            )
        )

        gcd_entry_point = TaxonomyEntryPoint.from_file(
            gcd_path
        )

        gaap_ci_entry_point = TaxonomyEntryPoint.from_file(
            gaap_ci_path
        )

        taxonomy_root = Path(
            os.path.commonpath(
                (
                    gcd_path.parent,
                    gaap_ci_path.parent,
                )
            )
        )

        with TemporaryDirectory(
            prefix="openbilanz-e-bilanz-",
            dir=taxonomy_root,
        ) as temporary_directory:
            temporary_directory_path = Path(
                temporary_directory
            )

            gcd_relative_path = Path(
                os.path.relpath(
                    gcd_path,
                    temporary_directory_path,
                )
            ).as_posix()

            gaap_ci_relative_path = Path(
                os.path.relpath(
                    gaap_ci_path,
                    temporary_directory_path,
                )
            ).as_posix()

            validation_xml = document.xml

            validation_xml = validation_xml.replace(
                gcd_entry_point.schema_ref_uri,
                gcd_relative_path,
            )

            validation_xml = validation_xml.replace(
                gaap_ci_entry_point.schema_ref_uri,
                gaap_ci_relative_path,
            )

            instance_path = (
                temporary_directory_path
                / "openbilanz-e-bilanz.xbrl"
            )

            instance_path.write_text(
                validation_xml,
                encoding="utf-8",
            )

            return self._adapter.validate(
                instance_path
            )

"""Orchestrierung einer vollständigen E-Bilanz aus GCD und GAAP-CI."""

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal

from openbilanz.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
from openbilanz.domain.e_bilanz_account_detail import (
    EBilanzAccountDetail,
)
from openbilanz.domain.fiscal_year import FiscalYear
from openbilanz.exporter.xbrl_export import XbrlExporter
from openbilanz.taxonomy.account_balance_builder import (
    AccountBalanceBuilder,
)
from openbilanz.taxonomy.entry_point import TaxonomyEntryPoint
from openbilanz.taxonomy.gaap_ci_statement_builder import (
    GaapCiStatement,
    GaapCiStatementBuilder,
)
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
from openbilanz.taxonomy.gcd_report_profile import GcdReportProfile
from openbilanz.taxonomy.gcd_shareholder import GcdShareholder
from openbilanz.taxonomy.hgb_gaap_ci_mapping import (
    create_hgb_gaap_ci_mapping,
)
from openbilanz.taxonomy.mapper import TaxonomyMapper
from openbilanz.taxonomy.model import TaxonomyModel
from openbilanz.taxonomy.unit import TaxonomyUnit


@dataclass(frozen=True, slots=True)
class EBilanzDocument:
    """Ergebnis der vollständigen E-Bilanz-Erzeugung."""

    xml: str
    gaap_ci_statement: GaapCiStatement


class EBilanzBuilder:
    """Erzeugt eine vollständige E-Bilanz aus GCD und HGB-Abschluss."""

    def __init__(
        self,
        *,
        gcd_model: TaxonomyModel,
        gaap_ci_model: TaxonomyModel,
        gcd_entry_point: TaxonomyEntryPoint,
        gaap_ci_entry_point: TaxonomyEntryPoint,
        gcd_namespace: str,
        gaap_ci_namespace: str,
        assets: FinancialStatementPosition,
        liabilities: FinancialStatementPosition,
        income_statement: FinancialStatementPosition,
    ) -> None:
        self._gcd_model = gcd_model
        self._gaap_ci_model = gaap_ci_model
        self._gcd_entry_point = gcd_entry_point
        self._gaap_ci_entry_point = gaap_ci_entry_point
        self._gcd_namespace = gcd_namespace
        self._gaap_ci_namespace = gaap_ci_namespace
        self._assets = assets
        self._liabilities = liabilities
        self._income_statement = income_statement

    def build(
        self,
        *,
        company_data: GcdCompanyData,
        fiscal_year: FiscalYear,
        amounts: Mapping[
            FinancialStatementPosition,
            Decimal,
        ],
        entity_identifier: str,
        entity_scheme: str,
        previous_fiscal_year: FiscalYear | None = None,
        identifiers: GcdCompanyIdentifiers | None = None,
        shareholders: tuple[GcdShareholder, ...] = (),
        domestic_branch_types: tuple[
            GcdDomesticBranchOfForeignCompanyType,
            ...
        ] = (),
        taxable_purpose_business_types: tuple[
            GcdEntityWithTaxablePurposeBusinessType,
            ...
        ] = (),
        account_details: tuple[
            EBilanzAccountDetail,
            ...
        ] = (),
        report_profile: GcdReportProfile | None = None,
    ) -> EBilanzDocument:
        """Erzeugt die vollständige E-Bilanz-XBRL-Instanz."""

        gaap_builder = GaapCiStatementBuilder(
            taxonomy_model=self._gaap_ci_model,
            assets=self._assets,
            liabilities=self._liabilities,
            income_statement=self._income_statement,
        )

        gaap_statement = gaap_builder.build(
            amounts=amounts,
            entity_identifier=entity_identifier,
            entity_scheme=entity_scheme,
            fiscal_year_start=fiscal_year.start_date,
            fiscal_year_end=fiscal_year.end_date,
        )

        duration_context = gaap_statement.duration_context

        taxonomy_mappings = create_hgb_gaap_ci_mapping(
            assets=self._assets,
            liabilities=self._liabilities,
            income_statement=self._income_statement,
        )

        taxonomy_mapper = TaxonomyMapper(
            mappings=taxonomy_mappings,
            taxonomy_model=self._gaap_ci_model,
        )

        account_balance_builder = AccountBalanceBuilder(
            taxonomy_model=self._gaap_ci_model,
            taxonomy_mapper=taxonomy_mapper,
        )

        account_balances = tuple(
            account_balance_builder.build(
                detail=detail,
                context=duration_context,
            )
            for detail in account_details
        )

        gcd_builder = GcdFactBuilder()

        gcd_facts = (
            gcd_builder.company_facts(
                data=company_data,
                taxonomy_model=self._gcd_model,
                context=duration_context,
            )
            + gcd_builder.fiscal_year_facts(
                fiscal_year=fiscal_year,
                previous_fiscal_year=previous_fiscal_year,
                taxonomy_model=self._gcd_model,
                context=duration_context,
            )
        )

        profile = (
            report_profile
            if report_profile is not None
            else GcdReportProfile.standard()
        )

        profile_facts = gcd_builder.report_profile_facts(
            profile=profile,
            taxonomy_model=self._gcd_model,
            context=duration_context,
        )

        report_element = gcd_builder.report_element(
            profile=profile,
            taxonomy_model=self._gcd_model,
            context=duration_context,
        )

        company_id_nos = (
            ()
            if identifiers is None
            else (
                gcd_builder.company_id_no(
                    identifiers=identifiers,
                    taxonomy_model=self._gcd_model,
                    context=duration_context,
                ),
            )
        )

        shareholder_tuples = tuple(
            gcd_builder.shareholder(
                shareholder=shareholder,
                taxonomy_model=self._gcd_model,
                context=duration_context,
            )
            for shareholder in shareholders
        )

        domestic_branches = tuple(
            gcd_builder.domestic_branch_of_foreign_company(
                branch_type=branch_type,
                taxonomy_model=self._gcd_model,
                context=duration_context,
            )
            for branch_type in domestic_branch_types
        )

        taxable_purpose_businesses = tuple(
            gcd_builder.entity_with_taxable_purpose_business(
                business_type=business_type,
                taxonomy_model=self._gcd_model,
                context=duration_context,
            )
            for business_type in taxable_purpose_business_types
        )

        facts = (
            gcd_facts
            + profile_facts
            + gaap_statement.facts
        )

        pure_unit = TaxonomyUnit.pure()

        exporter = XbrlExporter()

        year = fiscal_year.end_date.year

        xml = exporter.export(
            contexts={
                f"ctx-instant-{year}":
                    gaap_statement.instant_context,
                f"ctx-duration-{year}":
                    gaap_statement.duration_context,
            },
            units={
                "EUR": gaap_statement.unit,
                "PURE": pure_unit,
            },
            facts=facts,
            account_balances=account_balances,
            report_elements=(
                report_element,
            ),
            taxonomy_namespace=self._gaap_ci_namespace,
            taxonomy_namespaces={
                "de-gcd": self._gcd_namespace,
                "de-gaap-ci": self._gaap_ci_namespace,
            },
            entry_points=(
                self._gcd_entry_point,
                self._gaap_ci_entry_point,
            ),
            company_id_nos=company_id_nos,
            shareholders=shareholder_tuples,
            domestic_branches=domestic_branches,
            taxable_purpose_businesses=(
                taxable_purpose_businesses
            ),
        )

        return EBilanzDocument(
            xml=xml,
            gaap_ci_statement=gaap_statement,
        )

"""Fachliche Werte für den ERiC-Fact-Plan der Taxonomie 6.9."""

from __future__ import annotations

from openbilanz.domain.fiscal_year import FiscalYear
from openbilanz.eric.bilanz_generation.fact_plan_resolver import (
    FactPlanPath,
    FactPlanValue,
)
from openbilanz.eric.bilanz_generation.gaap_ci_6_9_values import (
    GaapCi69Values,
)
from openbilanz.taxonomy.gcd_company_data import GcdCompanyData
from openbilanz.taxonomy.gcd_company_identifiers import (
    GcdCompanyIdentifiers,
)
from openbilanz.taxonomy.gcd_report_profile import GcdReportProfile


class Taxonomy69ValueBuilder:
    """Übersetzt SimpleOB-Fachdaten in FactPlan-Werte für Taxonomie 6.9."""

    _REPORT_PROFILE_VALUES = {
        "genInfo.report.id.reportStatus.reportStatus.E": (
            "endgültig"
        ),
        "genInfo.report.id.revisionStatus.revisionStatus.E": (
            "erstmalig"
        ),
        "genInfo.report.id.statementType.statementType.E": (
            "Jahresabschluss"
        ),
        (
            "genInfo.report.id.accountingStandard."
            "accountingStandard.HGBM"
        ): "deutsches Handelsrecht",
        "genInfo.report.id.specialAccountingStandard.K": (
            "Kerntaxonomie"
        ),
        (
            "genInfo.report.id.incomeStatementFormat."
            "incomeStatementFormat.GKV"
        ): "Gesamtkostenverfahren",
        (
            "genInfo.report.id.consolidationRange."
            "consolidationRange.EA"
        ): "Einzelabschluss",
        "genInfo.company.id.incomeClassification.trade": (
            "Einkünfte aus Gewerbebetrieb"
        ),
    }

    _REPORT_ELEMENT_VALUES = {
        (
            "genInfo.report.id.reportElement."
            "reportElements.B"
        ): "Bilanz",
        (
            "genInfo.report.id.reportElement."
            "reportElements.GuV"
        ): "GuV",
        (
            "genInfo.report.id.reportElement."
            "reportElements.KS"
        ): "Kontennachweis",
        (
            "genInfo.report.id.reportElement."
            "reportElements.BAL"
        ): "Anlagenspiegel",
        (
            "genInfo.report.id.reportElement."
            "reportElements.BVV"
        ): "Steuerlicher Betriebsvermögensvergleich",
        (
            "genInfo.report.id.reportElement."
                "reportElements.STU"
        ): "Steuerliche Überleitungsrechnung",
    }

    @classmethod
    def build(
        cls,
        *,
        company_data: GcdCompanyData,
        identifiers: GcdCompanyIdentifiers,
        fiscal_year: FiscalYear,
        report_profile: GcdReportProfile,
        gaap_ci_values: GaapCi69Values,
        previous_fiscal_year: FiscalYear | None = None,
    ) -> dict[FactPlanPath, FactPlanValue]:
        """Erzeugt die Werte für den unterstützten 6.9-Standardfall."""

        cls._validate_inputs(
            company_data=company_data,
            identifiers=identifiers,
            fiscal_year=fiscal_year,
            report_profile=report_profile,
            gaap_ci_values=gaap_ci_values,
            previous_fiscal_year=previous_fiscal_year,
        )

        values: dict[
            FactPlanPath,
            FactPlanValue,
        ] = {}

        cls._add_report_profile_values(
            values=values,
            report_profile=report_profile,
        )

        cls._add_report_element_values(
            values=values,
            report_profile=report_profile,
        )

        cls._add_company_values(
            values=values,
            company_data=company_data,
            identifiers=identifiers,
            report_profile=report_profile,
        )

        cls._add_fiscal_year_values(
            values=values,
            fiscal_year=fiscal_year,
            previous_fiscal_year=previous_fiscal_year,
        )

        values[
            (
                "genInfo.report.id."
                "incomeStatementendswithBalProfit",
            )
        ] = "false"

        cls._add_gaap_ci_values(
            values=values,
            gaap_ci_values=gaap_ci_values,
        )

        return values

    @classmethod
    def _add_report_profile_values(
        cls,
        *,
        values: dict[FactPlanPath, FactPlanValue],
        report_profile: GcdReportProfile,
    ) -> None:
        profile_concepts = (
            (
                "genInfo.report.id.reportStatus",
                report_profile.report_status,
            ),
            (
                "genInfo.report.id.revisionStatus",
                report_profile.revision_status,
            ),
            (
                "genInfo.report.id.statementType",
                report_profile.statement_type,
            ),
            (
                "genInfo.report.id.accountingStandard",
                report_profile.accounting_standard,
            ),
            (
                "genInfo.report.id.specialAccountingStandard",
                report_profile.special_accounting_standard,
            ),
            (
                "genInfo.report.id.incomeStatementFormat",
                report_profile.income_statement_format,
            ),
            (
                "genInfo.report.id.consolidationRange",
                report_profile.consolidation_range,
            ),
            (
                "genInfo.company.id.incomeClassification",
                report_profile.income_classification,
            ),
        )

        for parent_name, concept_name in profile_concepts:
            try:
                value = cls._REPORT_PROFILE_VALUES[
                    concept_name
                ]
            except KeyError as exc:
                raise ValueError(
                    "unsupported Taxonomy 6.9 report profile "
                    f"concept: {concept_name}"
                ) from exc

            values[
                (
                    parent_name,
                    concept_name,
                )
            ] = value

    @classmethod
    def _add_report_element_values(
        cls,
        *,
        values: dict[FactPlanPath, FactPlanValue],
        report_profile: GcdReportProfile,
    ) -> None:
        parent_name = "genInfo.report.id.reportElement"

        for concept_name in report_profile.report_elements:
            try:
                value = cls._REPORT_ELEMENT_VALUES[
                    concept_name
                ]
            except KeyError as exc:
                raise ValueError(
                    "unsupported Taxonomy 6.9 report element: "
                    f"{concept_name}"
                ) from exc

            values[
                (
                    parent_name,
                    concept_name,
                )
            ] = value

    @staticmethod
    def _add_company_values(
        *,
        values: dict[FactPlanPath, FactPlanValue],
        company_data: GcdCompanyData,
        identifiers: GcdCompanyIdentifiers,
        report_profile: GcdReportProfile,
    ) -> None:
        values[
            ("genInfo.company.id.name",)
        ] = company_data.company.name

        values[
            ("genInfo.company.id.location.street",)
        ] = company_data.street

        values[
            ("genInfo.company.id.location.houseNo",)
        ] = company_data.house_number

        values[
            ("genInfo.company.id.location.zipCode",)
        ] = company_data.postal_code

        values[
            ("genInfo.company.id.location.city",)
        ] = company_data.city

        values[
            ("genInfo.company.id.location.country",)
        ] = company_data.country

        if company_data.business.strip():
            values[
                ("genInfo.company.id.business",)
            ] = company_data.business

        id_no_parent = "genInfo.company.id.idNo"

        values[
            (
                id_no_parent,
                (
                    "genInfo.company.id.idNo."
                    "type.companyId.ST13"
                ),
            )
        ] = identifiers.tax_number_13

        if identifiers.tax_id is not None:
            values[
                (
                    id_no_parent,
                    (
                        "genInfo.company.id.idNo."
                        "type.companyId.STID"
                    ),
                )
            ] = identifiers.tax_id

        if identifiers.tax_economic_id is not None:
            values[
                (
                    id_no_parent,
                    (
                        "genInfo.company.id.idNo."
                        "type.companyId.STWID"
                    ),
                )
            ] = identifiers.tax_economic_id

        if identifiers.bf4 is not None:
            values[
                (
                    id_no_parent,
                    (
                        "genInfo.company.id.idNo."
                        "type.companyId.BF4"
                    ),
                )
            ] = identifiers.bf4

        legal_status_concept = (
            report_profile.legal_status_for(
                company_data.legal_form
            )
        )

        values[
            (
                "genInfo.company.id.legalStatus",
                legal_status_concept,
            )
        ] = company_data.legal_form

    @staticmethod
    def _add_fiscal_year_values(
        *,
        values: dict[FactPlanPath, FactPlanValue],
        fiscal_year: FiscalYear,
        previous_fiscal_year: FiscalYear | None,
    ) -> None:
        start_date = fiscal_year.start_date.isoformat()
        end_date = fiscal_year.end_date.isoformat()

        values[
            ("genInfo.report.period.reportPeriodBegin",)
        ] = start_date

        values[
            ("genInfo.report.period.reportPeriodEnd",)
        ] = end_date

        values[
            ("genInfo.report.period.fiscalYearBegin",)
        ] = start_date

        values[
            ("genInfo.report.period.fiscalYearEnd",)
        ] = end_date

        values[
            ("genInfo.report.period.balSheetClosingDate",)
        ] = end_date

        if previous_fiscal_year is None:
            return

        previous_start_date = (
            previous_fiscal_year.start_date.isoformat()
        )
        previous_end_date = (
            previous_fiscal_year.end_date.isoformat()
        )

        values[
            ("genInfo.report.period.fiscalPreviousYearBegin",)
        ] = previous_start_date

        values[
            ("genInfo.report.period.fiscalPreviousYearEnd",)
        ] = previous_end_date

        values[
            (
                "genInfo.report.period."
                "balSheetClosingDatePreviousYear",
            )
        ] = previous_end_date

    @staticmethod
    def _add_gaap_ci_values(
        *,
        values: dict[FactPlanPath, FactPlanValue],
        gaap_ci_values: GaapCi69Values,
    ) -> None:
        values[
            ("is.netIncome",)
        ] = gaap_ci_values.net_income

        values[
            ("is.netIncome.eat",)
        ] = gaap_ci_values.earnings_after_taxes

        values[
            ("is.netIncome.regular.operatingTC",)
        ] = gaap_ci_values.operating_total_cost

        values[
            (
                (
                    "is.netIncome.regular.operatingTC."
                    "grossTradingProfit"
                ),
            )
        ] = gaap_ci_values.gross_trading_profit

    @staticmethod
    def _validate_inputs(
        *,
        company_data: GcdCompanyData,
        identifiers: GcdCompanyIdentifiers,
        fiscal_year: FiscalYear,
        report_profile: GcdReportProfile,
        gaap_ci_values: GaapCi69Values,
        previous_fiscal_year: FiscalYear | None,
    ) -> None:
        if not isinstance(
            company_data,
            GcdCompanyData,
        ):
            raise TypeError(
                "company_data must be a GcdCompanyData"
            )

        if not isinstance(
            identifiers,
            GcdCompanyIdentifiers,
        ):
            raise TypeError(
                "identifiers must be a GcdCompanyIdentifiers"
            )

        if not isinstance(
            fiscal_year,
            FiscalYear,
        ):
            raise TypeError(
                "fiscal_year must be a FiscalYear"
            )

        if (
            previous_fiscal_year is not None
            and not isinstance(
                previous_fiscal_year,
                FiscalYear,
            )
        ):
            raise TypeError(
                "previous_fiscal_year must be a FiscalYear or None"
            )

        if not isinstance(
            report_profile,
            GcdReportProfile,
        ):
            raise TypeError(
                "report_profile must be a GcdReportProfile"
            )

        if not isinstance(
            gaap_ci_values,
            GaapCi69Values,
        ):
            raise TypeError(
                "gaap_ci_values must be a GaapCi69Values"
            )

        if (
            identifiers.tax_number_13
            != company_data.tax_number
        ):
            raise ValueError(
                "company tax numbers do not match"
            )

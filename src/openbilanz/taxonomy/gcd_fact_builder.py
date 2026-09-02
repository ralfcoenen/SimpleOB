"""Aufbau von GCD-Werten aus Unternehmensstammdaten."""

from datetime import date
from decimal import Decimal

from openbilanz.domain.fiscal_year import FiscalYear
from openbilanz.taxonomy.context import TaxonomyContext
from openbilanz.taxonomy.fact import TaxonomyFact
from openbilanz.taxonomy.gcd_company_data import GcdCompanyData
from openbilanz.taxonomy.gcd_company_id_no import (
    GcdCompanyIdNo,
)
from openbilanz.taxonomy.gcd_company_identifiers import (
    GcdCompanyIdentifiers,
)
from openbilanz.taxonomy.gcd_domestic_branch_of_foreign_company import (
    GcdDomesticBranchOfForeignCompany,
    GcdDomesticBranchOfForeignCompanyType,
)
from openbilanz.taxonomy.gcd_entity_with_taxable_purpose_business import (
    GcdEntityWithTaxablePurposeBusiness,
    GcdEntityWithTaxablePurposeBusinessType,
)
from openbilanz.taxonomy.gcd_report_data import (
    GcdReportData,
)
from openbilanz.taxonomy.gcd_report_element import (
    GcdReportElement,
)
from openbilanz.taxonomy.gcd_report_profile import (
    GcdReportProfile,
)
from openbilanz.taxonomy.gcd_shareholder import (
    GcdShareholder,
)
from openbilanz.taxonomy.gcd_shareholder_tuple import (
    GcdShareDivideKeyTuple,
    GcdShareholderLegalStatusTuple,
    GcdShareholderTuple,
)
from openbilanz.taxonomy.model import TaxonomyModel
from openbilanz.taxonomy.nil_fact import TaxonomyNilFact
from openbilanz.taxonomy.text_fact import TaxonomyTextFact
from openbilanz.taxonomy.unit import TaxonomyUnit


class GcdFactBuilder:
    """Erzeugt GCD-Werte aus fachlichen Stammdaten."""

    def company_values(
        self,
        data: GcdCompanyData,
    ) -> dict[str, str]:
        """Liefert die GCD-Werte für Unternehmensstammdaten."""

        if not isinstance(
            data,
            GcdCompanyData,
        ):
            raise TypeError(
                "data must be a GcdCompanyData"
            )

        profile = GcdReportProfile.standard()

        legal_status_concept = profile.legal_status_for(
            data.legal_form
        )

        values = {
            "genInfo.company.id.name": (
                data.company.name
            ),
            "genInfo.company.id.idNo.type.companyId.ST13": (
                data.tax_number
            ),
            legal_status_concept: (
                data.legal_form
            ),
        }

        optional_values = {
            "genInfo.company.id.location.street": (
                data.street
            ),
            "genInfo.company.id.location.houseNo": (
                data.house_number
            ),
            "genInfo.company.id.location.zipCode": (
                data.postal_code
            ),
            "genInfo.company.id.location.city": (
                data.city
            ),
            "genInfo.company.id.location.country": (
                data.country
            ),
            "genInfo.company.id.business": (
                data.business
            ),
        }

        values.update(
            {
                concept_name: value
                for concept_name, value in optional_values.items()
                if value.strip()
            }
        )

        return values

    def fiscal_year_values(
        self,
        fiscal_year: FiscalYear,
        *,
        previous_fiscal_year: FiscalYear | None = None,
    ) -> dict[str, date]:
        """Liefert die GCD-Werte für das Wirtschaftsjahr."""

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

        values = {
            "genInfo.report.period.fiscalYearBegin": (
                fiscal_year.start_date
            ),
            "genInfo.report.period.fiscalYearEnd": (
                fiscal_year.end_date
            ),
            "genInfo.report.period.balSheetClosingDate": (
                fiscal_year.end_date
            ),
        }

        if previous_fiscal_year is not None:
            values.update(
                {
                    "genInfo.report.period.fiscalPreviousYearBegin": (
                        previous_fiscal_year.start_date
                    ),
                    "genInfo.report.period.fiscalPreviousYearEnd": (
                        previous_fiscal_year.end_date
                    ),
                    "genInfo.report.period.balSheetClosingDatePreviousYear": (
                        previous_fiscal_year.end_date
                    ),
                }
            )

        return values

    def company_facts(
        self,
        *,
        data: GcdCompanyData,
        taxonomy_model: TaxonomyModel,
        context: TaxonomyContext,
    ) -> tuple[TaxonomyTextFact, ...]:
        """Erzeugt GCD-Text-Facts für Unternehmensstammdaten."""

        if not isinstance(
            data,
            GcdCompanyData,
        ):
            raise TypeError(
                "data must be a GcdCompanyData"
            )

        if not isinstance(
            taxonomy_model,
            TaxonomyModel,
        ):
            raise TypeError(
                "taxonomy_model must be a TaxonomyModel"
            )

        if not isinstance(
            context,
            TaxonomyContext,
        ):
            raise TypeError(
                "context must be a TaxonomyContext"
            )

        values = self.company_values(
            data
        )

        concepts_by_name = {
            concept.name: concept
            for concept in taxonomy_model.concepts.concepts
        }

        facts: list[TaxonomyTextFact] = []

        for concept_name, value in values.items():
            concept = concepts_by_name.get(
                concept_name
            )

            if concept is None:
                raise ValueError(
                    "GCD taxonomy concept not found: "
                    f"{concept_name}"
                )

            facts.append(
                TaxonomyTextFact(
                    concept=concept,
                    value=value,
                    context=context,
                )
            )

        return tuple(facts)

    def fiscal_year_facts(
        self,
        *,
        fiscal_year: FiscalYear,
        taxonomy_model: TaxonomyModel,
        context: TaxonomyContext,
        previous_fiscal_year: FiscalYear | None = None,
    ) -> tuple[
        TaxonomyTextFact | TaxonomyNilFact,
        ...,
    ]:
        """Erzeugt GCD-Facts für das Wirtschaftsjahr."""

        if not isinstance(
            fiscal_year,
            FiscalYear,
        ):
            raise TypeError(
                "fiscal_year must be a FiscalYear"
            )

        if not isinstance(
            taxonomy_model,
            TaxonomyModel,
        ):
            raise TypeError(
                "taxonomy_model must be a TaxonomyModel"
            )

        if not isinstance(
            context,
            TaxonomyContext,
        ):
            raise TypeError(
                "context must be a TaxonomyContext"
            )

        values = self.fiscal_year_values(
            fiscal_year,
            previous_fiscal_year=previous_fiscal_year,
        )

        concepts_by_name = {
            concept.name: concept
            for concept in taxonomy_model.concepts.concepts
        }

        facts: list[
            TaxonomyTextFact | TaxonomyNilFact
        ] = []

        for concept_name, value in values.items():
            concept = concepts_by_name.get(
                concept_name
            )

            if concept is None:
                raise ValueError(
                    "GCD taxonomy concept not found: "
                    f"{concept_name}"
                )

            facts.append(
                TaxonomyTextFact(
                    concept=concept,
                    value=value.isoformat(),
                    context=context,
                )
            )

        if previous_fiscal_year is None:
            previous_year_concept_names = (
                "genInfo.report.period.fiscalPreviousYearBegin",
                "genInfo.report.period.fiscalPreviousYearEnd",
                "genInfo.report.period.balSheetClosingDatePreviousYear",
            )

            for concept_name in previous_year_concept_names:
                concept = concepts_by_name.get(
                    concept_name
                )

                if concept is None:
                    raise ValueError(
                        "GCD taxonomy concept not found: "
                        f"{concept_name}"
                    )

                facts.append(
                    TaxonomyNilFact(
                        concept=concept,
                        context=context,
                        unit=None,
                    )
                )

        return tuple(facts)

    def report_profile_facts(
        self,
        *,
        profile: GcdReportProfile,
        taxonomy_model: TaxonomyModel,
        context: TaxonomyContext,
    ) -> tuple[TaxonomyTextFact, ...]:
        """Erzeugt grundlegende GCD-Facts des Berichtsprofils."""

        if not isinstance(
            profile,
            GcdReportProfile,
        ):
            raise TypeError(
                "profile must be a GcdReportProfile"
            )

        if not isinstance(
            taxonomy_model,
            TaxonomyModel,
        ):
            raise TypeError(
                "taxonomy_model must be a TaxonomyModel"
            )

        if not isinstance(
            context,
            TaxonomyContext,
        ):
            raise TypeError(
                "context must be a TaxonomyContext"
            )

        concepts_by_name = {
            concept.name: concept
            for concept in taxonomy_model.concepts.concepts
        }

        values = (
            (
                profile.report_status,
                "endgültig",
            ),
            (
                profile.revision_status,
                "erstmalig",
            ),
            (
                profile.statement_type,
                "Jahresabschluss",
            ),
            (
                profile.accounting_standard,
                "deutsches Handelsrecht",
            ),
            (
                profile.special_accounting_standard,
                "Kerntaxonomie",
            ),
            (
                profile.income_statement_format,
                "Gesamtkostenverfahren",
            ),
            (
                profile.consolidation_range,
                "Einzelabschluss",
            ),
            (
                profile.income_classification,
                "Einkünfte aus Gewerbebetrieb",
            ),
        )

        facts: list[TaxonomyTextFact] = []

        for concept_name, value in values:
            concept = concepts_by_name.get(
                concept_name
            )

            if concept is None:
                raise ValueError(
                    "GCD taxonomy concept not found: "
                    f"{concept_name}"
                )

            facts.append(
                TaxonomyTextFact(
                    concept=concept,
                    value=value,
                    context=context,
                )
            )

        return tuple(facts)

    def report_element(
        self,
        *,
        profile: GcdReportProfile,
        taxonomy_model: TaxonomyModel,
        context: TaxonomyContext,
    ) -> GcdReportElement:
        """Erzeugt das GCD-Report-Element aus dem Berichtsprofil."""

        if not isinstance(
            profile,
            GcdReportProfile,
        ):
            raise TypeError(
                "profile must be a GcdReportProfile"
            )

        if not isinstance(
            taxonomy_model,
            TaxonomyModel,
        ):
            raise TypeError(
                "taxonomy_model must be a TaxonomyModel"
            )

        if not isinstance(
            context,
            TaxonomyContext,
        ):
            raise TypeError(
                "context must be a TaxonomyContext"
            )

        concepts_by_name = {
            concept.name: concept
            for concept in taxonomy_model.concepts.concepts
        }

        values = {
            "genInfo.report.id.reportElement.reportElements.B": (
                "Bilanz"
            ),
            "genInfo.report.id.reportElement.reportElements.GuV": (
                "GuV"
            ),
            "genInfo.report.id.reportElement.reportElements.BAL": (
                "Anlagenspiegel"
            ),
            "genInfo.report.id.reportElement.reportElements.KS": (
                "Kontennachweis"
            ),
        }

        facts: list[TaxonomyTextFact] = []

        for concept_name in profile.report_elements:
            concept = concepts_by_name.get(
                concept_name
            )

            if concept is None:
                raise ValueError(
                    "GCD taxonomy concept not found: "
                    f"{concept_name}"
                )

            value = values.get(
                concept_name
            )

            if value is None:
                raise ValueError(
                    "unsupported GCD report element: "
                    f"{concept_name}"
                )

            facts.append(
                TaxonomyTextFact(
                    concept=concept,
                    value=value,
                    context=context,
                )
            )

        return GcdReportElement(
            facts=tuple(facts)
        )

    def report_data_facts(
        self,
        *,
        data: GcdReportData,
        taxonomy_model: TaxonomyModel,
        context: TaxonomyContext,
    ) -> tuple[TaxonomyTextFact, ...]:
        """Erzeugt GCD-Facts aus variablen Berichtsdaten."""

        if not isinstance(
            data,
            GcdReportData,
        ):
            raise TypeError(
                "data must be a GcdReportData"
            )

        if not isinstance(
            taxonomy_model,
            TaxonomyModel,
        ):
            raise TypeError(
                "taxonomy_model must be a TaxonomyModel"
            )

        if not isinstance(
            context,
            TaxonomyContext,
        ):
            raise TypeError(
                "context must be a TaxonomyContext"
            )

        concept_name = (
            "genInfo.report.id."
            "incomeStatementendswithBalProfit"
        )

        concepts_by_name = {
            concept.name: concept
            for concept in taxonomy_model.concepts.concepts
        }

        concept = concepts_by_name.get(
            concept_name
        )

        if concept is None:
            raise ValueError(
                "GCD taxonomy concept not found: "
                f"{concept_name}"
            )

        value = (
            "true"
            if data.income_statement_ends_with_balance_profit
            else "false"
        )

        return (
            TaxonomyTextFact(
                concept=concept,
                value=value,
                context=context,
            ),
        )

    def company_id_no(
        self,
        *,
        identifiers: GcdCompanyIdentifiers,
        taxonomy_model: TaxonomyModel,
        context: TaxonomyContext,
    ) -> GcdCompanyIdNo:
        """Erzeugt das GCD-idNo-Tuple für Unternehmenskennungen."""

        if not isinstance(
            identifiers,
            GcdCompanyIdentifiers,
        ):
            raise TypeError(
                "identifiers must be a GcdCompanyIdentifiers"
            )

        if not isinstance(
            taxonomy_model,
            TaxonomyModel,
        ):
            raise TypeError(
                "taxonomy_model must be a TaxonomyModel"
            )

        if not isinstance(
            context,
            TaxonomyContext,
        ):
            raise TypeError(
                "context must be a TaxonomyContext"
            )

        values: list[tuple[str, str]] = [
            (
                "genInfo.company.id.idNo.type.companyId.ST13",
                identifiers.tax_number_13,
            ),
        ]

        if identifiers.tax_id is not None:
            values.append(
                (
                    "genInfo.company.id.idNo.type.companyId.STID",
                    identifiers.tax_id,
                )
            )

        if identifiers.tax_economic_id is not None:
            values.append(
                (
                    "genInfo.company.id.idNo.type.companyId.STWID",
                    identifiers.tax_economic_id,
                )
            )

        if identifiers.bf4 is not None:
            values.append(
                (
                    "genInfo.company.id.idNo.type.companyId.BF4",
                    identifiers.bf4,
                )
            )

        concepts_by_name = {
            concept.name: concept
            for concept in taxonomy_model.concepts.concepts
        }

        facts: list[TaxonomyTextFact] = []

        for concept_name, value in values:
            concept = concepts_by_name.get(
                concept_name
            )

            if concept is None:
                raise ValueError(
                    "GCD taxonomy concept not found: "
                    f"{concept_name}"
                )

            facts.append(
                TaxonomyTextFact(
                    concept=concept,
                    value=value,
                    context=context,
                )
            )

        return GcdCompanyIdNo(
            facts=tuple(facts)
        )

    def domestic_branch_of_foreign_company(
        self,
        *,
        branch_type: GcdDomesticBranchOfForeignCompanyType,
        taxonomy_model: TaxonomyModel,
        context: TaxonomyContext,
    ) -> GcdDomesticBranchOfForeignCompany:
        """Erzeugt das GCD-Tuple für eine inländische Zweigniederlassung."""

        if not isinstance(
            branch_type,
            GcdDomesticBranchOfForeignCompanyType,
        ):
            raise TypeError(
                "branch_type must be a "
                "GcdDomesticBranchOfForeignCompanyType"
            )

        if not isinstance(
            taxonomy_model,
            TaxonomyModel,
        ):
            raise TypeError(
                "taxonomy_model must be a TaxonomyModel"
            )

        if not isinstance(
            context,
            TaxonomyContext,
        ):
            raise TypeError(
                "context must be a TaxonomyContext"
            )

        concept_name = (
            "genInfo.company.id."
            "domesticBranchOfForeignCompany."
            f"{branch_type.value}"
        )

        concepts_by_name = {
            concept.name: concept
            for concept in taxonomy_model.concepts.concepts
        }

        concept = concepts_by_name.get(
            concept_name
        )

        if concept is None:
            raise ValueError(
                "GCD taxonomy concept not found: "
                f"{concept_name}"
            )

        fact = TaxonomyTextFact(
            concept=concept,
            value=branch_type.value,
            context=context,
        )

        return GcdDomesticBranchOfForeignCompany(
            fact=fact,
        )

    def entity_with_taxable_purpose_business(
        self,
        *,
        business_type: GcdEntityWithTaxablePurposeBusinessType,
        taxonomy_model: TaxonomyModel,
        context: TaxonomyContext,
    ) -> GcdEntityWithTaxablePurposeBusiness:
        """Erzeugt das GCD-Tuple für den steuerpflichtigen Betrieb."""

        if not isinstance(
            business_type,
            GcdEntityWithTaxablePurposeBusinessType,
        ):
            raise TypeError(
                "business_type must be a "
                "GcdEntityWithTaxablePurposeBusinessType"
            )

        if not isinstance(
            taxonomy_model,
            TaxonomyModel,
        ):
            raise TypeError(
                "taxonomy_model must be a TaxonomyModel"
            )

        if not isinstance(
            context,
            TaxonomyContext,
        ):
            raise TypeError(
                "context must be a TaxonomyContext"
            )

        concept_name = (
            "genInfo.company.id."
            "entityWithTaxablePurposeBusiness."
            f"{business_type.value}"
        )

        concepts_by_name = {
            concept.name: concept
            for concept in taxonomy_model.concepts.concepts
        }

        concept = concepts_by_name.get(
            concept_name
        )

        if concept is None:
            raise ValueError(
                "GCD taxonomy concept not found: "
                f"{concept_name}"
            )

        fact = TaxonomyTextFact(
            concept=concept,
            value=business_type.value,
            context=context,
        )

        return GcdEntityWithTaxablePurposeBusiness(
            fact=fact,
        )

    def shareholder_facts(
        self,
        *,
        shareholder: GcdShareholder,
        taxonomy_model: TaxonomyModel,
        context: TaxonomyContext,
    ) -> tuple[TaxonomyTextFact, ...]:
        """Erzeugt die flachen Basis-Facts eines Gesellschafters."""

        if not isinstance(
            shareholder,
            GcdShareholder,
        ):
            raise TypeError(
                "shareholder must be a GcdShareholder"
            )

        if not isinstance(
            taxonomy_model,
            TaxonomyModel,
        ):
            raise TypeError(
                "taxonomy_model must be a TaxonomyModel"
            )

        if not isinstance(
            context,
            TaxonomyContext,
        ):
            raise TypeError(
                "context must be a TaxonomyContext"
            )

        concepts_by_name = {
            concept.name: concept
            for concept in taxonomy_model.concepts.concepts
        }

        values: list[tuple[str, str]] = [
            (
                "genInfo.company.id.shareholder.name",
                shareholder.name,
            ),
            (
                "genInfo.company.id.shareholder.id",
                shareholder.shareholder_id,
            ),
            (
                "genInfo.company.id.shareholder.taxnumber",
                shareholder.tax_number,
            ),
            (
                "genInfo.company.id.shareholder.taxid",
                shareholder.tax_id,
            ),
            (
                "genInfo.company.id.shareholder.WID",
                shareholder.wid,
            ),
        ]

        if shareholder.first_name is not None:
            values.append(
                (
                    "genInfo.company.id.shareholder.FirstName",
                    shareholder.first_name,
                )
            )

        if shareholder.group is not None:
            values.append(
                (
                    (
                        "genInfo.company.id.shareholder.group."
                        f"{shareholder.group.value}"
                    ),
                    shareholder.group.value,
                )
            )

        if shareholder.signer_id is not None:
            values.append(
                (
                    "genInfo.company.id.shareholder.signerId",
                    shareholder.signer_id,
                )
            )

        if shareholder.economic_id is not None:
            values.append(
                (
                    "genInfo.company.id.shareholder.beWiNr",
                    shareholder.economic_id,
                )
            )

        id_not_assigned_name = (
            "genInfo.company.id.shareholder.idNotAssigned"
        )

        if (
            shareholder.id_not_assigned is not None
            and id_not_assigned_name in concepts_by_name
        ):
            values.append(
                (
                    id_not_assigned_name,
                    shareholder.id_not_assigned,
                )
            )

        facts: list[TaxonomyTextFact] = []

        for concept_name, value in values:
            concept = concepts_by_name.get(
                concept_name
            )

            if concept is None:
                raise ValueError(
                    "GCD taxonomy concept not found: "
                    f"{concept_name}"
                )

            facts.append(
                TaxonomyTextFact(
                    concept=concept,
                    value=value,
                    context=context,
                )
            )

        return tuple(facts)

    def shareholder_legal_status(
        self,
        *,
        shareholder: GcdShareholder,
        taxonomy_model: TaxonomyModel,
        context: TaxonomyContext,
    ) -> GcdShareholderLegalStatusTuple:
        """Erzeugt das Legal-Status-Tuple eines Gesellschafters."""

        if not isinstance(
            shareholder,
            GcdShareholder,
        ):
            raise TypeError(
                "shareholder must be a GcdShareholder"
            )

        if not isinstance(
            taxonomy_model,
            TaxonomyModel,
        ):
            raise TypeError(
                "taxonomy_model must be a TaxonomyModel"
            )

        if not isinstance(
            context,
            TaxonomyContext,
        ):
            raise TypeError(
                "context must be a TaxonomyContext"
            )

        concept_name = (
            "genInfo.company.id.shareholder."
            "legalStatus.legalStatus."
            f"{shareholder.legal_status.value}"
        )

        concepts_by_name = {
            concept.name: concept
            for concept in taxonomy_model.concepts.concepts
        }

        concept = concepts_by_name.get(
            concept_name
        )

        if concept is None:
            raise ValueError(
                "GCD taxonomy concept not found: "
                f"{concept_name}"
            )

        fact = TaxonomyTextFact(
            concept=concept,
            value=shareholder.legal_status.value,
            context=context,
        )

        return GcdShareholderLegalStatusTuple(
            fact=fact,
        )

    def shareholder_share_divide_key(
        self,
        *,
        shareholder: GcdShareholder,
        taxonomy_model: TaxonomyModel,
        context: TaxonomyContext,
    ) -> GcdShareDivideKeyTuple:
        """Erzeugt das ShareDivideKey-Tuple eines Gesellschafters."""

        if not isinstance(
            shareholder,
            GcdShareholder,
        ):
            raise TypeError(
                "shareholder must be a GcdShareholder"
            )

        if not isinstance(
            taxonomy_model,
            TaxonomyModel,
        ):
            raise TypeError(
                "taxonomy_model must be a TaxonomyModel"
            )

        if not isinstance(
            context,
            TaxonomyContext,
        ):
            raise TypeError(
                "context must be a TaxonomyContext"
            )

        numerator_name = (
            "genInfo.company.id.shareholder."
            "ShareDivideKey.numerator"
        )

        denominator_name = (
            "genInfo.company.id.shareholder."
            "ShareDivideKey.denominator"
        )

        concepts_by_name = {
            concept.name: concept
            for concept in taxonomy_model.concepts.concepts
        }

        numerator_concept = concepts_by_name.get(
            numerator_name
        )

        if numerator_concept is None:
            raise ValueError(
                "GCD taxonomy concept not found: "
                f"{numerator_name}"
            )

        denominator_concept = concepts_by_name.get(
            denominator_name
        )

        if denominator_concept is None:
            raise ValueError(
                "GCD taxonomy concept not found: "
                f"{denominator_name}"
            )

        numerator_fact = TaxonomyTextFact(
            concept=numerator_concept,
            value=shareholder.share_divide_key.numerator,
            context=context,
        )

        denominator_fact = TaxonomyTextFact(
            concept=denominator_concept,
            value=shareholder.share_divide_key.denominator,
            context=context,
        )

        return GcdShareDivideKeyTuple(
            numerator=numerator_fact,
            denominator=denominator_fact,
        )

    def shareholder_current_number(
        self,
        *,
        shareholder: GcdShareholder,
        taxonomy_model: TaxonomyModel,
        context: TaxonomyContext,
    ) -> TaxonomyFact:
        """Erzeugt currentnumber als numerischen Gesellschafter-Fact."""

        if not isinstance(
            shareholder,
            GcdShareholder,
        ):
            raise TypeError(
                "shareholder must be a GcdShareholder"
            )

        if not isinstance(
            taxonomy_model,
            TaxonomyModel,
        ):
            raise TypeError(
                "taxonomy_model must be a TaxonomyModel"
            )

        if not isinstance(
            context,
            TaxonomyContext,
        ):
            raise TypeError(
                "context must be a TaxonomyContext"
            )

        if shareholder.current_number is None:
            raise ValueError(
                "shareholder.current_number must not be None"
            )

        concept_name = (
            "genInfo.company.id.shareholder.currentnumber"
        )

        concepts_by_name = {
            concept.name: concept
            for concept in taxonomy_model.concepts.concepts
        }

        concept = concepts_by_name.get(
            concept_name
        )

        if concept is None:
            raise ValueError(
                "GCD taxonomy concept not found: "
                f"{concept_name}"
            )

        return TaxonomyFact(
            concept=concept,
            amount=Decimal(
                shareholder.current_number
            ),
            context=context,
            unit=TaxonomyUnit.pure(),
            decimals="INF",
        )

    def shareholder(
        self,
        *,
        shareholder: GcdShareholder,
        taxonomy_model: TaxonomyModel,
        context: TaxonomyContext,
    ) -> GcdShareholderTuple:
        """Setzt die Gesellschafter-Bausteine zum GCD-Tuple zusammen."""

        if not isinstance(
            shareholder,
            GcdShareholder,
        ):
            raise TypeError(
                "shareholder must be a GcdShareholder"
            )

        if not isinstance(
            taxonomy_model,
            TaxonomyModel,
        ):
            raise TypeError(
                "taxonomy_model must be a TaxonomyModel"
            )

        if not isinstance(
            context,
            TaxonomyContext,
        ):
            raise TypeError(
                "context must be a TaxonomyContext"
            )

        flat_facts = self.shareholder_facts(
            shareholder=shareholder,
            taxonomy_model=taxonomy_model,
            context=context,
        )

        facts_by_name = {
            fact.concept.name: fact
            for fact in flat_facts
        }

        legal_status = self.shareholder_legal_status(
            shareholder=shareholder,
            taxonomy_model=taxonomy_model,
            context=context,
        )

        share_divide_key = self.shareholder_share_divide_key(
            shareholder=shareholder,
            taxonomy_model=taxonomy_model,
            context=context,
        )

        current_number = None

        if shareholder.current_number is not None:
            current_number = self.shareholder_current_number(
                shareholder=shareholder,
                taxonomy_model=taxonomy_model,
                context=context,
            )

        group_name = None

        if shareholder.group is not None:
            group_name = (
                "genInfo.company.id.shareholder.group."
                f"{shareholder.group.value}"
            )

        return GcdShareholderTuple(
            name=facts_by_name[
                "genInfo.company.id.shareholder.name"
            ],
            shareholder_id=facts_by_name[
                "genInfo.company.id.shareholder.id"
            ],
            tax_number=facts_by_name[
                "genInfo.company.id.shareholder.taxnumber"
            ],
            tax_id=facts_by_name[
                "genInfo.company.id.shareholder.taxid"
            ],
            wid=facts_by_name[
                "genInfo.company.id.shareholder.WID"
            ],
            legal_status=legal_status,
            share_divide_key=share_divide_key,
            first_name=facts_by_name.get(
                "genInfo.company.id.shareholder.FirstName"
            ),
            group=(
                facts_by_name.get(group_name)
                if group_name is not None
                else None
            ),
            current_number=current_number,
            signer_id=facts_by_name.get(
                "genInfo.company.id.shareholder.signerId"
            ),
            economic_id=facts_by_name.get(
                "genInfo.company.id.shareholder.beWiNr"
            ),
            id_not_assigned=facts_by_name.get(
                "genInfo.company.id.shareholder.idNotAssigned"
            ),
        )

"""Aufbau von GCD-Werten aus Unternehmensstammdaten."""

from datetime import date

from openbilanz.domain.fiscal_year import FiscalYear
from openbilanz.taxonomy.context import TaxonomyContext
from openbilanz.taxonomy.gcd_company_data import GcdCompanyData
from openbilanz.taxonomy.model import TaxonomyModel
from openbilanz.taxonomy.text_fact import TaxonomyTextFact

from openbilanz.taxonomy.gcd_report_profile import (
    GcdReportProfile,
)

from openbilanz.taxonomy.gcd_report_element import (
    GcdReportElement,
)
from openbilanz.taxonomy.taxonomy import (
    TaxonomyVersion,
)


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
    ) -> dict[str, date]:
        """Liefert die GCD-Werte für das Wirtschaftsjahr."""

        if not isinstance(
            fiscal_year,
            FiscalYear,
        ):
            raise TypeError(
                "fiscal_year must be a FiscalYear"
            )

        return {
            "genInfo.report.period.fiscalYearBegin": (
                fiscal_year.start_date
            ),
            "genInfo.report.period.fiscalYearEnd": (
                fiscal_year.end_date
            ),
        }
    
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
    ) -> tuple[TaxonomyTextFact, ...]:
        """Erzeugt GCD-Text-Facts für das Wirtschaftsjahr."""

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
            fiscal_year
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
                    value=value.isoformat(),
                    context=context,
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
        version=TaxonomyVersion
    ) -> GcdReportElement:
        """Erzeugt das GCD-Report-Element für den Standardfall."""

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
            
        if not isinstance(
            version,
            TaxonomyVersion,
        ):
            raise TypeError(
                "version must be a TaxonomyVersion"
            )

        values = [
            (
                "genInfo.report.id.reportElement."
                "reportElements.B",
                "Bilanz",
            ),
            (
                "genInfo.report.id.reportElement."
                "reportElements.GuV",
                "GuV",
            ),
            (
                "genInfo.report.id.reportElement."
                "reportElements.BAL",
                "Anlagenspiegel",
            ),
        ]

        if version in (
            TaxonomyVersion.V6_9,
            TaxonomyVersion.V6_10,
        ):
            values.append(
                (
                    "genInfo.report.id.reportElement."
                    "reportElements.KS",
                    "Kontennachweis",
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

        return GcdReportElement(
            facts=tuple(facts)
        )
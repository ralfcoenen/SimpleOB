"""Aufbau von GCD-Werten aus Unternehmensstammdaten."""

from datetime import date

from openbilanz.domain.fiscal_year import FiscalYear
from openbilanz.taxonomy.context import TaxonomyContext
from openbilanz.taxonomy.gcd_company_data import GcdCompanyData
from openbilanz.taxonomy.model import TaxonomyModel
from openbilanz.taxonomy.text_fact import TaxonomyTextFact


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

        return {
            "genInfo.company.id.name": (
                data.company.name
            ),
            "genInfo.company.id.idNo.type.companyId.ST13": (
                data.tax_number
            ),
            "genInfo.company.id.legalStatus.legalStatus.UG": (
                data.legal_form
            ),
        }
        
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
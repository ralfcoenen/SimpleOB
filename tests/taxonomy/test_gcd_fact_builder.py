"""Tests für den Aufbau von GCD-Facts."""

from datetime import date
from uuid import uuid4

from openbilanz.domain.company import Company
from openbilanz.domain.fiscal_year import FiscalYear
from openbilanz.taxonomy.concept import (
    TaxonomyBalance,
    TaxonomyConcept,
    TaxonomyPeriodType,
)
from openbilanz.taxonomy.concept_set import TaxonomyConceptSet
from openbilanz.taxonomy.context import TaxonomyContext
from openbilanz.taxonomy.gcd_company_data import GcdCompanyData
from openbilanz.taxonomy.gcd_fact_builder import GcdFactBuilder
from openbilanz.taxonomy.label_set import TaxonomyLabelSet
from openbilanz.taxonomy.model import TaxonomyModel
from openbilanz.taxonomy.presentation_set import (
    TaxonomyPresentationSet,
)
from openbilanz.taxonomy.text_fact import TaxonomyTextFact


def _taxonomy_model(
    *concepts: TaxonomyConcept,
) -> TaxonomyModel:
    """Erzeugt ein minimales GCD-Taxonomiemodell für Tests."""

    return TaxonomyModel(
        concepts=TaxonomyConceptSet(
            concepts=concepts,
        ),
        labels=TaxonomyLabelSet(
            labels=(),
        ),
        presentation=TaxonomyPresentationSet(
            relations=(),
        ),
    )

def test_gcd_fact_builder_defines_company_concepts() -> None:
    """Der Builder kennt die GCD-Concepts der UG-Stammdaten."""

    company = Company(
        company_id=uuid4(),
        name="Muster UG (haftungsbeschränkt)",
    )

    data = GcdCompanyData(
        company=company,
        tax_number="1234567890123",
        legal_form="UG (haftungsbeschränkt)",
    )

    builder = GcdFactBuilder()

    values = builder.company_values(
        data
    )

    assert values == {
        "genInfo.company.id.name": (
            "Muster UG (haftungsbeschränkt)"
        ),
        "genInfo.company.id.idNo.type.companyId.ST13": (
            "1234567890123"
        ),
        "genInfo.company.id.legalStatus.legalStatus.UG": (
            "UG (haftungsbeschränkt)"
        ),
    }


def test_gcd_fact_builder_defines_fiscal_year_values() -> None:
    """Der Builder liefert Beginn und Ende des Wirtschaftsjahres."""

    fiscal_year = FiscalYear(
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
    )

    builder = GcdFactBuilder()

    values = builder.fiscal_year_values(
        fiscal_year
    )

    assert values == {
        "genInfo.report.period.fiscalYearBegin": date(
            2025,
            1,
            1,
        ),
        "genInfo.report.period.fiscalYearEnd": date(
            2025,
            12,
            31,
        ),
    }

def test_gcd_fact_builder_builds_company_facts() -> None:
    """Unternehmensstammdaten werden zu GCD-Text-Facts."""

    company = Company(
        company_id=uuid4(),
        name="Muster UG (haftungsbeschränkt)",
    )

    data = GcdCompanyData(
        company=company,
        tax_number="1234567890123",
        legal_form="UG (haftungsbeschränkt)",
    )

    concepts = (
        TaxonomyConcept(
            name="genInfo.company.id.name",
            concept_id="de-gcd_genInfo.company.id.name",
            type_name="xbrli:stringItemType",
            substitution_group="xbrli:item",
            period_type=TaxonomyPeriodType.DURATION,
            balance=TaxonomyBalance.NONE,
            abstract=False,
            nillable=True,
        ),
        TaxonomyConcept(
            name=(
                "genInfo.company.id.idNo.type."
                "companyId.ST13"
            ),
            concept_id=(
                "de-gcd_genInfo.company.id.idNo."
                "type.companyId.ST13"
            ),
            type_name="de-gcd:ST13",
            substitution_group="xbrli:item",
            period_type=TaxonomyPeriodType.DURATION,
            balance=TaxonomyBalance.NONE,
            abstract=False,
            nillable=True,
        ),
        TaxonomyConcept(
            name=(
                "genInfo.company.id.legalStatus."
                "legalStatus.UG"
            ),
            concept_id=(
                "de-gcd_genInfo.company.id.legalStatus."
                "legalStatus.UG"
            ),
            type_name="xbrli:stringItemType",
            substitution_group="xbrli:item",
            period_type=TaxonomyPeriodType.DURATION,
            balance=TaxonomyBalance.NONE,
            abstract=False,
            nillable=True,
        ),
    )

    taxonomy_model = _taxonomy_model(
        *concepts
    )

    context = TaxonomyContext(
        entity_identifier="DE123456789",
        entity_scheme=(
            "http://www.bundesfinanzministerium.de"
        ),
        period_type=TaxonomyPeriodType.DURATION,
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
    )

    builder = GcdFactBuilder()

    facts = builder.company_facts(
        data=data,
        taxonomy_model=taxonomy_model,
        context=context,
    )

    assert len(facts) == 3

    assert all(
        isinstance(
            fact,
            TaxonomyTextFact,
        )
        for fact in facts
    )

    values = {
        fact.concept.name: fact.value
        for fact in facts
    }

    assert values == {
        "genInfo.company.id.name": (
            "Muster UG (haftungsbeschränkt)"
        ),
        "genInfo.company.id.idNo.type.companyId.ST13": (
            "1234567890123"
        ),
        "genInfo.company.id.legalStatus.legalStatus.UG": (
            "UG (haftungsbeschränkt)"
        ),
    }

def test_gcd_fact_builder_builds_fiscal_year_facts() -> None:
    """Wirtschaftsjahresdaten werden zu GCD-Text-Facts."""

    fiscal_year = FiscalYear(
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
    )

    concepts = (
        TaxonomyConcept(
            name="genInfo.report.period.fiscalYearBegin",
            concept_id=(
                "de-gcd_genInfo.report.period.fiscalYearBegin"
            ),
            type_name="xbrli:dateItemType",
            substitution_group="xbrli:item",
            period_type=TaxonomyPeriodType.DURATION,
            balance=TaxonomyBalance.NONE,
            abstract=False,
            nillable=True,
        ),
        TaxonomyConcept(
            name="genInfo.report.period.fiscalYearEnd",
            concept_id=(
                "de-gcd_genInfo.report.period.fiscalYearEnd"
            ),
            type_name="xbrli:dateItemType",
            substitution_group="xbrli:item",
            period_type=TaxonomyPeriodType.DURATION,
            balance=TaxonomyBalance.NONE,
            abstract=False,
            nillable=True,
        ),
    )

    taxonomy_model = _taxonomy_model(
        *concepts
    )

    context = TaxonomyContext(
        entity_identifier="DE123456789",
        entity_scheme=(
            "http://www.bundesfinanzministerium.de"
        ),
        period_type=TaxonomyPeriodType.DURATION,
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
    )

    builder = GcdFactBuilder()

    facts = builder.fiscal_year_facts(
        fiscal_year=fiscal_year,
        taxonomy_model=taxonomy_model,
        context=context,
    )

    assert len(facts) == 2

    assert all(
        isinstance(
            fact,
            TaxonomyTextFact,
        )
        for fact in facts
    )

    values = {
        fact.concept.name: fact.value
        for fact in facts
    }

    assert values == {
        "genInfo.report.period.fiscalYearBegin": (
            "2025-01-01"
        ),
        "genInfo.report.period.fiscalYearEnd": (
            "2025-12-31"
        ),
    }


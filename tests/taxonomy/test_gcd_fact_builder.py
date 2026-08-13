"""Tests für den Aufbau von GCD-Facts."""
from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from openbilanz.domain.company import Company
from openbilanz.domain.fiscal_year import FiscalYear
from openbilanz.taxonomy.concept import (
    TaxonomyBalance,
    TaxonomyConcept,
    TaxonomyPeriodType,
)
from openbilanz.taxonomy.concept_set import TaxonomyConceptSet
from openbilanz.taxonomy.context import TaxonomyContext
from openbilanz.taxonomy.fact import TaxonomyFact
from openbilanz.taxonomy.gcd_company_data import GcdCompanyData
from openbilanz.taxonomy.gcd_company_id_no import (
    GcdCompanyIdNo,
)
from openbilanz.taxonomy.gcd_company_identifiers import (
    GcdCompanyIdentifiers,
)
from openbilanz.taxonomy.gcd_fact_builder import GcdFactBuilder
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
    GcdShareDivideKey,
    GcdShareholder,
    GcdShareholderGroup,
    GcdShareholderLegalStatus,
)
from openbilanz.taxonomy.gcd_shareholder_tuple import (
    GcdShareDivideKeyTuple,
    GcdShareholderLegalStatusTuple,
    GcdShareholderTuple,
)
from openbilanz.taxonomy.label_set import TaxonomyLabelSet
from openbilanz.taxonomy.model import TaxonomyModel
from openbilanz.taxonomy.presentation_set import (
    TaxonomyPresentationSet,
)
from openbilanz.taxonomy.taxonomy import (
    TaxonomyVersion,
)
from openbilanz.taxonomy.text_fact import TaxonomyTextFact
from openbilanz.taxonomy.unit import TaxonomyUnit

TEST_ENTITY_SCHEME = (
    "http://www.bundesfinanzministerium.de"
)


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

def test_gcd_fact_builder_includes_required_company_details() -> None:
    """Der Builder liefert Anschrift und Unternehmensgegenstand."""

    company = Company(
        company_id=uuid4(),
        name="Muster UG (haftungsbeschränkt)",
    )

    data = GcdCompanyData(
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
        "genInfo.company.id.location.street": (
            "Musterstraße"
        ),
        "genInfo.company.id.location.houseNo": (
            "12a"
        ),
        "genInfo.company.id.location.zipCode": (
            "12345"
        ),
        "genInfo.company.id.location.city": (
            "Musterstadt"
        ),
        "genInfo.company.id.location.country": (
            "DE"
        ),
        "genInfo.company.id.business": (
            "Softwareentwicklung"
        ),
    }

def test_gcd_fact_builder_defines_gmbh_company_concepts() -> None:
    """Der Builder verwendet für eine GmbH das richtige GCD-Concept."""

    company = Company(
        company_id=uuid4(),
        name="Muster GmbH",
    )

    data = GcdCompanyData(
        company=company,
        tax_number="1234567890123",
        legal_form="GmbH",
    )

    builder = GcdFactBuilder()

    values = builder.company_values(
        data
    )

    assert values == {
        "genInfo.company.id.name": "Muster GmbH",
        "genInfo.company.id.idNo.type.companyId.ST13": (
            "1234567890123"
        ),
        "genInfo.company.id.legalStatus.legalStatus.GMBH": (
            "GmbH"
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
    "genInfo.report.period.balSheetClosingDate": date(
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
        entity_scheme=TEST_ENTITY_SCHEME,
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

def test_gcd_fact_builder_builds_required_company_detail_facts() -> None:
    """Anschrift und Unternehmensgegenstand werden zu GCD-Text-Facts."""

    company = Company(
        company_id=uuid4(),
        name="Muster UG (haftungsbeschränkt)",
    )

    data = GcdCompanyData(
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

    concept_names = (
        "genInfo.company.id.name",
        "genInfo.company.id.idNo.type.companyId.ST13",
        "genInfo.company.id.legalStatus.legalStatus.UG",
        "genInfo.company.id.location.street",
        "genInfo.company.id.location.houseNo",
        "genInfo.company.id.location.zipCode",
        "genInfo.company.id.location.city",
        "genInfo.company.id.location.country",
        "genInfo.company.id.business",
    )

    concepts = tuple(
        TaxonomyConcept(
            name=name,
            concept_id="de-gcd_" + name,
            type_name="xbrli:stringItemType",
            substitution_group="xbrli:item",
            period_type=TaxonomyPeriodType.DURATION,
            balance=TaxonomyBalance.NONE,
            abstract=False,
            nillable=True,
        )
        for name in concept_names
    )

    taxonomy_model = _taxonomy_model(
        *concepts
    )

    context = TaxonomyContext(
        entity_identifier="DE123456789",
        entity_scheme=TEST_ENTITY_SCHEME,
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
        "genInfo.company.id.location.street": (
            "Musterstraße"
        ),
        "genInfo.company.id.location.houseNo": (
            "12a"
        ),
        "genInfo.company.id.location.zipCode": (
            "12345"
        ),
        "genInfo.company.id.location.city": (
            "Musterstadt"
        ),
        "genInfo.company.id.location.country": (
            "DE"
        ),
        "genInfo.company.id.business": (
            "Softwareentwicklung"
        ),
    }


def test_gcd_fact_builder_builds_gmbh_company_facts() -> None:
    """GmbH-Stammdaten werden mit dem richtigen Rechtsform-Concept erzeugt."""

    company = Company(
        company_id=uuid4(),
        name="Muster GmbH",
    )

    data = GcdCompanyData(
        company=company,
        tax_number="1234567890123",
        legal_form="GmbH",
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
                "legalStatus.GMBH"
            ),
            concept_id=(
                "de-gcd_genInfo.company.id.legalStatus."
                "legalStatus.GMBH"
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
        entity_scheme=TEST_ENTITY_SCHEME,
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

    values = {
        fact.concept.name: fact.value
        for fact in facts
    }

    assert values == {
        "genInfo.company.id.name": "Muster GmbH",
        "genInfo.company.id.idNo.type.companyId.ST13": (
            "1234567890123"
        ),
        "genInfo.company.id.legalStatus.legalStatus.GMBH": (
            "GmbH"
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
        TaxonomyConcept(
            name="genInfo.report.period.balSheetClosingDate",
            concept_id=(
                "de-gcd_genInfo.report.period.balSheetClosingDate"
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
        entity_scheme=TEST_ENTITY_SCHEME,
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
        "genInfo.report.period.fiscalYearBegin": (
            "2025-01-01"
        ),
        "genInfo.report.period.fiscalYearEnd": (
            "2025-12-31"
        ),
        "genInfo.report.period.balSheetClosingDate": (
            "2025-12-31"
        ),
    }

def test_gcd_fact_builder_builds_report_profile_facts() -> None:
    """Das GCD-Berichtsprofil erzeugt grundlegende Berichtsfacts."""

    profile = GcdReportProfile.standard()

    report_status_concept = TaxonomyConcept(
        name=profile.report_status,
        concept_id=(
            "de-gcd_"
            + profile.report_status
        ),
        type_name="xbrli:stringItemType",
        substitution_group="xbrli:item",
        period_type=TaxonomyPeriodType.DURATION,
        balance=TaxonomyBalance.NONE,
        abstract=False,
        nillable=True,
    )

    revision_status_concept = TaxonomyConcept(
        name=profile.revision_status,
        concept_id=(
            "de-gcd_"
            + profile.revision_status
        ),
        type_name="xbrli:stringItemType",
        substitution_group="xbrli:item",
        period_type=TaxonomyPeriodType.DURATION,
        balance=TaxonomyBalance.NONE,
        abstract=False,
        nillable=True,
    )

    statement_type_concept = TaxonomyConcept(
        name=profile.statement_type,
        concept_id=(
            "de-gcd_"
            + profile.statement_type
        ),
        type_name="xbrli:stringItemType",
        substitution_group="xbrli:item",
        period_type=TaxonomyPeriodType.DURATION,
        balance=TaxonomyBalance.NONE,
        abstract=False,
        nillable=True,
    )

    accounting_standard_concept = TaxonomyConcept(
        name=profile.accounting_standard,
        concept_id=(
            "de-gcd_"
            + profile.accounting_standard
        ),
        type_name="xbrli:stringItemType",
        substitution_group="xbrli:item",
        period_type=TaxonomyPeriodType.DURATION,
        balance=TaxonomyBalance.NONE,
        abstract=False,
        nillable=True,
    )
    
    special_accounting_standard_concept = TaxonomyConcept(
        name=profile.special_accounting_standard,
        concept_id=(
            "de-gcd_"
            + profile.special_accounting_standard
        ),
        type_name="xbrli:stringItemType",
        substitution_group="xbrli:item",
        period_type=TaxonomyPeriodType.DURATION,
        balance=TaxonomyBalance.NONE,
        abstract=False,
        nillable=True,
    )

    income_statement_format_concept = TaxonomyConcept(
        name=profile.income_statement_format,
        concept_id=(
            "de-gcd_"
            + profile.income_statement_format
        ),
        type_name="xbrli:stringItemType",
        substitution_group="xbrli:item",
        period_type=TaxonomyPeriodType.DURATION,
        balance=TaxonomyBalance.NONE,
        abstract=False,
        nillable=True,
    )
    
    consolidation_range_concept = TaxonomyConcept(
        name=profile.consolidation_range,
        concept_id=(
            "de-gcd_"
            + profile.consolidation_range
        ),
        type_name="xbrli:stringItemType",
        substitution_group="xbrli:item",
        period_type=TaxonomyPeriodType.DURATION,
        balance=TaxonomyBalance.NONE,
        abstract=False,
        nillable=True,
    )

    income_classification_concept = TaxonomyConcept(
        name=profile.income_classification,
        concept_id=(
            "de-gcd_"
            + profile.income_classification
        ),
        type_name="xbrli:stringItemType",
        substitution_group="xbrli:item",
        period_type=TaxonomyPeriodType.DURATION,
        balance=TaxonomyBalance.NONE,
        abstract=False,
        nillable=True,
    )
    
    taxonomy_model = _taxonomy_model(
        report_status_concept,
        revision_status_concept,
        statement_type_concept,
        accounting_standard_concept,
        special_accounting_standard_concept,
        income_statement_format_concept,
        consolidation_range_concept,
        income_classification_concept,
    )

    context = TaxonomyContext(
        entity_identifier="DE123456789",
        entity_scheme=TEST_ENTITY_SCHEME,
        period_type=TaxonomyPeriodType.DURATION,
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
    )

    builder = GcdFactBuilder()

    facts = builder.report_profile_facts(
        profile=profile,
        taxonomy_model=taxonomy_model,
        context=context,
    )

    assert facts == (
        TaxonomyTextFact(
            concept=report_status_concept,
            value="endgültig",
            context=context,
        ),
        TaxonomyTextFact(
            concept=revision_status_concept,
            value="erstmalig",
            context=context,
        ),
        TaxonomyTextFact(
            concept=statement_type_concept,
            value="Jahresabschluss",
            context=context,
        ),
        TaxonomyTextFact(
            concept=accounting_standard_concept,
            value="deutsches Handelsrecht",
            context=context,
        ),
        TaxonomyTextFact(
            concept=special_accounting_standard_concept,
            value="Kerntaxonomie",
            context=context,
        ),
        TaxonomyTextFact(
            concept=income_statement_format_concept,
            value="Gesamtkostenverfahren",
            context=context,
        ),
        TaxonomyTextFact(
            concept=consolidation_range_concept,
            value="Einzelabschluss",
            context=context,
        ),
        TaxonomyTextFact(
            concept=income_classification_concept,
            value="Einkünfte aus Gewerbebetrieb",
            context=context,
        ),
    )
    
def test_gcd_fact_builder_builds_standard_report_element() -> None:
    """Das Standardprofil erzeugt die regulären Berichtselemente."""

    profile = GcdReportProfile.standard()

    concept_names = (
        "genInfo.report.id.reportElement.reportElements.B",
        "genInfo.report.id.reportElement.reportElements.GuV",
        "genInfo.report.id.reportElement.reportElements.BAL",
    )

    concepts = tuple(
        TaxonomyConcept(
            name=name,
            concept_id="de-gcd_" + name,
            type_name="xbrli:stringItemType",
            substitution_group=(
                "de-gcd:"
                "genInfo.report.id.reportElement."
                "reportElements.head"
            ),
            period_type=TaxonomyPeriodType.DURATION,
            balance=TaxonomyBalance.NONE,
            abstract=False,
            nillable=True,
        )
        for name in concept_names
    )

    taxonomy_model = _taxonomy_model(
        *concepts
    )

    context = TaxonomyContext(
        entity_identifier="DE123456789",
        entity_scheme=TEST_ENTITY_SCHEME,
        period_type=TaxonomyPeriodType.DURATION,
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
    )

    builder = GcdFactBuilder()

    report_element = builder.report_element(
        profile=profile,
        taxonomy_model=taxonomy_model,
        context=context,
        version=TaxonomyVersion.V6_8,
    )

    assert isinstance(
        report_element,
        GcdReportElement,
    )

    values = {
        fact.concept.name: fact.value
        for fact in report_element.facts
    }

    assert values == {
        "genInfo.report.id.reportElement.reportElements.B": (
            "Bilanz"
        ),
        "genInfo.report.id.reportElement.reportElements.GuV": (
            "GuV"
        ),
        "genInfo.report.id.reportElement.reportElements.BAL": (
            "Anlagenspiegel"
        ),
    }

def test_gcd_fact_builder_adds_account_statements_from_69() -> None:
    """Ab Taxonomie 6.9 gehört der Kontennachweis zum Report-Element."""

    profile = GcdReportProfile.standard()

    concept_names = (
        "genInfo.report.id.reportElement.reportElements.B",
        "genInfo.report.id.reportElement.reportElements.GuV",
        "genInfo.report.id.reportElement.reportElements.BAL",
        "genInfo.report.id.reportElement.reportElements.KS",
    )

    concepts = tuple(
        TaxonomyConcept(
            name=name,
            concept_id="de-gcd_" + name,
            type_name="xbrli:stringItemType",
            substitution_group=(
                "de-gcd:"
                "genInfo.report.id.reportElement."
                "reportElements.head"
            ),
            period_type=TaxonomyPeriodType.DURATION,
            balance=TaxonomyBalance.NONE,
            abstract=False,
            nillable=True,
        )
        for name in concept_names
    )

    taxonomy_model = _taxonomy_model(
        *concepts
    )

    context = TaxonomyContext(
        entity_identifier="DE123456789",
        entity_scheme=TEST_ENTITY_SCHEME,
        period_type=TaxonomyPeriodType.DURATION,
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
    )

    builder = GcdFactBuilder()

    report_element = builder.report_element(
        profile=profile,
        taxonomy_model=taxonomy_model,
        context=context,
        version=TaxonomyVersion.V6_9,
    )

    values = {
        fact.concept.name: fact.value
        for fact in report_element.facts
    }

    assert values == {
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
    
def test_gcd_fact_builder_keeps_account_statements_in_610() -> None:
    """Auch Taxonomie 6.10 enthält den Kontennachweis im Report-Element."""

    profile = GcdReportProfile.standard()

    concept_names = (
        "genInfo.report.id.reportElement.reportElements.B",
        "genInfo.report.id.reportElement.reportElements.GuV",
        "genInfo.report.id.reportElement.reportElements.BAL",
        "genInfo.report.id.reportElement.reportElements.KS",
    )

    concepts = tuple(
        TaxonomyConcept(
            name=name,
            concept_id="de-gcd_" + name,
            type_name="xbrli:stringItemType",
            substitution_group=(
                "de-gcd:"
                "genInfo.report.id.reportElement."
                "reportElements.head"
            ),
            period_type=TaxonomyPeriodType.DURATION,
            balance=TaxonomyBalance.NONE,
            abstract=False,
            nillable=True,
        )
        for name in concept_names
    )

    taxonomy_model = _taxonomy_model(
        *concepts
    )

    context = TaxonomyContext(
        entity_identifier="DE123456789",
        entity_scheme=TEST_ENTITY_SCHEME,
        period_type=TaxonomyPeriodType.DURATION,
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
    )

    builder = GcdFactBuilder()

    report_element = builder.report_element(
        profile=profile,
        taxonomy_model=taxonomy_model,
        context=context,
        version=TaxonomyVersion.V6_10,
    )

    values = {
        fact.concept.name: fact.value
        for fact in report_element.facts
    }

    assert values == {
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
    
def test_gcd_fact_builder_includes_balance_sheet_closing_date() -> None:
    """Das Ende des Wirtschaftsjahres ist zugleich der Bilanzstichtag."""

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
        "genInfo.report.period.balSheetClosingDate": date(
            2025,
            12,
            31,
        ),
    }


def test_gcd_fact_builder_includes_previous_fiscal_year_values() -> None:
    """Der Builder liefert die GCD-Periodendaten des Vorjahres."""

    fiscal_year = FiscalYear(
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
    )

    previous_fiscal_year = FiscalYear(
        start_date=date(2024, 1, 1),
        end_date=date(2024, 12, 31),
    )

    builder = GcdFactBuilder()

    values = builder.fiscal_year_values(
        fiscal_year,
        previous_fiscal_year=previous_fiscal_year,
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
        "genInfo.report.period.balSheetClosingDate": date(
            2025,
            12,
            31,
        ),
        "genInfo.report.period.fiscalPreviousYearBegin": date(
            2024,
            1,
            1,
        ),
        "genInfo.report.period.fiscalPreviousYearEnd": date(
            2024,
            12,
            31,
        ),
        "genInfo.report.period.balSheetClosingDatePreviousYear": date(
            2024,
            12,
            31,
        ),
    }
    
def test_gcd_fact_builder_builds_previous_fiscal_year_facts() -> None:
        """Vorjahresdaten werden zu GCD-Text-Facts."""

        fiscal_year = FiscalYear(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
        )

        previous_fiscal_year = FiscalYear(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
        )

        concept_names = (
            "genInfo.report.period.fiscalYearBegin",
            "genInfo.report.period.fiscalYearEnd",
            "genInfo.report.period.balSheetClosingDate",
            "genInfo.report.period.fiscalPreviousYearBegin",
            "genInfo.report.period.fiscalPreviousYearEnd",
            "genInfo.report.period.balSheetClosingDatePreviousYear",
        )

        concepts = tuple(
            TaxonomyConcept(
                name=name,
                concept_id="de-gcd_" + name,
                type_name="xbrli:dateItemType",
                substitution_group="xbrli:item",
                period_type=TaxonomyPeriodType.DURATION,
                balance=TaxonomyBalance.NONE,
                abstract=False,
                nillable=True,
            )
            for name in concept_names
        )

        taxonomy_model = _taxonomy_model(
            *concepts
        )

        context = TaxonomyContext(
            entity_identifier="DE123456789",
            entity_scheme=TEST_ENTITY_SCHEME,
            period_type=TaxonomyPeriodType.DURATION,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
        )

        builder = GcdFactBuilder()

        facts = builder.fiscal_year_facts(
            fiscal_year=fiscal_year,
            previous_fiscal_year=previous_fiscal_year,
            taxonomy_model=taxonomy_model,
            context=context,
        )

        assert len(facts) == 6

        values = {
            fact.concept.name: fact.value
            for fact in facts
        }

        assert values == {
            "genInfo.report.period.fiscalYearBegin": "2025-01-01",
            "genInfo.report.period.fiscalYearEnd": "2025-12-31",
            "genInfo.report.period.balSheetClosingDate": "2025-12-31",
            "genInfo.report.period.fiscalPreviousYearBegin": "2024-01-01",
            "genInfo.report.period.fiscalPreviousYearEnd": "2024-12-31",
            "genInfo.report.period.balSheetClosingDatePreviousYear": (
                "2024-12-31"
            ),
        }


@pytest.mark.parametrize(
    ("value", "expected"),
    (
        (
            True,
            "true",
        ),
        (
            False,
            "false",
        ),
    ),
)
def test_gcd_fact_builder_builds_variable_report_data_facts(
    value: bool,
    expected: str,
) -> None:
    """Variable Berichtsdaten werden zu GCD-Facts."""

    concept = TaxonomyConcept(
        name=(
            "genInfo.report.id."
            "incomeStatementendswithBalProfit"
        ),
        concept_id=(
            "de-gcd_genInfo.report.id."
            "incomeStatementendswithBalProfit"
        ),
        type_name="xbrli:booleanItemType",
        substitution_group="xbrli:item",
        period_type=TaxonomyPeriodType.DURATION,
        balance=TaxonomyBalance.NONE,
        abstract=False,
        nillable=True,
    )

    taxonomy_model = _taxonomy_model(
        concept
    )

    context = TaxonomyContext(
        entity_identifier="DE123456789",
        entity_scheme=TEST_ENTITY_SCHEME,
        period_type=TaxonomyPeriodType.DURATION,
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
    )

    data = GcdReportData(
        income_statement_ends_with_balance_profit=value,
    )

    builder = GcdFactBuilder()

    facts = builder.report_data_facts(
        data=data,
        taxonomy_model=taxonomy_model,
        context=context,
    )

    assert facts == (
        TaxonomyTextFact(
            concept=concept,
            value=expected,
            context=context,
        ),
    )
    
def test_gcd_fact_builder_builds_company_id_no_tuple() -> None:
    """Unternehmenskennungen werden zu einem GCD-idNo-Tuple."""

    identifiers = GcdCompanyIdentifiers(
        tax_number_13="1234567890123",
        tax_id="12345678901",
        tax_economic_id="DE123456789",
        bf4="1234",
    )

    concept_names = (
        "genInfo.company.id.idNo.type.companyId.ST13",
        "genInfo.company.id.idNo.type.companyId.STID",
        "genInfo.company.id.idNo.type.companyId.STWID",
        "genInfo.company.id.idNo.type.companyId.BF4",
    )

    concepts = tuple(
        TaxonomyConcept(
            name=name,
            concept_id="de-gcd_" + name,
            type_name="xbrli:stringItemType",
            substitution_group="xbrli:item",
            period_type=TaxonomyPeriodType.DURATION,
            balance=TaxonomyBalance.NONE,
            abstract=False,
            nillable=True,
        )
        for name in concept_names
    )

    taxonomy_model = _taxonomy_model(
        *concepts
    )

    context = TaxonomyContext(
        entity_identifier="DE123456789",
        entity_scheme=TEST_ENTITY_SCHEME,
        period_type=TaxonomyPeriodType.DURATION,
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
    )

    builder = GcdFactBuilder()

    company_id_no = builder.company_id_no(
        identifiers=identifiers,
        taxonomy_model=taxonomy_model,
        context=context,
    )

    assert isinstance(
        company_id_no,
        GcdCompanyIdNo,
    )

    values = {
        fact.concept.name: fact.value
        for fact in company_id_no.facts
    }

    assert values == {
        "genInfo.company.id.idNo.type.companyId.ST13": (
            "1234567890123"
        ),
        "genInfo.company.id.idNo.type.companyId.STID": (
            "12345678901"
        ),
        "genInfo.company.id.idNo.type.companyId.STWID": (
            "DE123456789"
        ),
        "genInfo.company.id.idNo.type.companyId.BF4": (
            "1234"
        ),
    }


def test_gcd_fact_builder_omits_optional_company_identifiers() -> None:
    """Nicht vorhandene optionale Kennungen werden nicht ausgegeben."""

    identifiers = GcdCompanyIdentifiers(
        tax_number_13="1234567890123",
    )

    concept = TaxonomyConcept(
        name=(
            "genInfo.company.id.idNo.type.companyId.ST13"
        ),
        concept_id=(
            "de-gcd_genInfo.company.id.idNo.type.companyId.ST13"
        ),
        type_name="xbrli:stringItemType",
        substitution_group="xbrli:item",
        period_type=TaxonomyPeriodType.DURATION,
        balance=TaxonomyBalance.NONE,
        abstract=False,
        nillable=True,
    )

    taxonomy_model = _taxonomy_model(
        concept
    )

    context = TaxonomyContext(
        entity_identifier="DE123456789",
        entity_scheme=TEST_ENTITY_SCHEME,
        period_type=TaxonomyPeriodType.DURATION,
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
    )

    builder = GcdFactBuilder()

    company_id_no = builder.company_id_no(
        identifiers=identifiers,
        taxonomy_model=taxonomy_model,
        context=context,
    )

    assert company_id_no.facts == (
        TaxonomyTextFact(
            concept=concept,
            value="1234567890123",
            context=context,
        ),
    )

def test_gcd_fact_builder_builds_basic_shareholder_facts() -> None:
    """Der Builder erzeugt die flachen Basis-Facts eines Gesellschafters."""

    shareholder = GcdShareholder(
        name="Mustermann",
        shareholder_id="1",
        tax_number="1234567890123",
        tax_id="12345678901",
        wid="WID-1",
        legal_status=(
            GcdShareholderLegalStatus.NATURAL_PERSON
        ),
        share_divide_key=GcdShareDivideKey(
            numerator="25",
            denominator="100",
        ),
    )

    concept_names = (
        "genInfo.company.id.shareholder.name",
        "genInfo.company.id.shareholder.id",
        "genInfo.company.id.shareholder.taxnumber",
        "genInfo.company.id.shareholder.taxid",
        "genInfo.company.id.shareholder.WID",
    )

    concepts = tuple(
        TaxonomyConcept(
            name=name,
            concept_id="de-gcd_" + name,
            type_name="xbrli:stringItemType",
            substitution_group="xbrli:item",
            period_type=TaxonomyPeriodType.DURATION,
            balance=TaxonomyBalance.NONE,
            abstract=False,
            nillable=True,
        )
        for name in concept_names
    )

    taxonomy_model = _taxonomy_model(
        *concepts
    )

    context = TaxonomyContext(
        entity_identifier="DE123456789",
        entity_scheme=TEST_ENTITY_SCHEME,
        period_type=TaxonomyPeriodType.DURATION,
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
    )

    builder = GcdFactBuilder()

    facts = builder.shareholder_facts(
        shareholder=shareholder,
        taxonomy_model=taxonomy_model,
        context=context,
    )

    assert len(facts) == 5

    values_by_name = {
        fact.concept.name: fact.value
        for fact in facts
    }

    assert values_by_name == {
        "genInfo.company.id.shareholder.name": (
            "Mustermann"
        ),
        "genInfo.company.id.shareholder.id": (
            "1"
        ),
        "genInfo.company.id.shareholder.taxnumber": (
            "1234567890123"
        ),
        "genInfo.company.id.shareholder.taxid": (
            "12345678901"
        ),
        "genInfo.company.id.shareholder.WID": (
            "WID-1"
        ),
    }

def test_gcd_fact_builder_builds_shareholder_group_fact() -> None:
    """Der Builder ergänzt die ausgewählte Gesellschaftergruppe."""

    shareholder = GcdShareholder(
        name="Mustermann",
        shareholder_id="1",
        tax_number="1234567890123",
        tax_id="12345678901",
        wid="WID-1",
        group=GcdShareholderGroup.LIMITED,
        legal_status=(
            GcdShareholderLegalStatus.NATURAL_PERSON
        ),
        share_divide_key=GcdShareDivideKey(
            numerator="25",
            denominator="100",
        ),
    )

    concept_names = (
        "genInfo.company.id.shareholder.name",
        "genInfo.company.id.shareholder.id",
        "genInfo.company.id.shareholder.taxnumber",
        "genInfo.company.id.shareholder.taxid",
        "genInfo.company.id.shareholder.WID",
        "genInfo.company.id.shareholder.group.limPartner",
    )

    concepts = tuple(
        TaxonomyConcept(
            name=name,
            concept_id="de-gcd_" + name,
            type_name="xbrli:stringItemType",
            substitution_group="xbrli:item",
            period_type=TaxonomyPeriodType.DURATION,
            balance=TaxonomyBalance.NONE,
            abstract=False,
            nillable=True,
        )
        for name in concept_names
    )

    taxonomy_model = _taxonomy_model(
        *concepts
    )

    context = TaxonomyContext(
        entity_identifier="DE123456789",
        entity_scheme=TEST_ENTITY_SCHEME,
        period_type=TaxonomyPeriodType.DURATION,
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
    )

    builder = GcdFactBuilder()

    facts = builder.shareholder_facts(
        shareholder=shareholder,
        taxonomy_model=taxonomy_model,
        context=context,
    )

    assert len(facts) == 6

    values_by_name = {
        fact.concept.name: fact.value
        for fact in facts
    }

    assert (
        values_by_name[
            "genInfo.company.id.shareholder.group.limPartner"
        ]
        == "limPartner"
    )

def test_gcd_fact_builder_builds_shareholder_legal_status() -> None:
    """Der Builder erzeugt das Legal-Status-Tuple eines Gesellschafters."""

    shareholder = GcdShareholder(
        name="Mustermann",
        shareholder_id="1",
        tax_number="1234567890123",
        tax_id="12345678901",
        wid="WID-1",
        legal_status=(
            GcdShareholderLegalStatus.NATURAL_PERSON
        ),
        share_divide_key=GcdShareDivideKey(
            numerator="25",
            denominator="100",
        ),
    )

    concept_name = (
        "genInfo.company.id.shareholder."
        "legalStatus.legalStatus.NPP"
    )

    concept = TaxonomyConcept(
        name=concept_name,
        concept_id="de-gcd_" + concept_name,
        type_name="xbrli:stringItemType",
        substitution_group="xbrli:item",
        period_type=TaxonomyPeriodType.DURATION,
        balance=TaxonomyBalance.NONE,
        abstract=False,
        nillable=True,
    )

    taxonomy_model = _taxonomy_model(
        concept
    )

    context = TaxonomyContext(
        entity_identifier="DE123456789",
        entity_scheme=TEST_ENTITY_SCHEME,
        period_type=TaxonomyPeriodType.DURATION,
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
    )

    builder = GcdFactBuilder()

    result = builder.shareholder_legal_status(
        shareholder=shareholder,
        taxonomy_model=taxonomy_model,
        context=context,
    )

    assert isinstance(
        result,
        GcdShareholderLegalStatusTuple,
    )

    assert result.fact.concept.name == concept_name
    assert result.fact.value == "NPP"
    assert result.fact.context == context
    
def test_gcd_fact_builder_builds_shareholder_share_divide_key() -> None:
    """Der Builder erzeugt das Beteiligungsquoten-Tuple."""

    shareholder = GcdShareholder(
        name="Mustermann",
        shareholder_id="1",
        tax_number="1234567890123",
        tax_id="12345678901",
        wid="WID-1",
        legal_status=(
            GcdShareholderLegalStatus.NATURAL_PERSON
        ),
        share_divide_key=GcdShareDivideKey(
            numerator="25",
            denominator="100",
        ),
    )

    numerator_name = (
        "genInfo.company.id.shareholder."
        "ShareDivideKey.numerator"
    )

    denominator_name = (
        "genInfo.company.id.shareholder."
        "ShareDivideKey.denominator"
    )

    concepts = (
        TaxonomyConcept(
            name=numerator_name,
            concept_id="de-gcd_" + numerator_name,
            type_name="xbrli:stringItemType",
            substitution_group="xbrli:item",
            period_type=TaxonomyPeriodType.DURATION,
            balance=TaxonomyBalance.NONE,
            abstract=False,
            nillable=True,
        ),
        TaxonomyConcept(
            name=denominator_name,
            concept_id="de-gcd_" + denominator_name,
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
        entity_scheme=TEST_ENTITY_SCHEME,
        period_type=TaxonomyPeriodType.DURATION,
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
    )

    builder = GcdFactBuilder()

    result = builder.shareholder_share_divide_key(
        shareholder=shareholder,
        taxonomy_model=taxonomy_model,
        context=context,
    )

    assert isinstance(
        result,
        GcdShareDivideKeyTuple,
    )

    assert (
        result.numerator.concept.name
        == numerator_name
    )
    assert result.numerator.value == "25"
    assert result.numerator.context == context

    assert (
        result.denominator.concept.name
        == denominator_name
    )
    assert result.denominator.value == "100"
    assert result.denominator.context == context


def test_gcd_fact_builder_builds_shareholder_current_number() -> None:
    """Der Builder erzeugt currentnumber als numerischen Fact."""

    shareholder = GcdShareholder(
        name="Mustermann",
        shareholder_id="1",
        tax_number="1234567890123",
        tax_id="12345678901",
        wid="WID-1",
        legal_status=(
            GcdShareholderLegalStatus.NATURAL_PERSON
        ),
        share_divide_key=GcdShareDivideKey(
            numerator="25",
            denominator="100",
        ),
        current_number=1,
    )

    concept_name = (
        "genInfo.company.id.shareholder.currentnumber"
    )

    concept = TaxonomyConcept(
        name=concept_name,
        concept_id="de-gcd_" + concept_name,
        type_name="xbrli:positiveIntegerItemType",
        substitution_group="xbrli:item",
        period_type=TaxonomyPeriodType.DURATION,
        balance=TaxonomyBalance.NONE,
        abstract=False,
        nillable=True,
    )

    taxonomy_model = _taxonomy_model(
        concept
    )

    context = TaxonomyContext(
        entity_identifier="DE123456789",
        entity_scheme=TEST_ENTITY_SCHEME,
        period_type=TaxonomyPeriodType.DURATION,
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
    )

    builder = GcdFactBuilder()

    result = builder.shareholder_current_number(
        shareholder=shareholder,
        taxonomy_model=taxonomy_model,
        context=context,
    )

    assert isinstance(
        result,
        TaxonomyFact,
    )

    assert result.concept.name == concept_name
    assert result.amount == Decimal("1")
    assert result.context == context
    assert result.unit == TaxonomyUnit.pure()
    assert result.decimals == "INF"
    
def test_gcd_fact_builder_builds_shareholder_tuple() -> None:
    """Der Builder setzt die Gesellschafter-Bausteine zum Tuple zusammen."""

    shareholder = GcdShareholder(
        name="Mustermann",
        shareholder_id="1",
        tax_number="1234567890123",
        tax_id="12345678901",
        wid="WID-1",
        group=GcdShareholderGroup.LIMITED,
        legal_status=(
            GcdShareholderLegalStatus.NATURAL_PERSON
        ),
        share_divide_key=GcdShareDivideKey(
            numerator="25",
            denominator="100",
        ),
        current_number=1,
    )

    concept_names = (
        "genInfo.company.id.shareholder.name",
        "genInfo.company.id.shareholder.id",
        "genInfo.company.id.shareholder.taxnumber",
        "genInfo.company.id.shareholder.taxid",
        "genInfo.company.id.shareholder.WID",
        "genInfo.company.id.shareholder.group.limPartner",
        (
            "genInfo.company.id.shareholder."
            "legalStatus.legalStatus.NPP"
        ),
        (
            "genInfo.company.id.shareholder."
            "ShareDivideKey.numerator"
        ),
        (
            "genInfo.company.id.shareholder."
            "ShareDivideKey.denominator"
        ),
        "genInfo.company.id.shareholder.currentnumber",
    )

    concepts = tuple(
        TaxonomyConcept(
            name=name,
            concept_id="de-gcd_" + name,
            type_name=(
                "xbrli:positiveIntegerItemType"
                if name.endswith("currentnumber")
                else "xbrli:stringItemType"
            ),
            substitution_group="xbrli:item",
            period_type=TaxonomyPeriodType.DURATION,
            balance=TaxonomyBalance.NONE,
            abstract=False,
            nillable=True,
        )
        for name in concept_names
    )

    taxonomy_model = _taxonomy_model(
        *concepts
    )

    context = TaxonomyContext(
        entity_identifier="DE123456789",
        entity_scheme=TEST_ENTITY_SCHEME,
        period_type=TaxonomyPeriodType.DURATION,
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
    )

    builder = GcdFactBuilder()

    result = builder.shareholder(
        shareholder=shareholder,
        taxonomy_model=taxonomy_model,
        context=context,
    )

    assert isinstance(
        result,
        GcdShareholderTuple,
    )

    assert result.name.value == "Mustermann"
    assert result.shareholder_id.value == "1"
    assert result.tax_number.value == "1234567890123"
    assert result.tax_id.value == "12345678901"
    assert result.wid.value == "WID-1"

    assert result.group is not None
    assert result.group.value == "limPartner"

    assert result.legal_status.fact.value == "NPP"

    assert (
        result.share_divide_key.numerator.value
        == "25"
    )
    assert (
        result.share_divide_key.denominator.value
        == "100"
    )

    assert result.current_number is not None
    assert result.current_number.amount == Decimal("1")
    assert result.current_number.unit == TaxonomyUnit.pure()
    assert result.current_number.decimals == "INF"
    

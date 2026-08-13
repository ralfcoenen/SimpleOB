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
from openbilanz.taxonomy.gcd_report_profile import (
    GcdReportProfile,
)
from openbilanz.taxonomy.label_set import TaxonomyLabelSet
from openbilanz.taxonomy.model import TaxonomyModel
from openbilanz.taxonomy.presentation_set import (
    TaxonomyPresentationSet,
)
from openbilanz.taxonomy.text_fact import TaxonomyTextFact
from openbilanz.taxonomy.gcd_report_element import (
    GcdReportElement,
)
from openbilanz.taxonomy.taxonomy import (
    TaxonomyVersion,
)

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
    

"""Tests für das GCD-Report-Element-Tuple."""
from datetime import date

import pytest

from simpleob.taxonomy.concept import (
    TaxonomyBalance,
    TaxonomyConcept,
    TaxonomyPeriodType,
)
from simpleob.taxonomy.context import TaxonomyContext
from simpleob.taxonomy.gcd_report_element import (
    GcdReportElement,
)
from simpleob.taxonomy.text_fact import TaxonomyTextFact

TEST_ENTITY_SCHEME = (
    "http://www.bundesfinanzministerium.de"
)


def test_gcd_report_element_contains_report_element_facts() -> None:
    """Ein GCD-Report-Element enthält mehrere Berichtselement-Facts."""

    context = TaxonomyContext(
        entity_identifier="DE123456789",
        entity_scheme=TEST_ENTITY_SCHEME,
        period_type=TaxonomyPeriodType.DURATION,
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
    )

    balance_concept = TaxonomyConcept(
        name=(
            "genInfo.report.id.reportElement."
            "reportElements.B"
        ),
        concept_id=(
            "de-gcd_genInfo.report.id.reportElement."
            "reportElements.B"
        ),
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

    income_statement_concept = TaxonomyConcept(
        name=(
            "genInfo.report.id.reportElement."
            "reportElements.GuV"
        ),
        concept_id=(
            "de-gcd_genInfo.report.id.reportElement."
            "reportElements.GuV"
        ),
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

    balance_fact = TaxonomyTextFact(
        concept=balance_concept,
        value="Bilanz",
        context=context,
    )

    income_statement_fact = TaxonomyTextFact(
        concept=income_statement_concept,
        value="GuV",
        context=context,
    )

    report_element = GcdReportElement(
        facts=(
            balance_fact,
            income_statement_fact,
        )
    )

    assert report_element.facts == (
        balance_fact,
        income_statement_fact,
    )

def test_gcd_report_element_rejects_non_text_facts() -> None:
    """Ein GCD-Report-Element enthält nur TaxonomyTextFact-Objekte."""

    with pytest.raises(
        TypeError,
        match="facts must contain only TaxonomyTextFact objects",
    ):
        GcdReportElement(
            facts=(
                "not-a-fact",  # type: ignore[arg-type]
            )
        )

def test_gcd_report_element_rejects_multiple_contexts() -> None:
    """Alle Facts eines GCD-Report-Elements verwenden denselben Context."""

    first_context = TaxonomyContext(
        entity_identifier="DE123456789",
        entity_scheme=TEST_ENTITY_SCHEME,
        period_type=TaxonomyPeriodType.DURATION,
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
    )

    second_context = TaxonomyContext(
        entity_identifier="DE123456789",
        entity_scheme=TEST_ENTITY_SCHEME,
        period_type=TaxonomyPeriodType.DURATION,
        start_date=date(2024, 1, 1),
        end_date=date(2024, 12, 31),
    )

    balance_concept = TaxonomyConcept(
        name=(
            "genInfo.report.id.reportElement."
            "reportElements.B"
        ),
        concept_id=(
            "de-gcd_genInfo.report.id.reportElement."
            "reportElements.B"
        ),
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

    income_statement_concept = TaxonomyConcept(
        name=(
            "genInfo.report.id.reportElement."
            "reportElements.GuV"
        ),
        concept_id=(
            "de-gcd_genInfo.report.id.reportElement."
            "reportElements.GuV"
        ),
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

    with pytest.raises(
        ValueError,
        match="facts must use the same context",
    ):
        GcdReportElement(
            facts=(
                TaxonomyTextFact(
                    concept=balance_concept,
                    value="Bilanz",
                    context=first_context,
                ),
                TaxonomyTextFact(
                    concept=income_statement_concept,
                    value="GuV",
                    context=second_context,
                ),
            )
        )
        

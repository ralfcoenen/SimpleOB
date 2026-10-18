"""Tests für nichtnumerische Text-Facts."""
from datetime import date

import pytest

from simpleob.taxonomy.concept import (
    TaxonomyBalance,
    TaxonomyConcept,
    TaxonomyPeriodType,
)
from simpleob.taxonomy.context import TaxonomyContext
from simpleob.taxonomy.text_fact import TaxonomyTextFact

TEST_ENTITY_SCHEME = (
    "http://www.bundesfinanzministerium.de"
)


def test_taxonomy_text_fact_stores_string_value() -> None:
    """Ein stringItemType-Concept kann einen Textwert tragen."""

    concept = TaxonomyConcept(
        name="nt.registerAgriculture",
        concept_id="de-gaap-ci_nt.registerAgriculture",
        type_name="xbrli:stringItemType",
        substitution_group="xbrli:item",
        period_type=TaxonomyPeriodType.DURATION,
        balance=TaxonomyBalance.NONE,
        abstract=False,
        nillable=True,
    )

    context = TaxonomyContext(
        entity_identifier="DE123456789",
        entity_scheme=TEST_ENTITY_SCHEME,
        period_type=TaxonomyPeriodType.DURATION,
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
    )

    fact = TaxonomyTextFact(
        concept=concept,
        value="Landwirtschaftlicher Betrieb",
        context=context,
    )

    assert fact.concept is concept
    assert fact.value == "Landwirtschaftlicher Betrieb"
    assert fact.context is context
    
def test_taxonomy_text_fact_rejects_non_string_value() -> None:
    """Ein Text-Fact benötigt einen String-Wert."""

    concept = TaxonomyConcept(
        name="nt.registerAgriculture",
        concept_id="de-gaap-ci_nt.registerAgriculture",
        type_name="xbrli:stringItemType",
        substitution_group="xbrli:item",
        period_type=TaxonomyPeriodType.DURATION,
        balance=TaxonomyBalance.NONE,
        abstract=False,
        nillable=True,
    )

    context = TaxonomyContext(
        entity_identifier="DE123456789",
        entity_scheme=TEST_ENTITY_SCHEME,
        period_type=TaxonomyPeriodType.DURATION,
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
    )

    with pytest.raises(
        TypeError,
        match="value must be a string",
    ):
        TaxonomyTextFact(
            concept=concept,
            value=123,  # type: ignore[arg-type]
            context=context,
        )

def test_taxonomy_text_fact_rejects_invalid_concept() -> None:
    """Ein Text-Fact benötigt ein gültiges Taxonomie-Concept."""

    context = TaxonomyContext(
        entity_identifier="DE123456789",
        entity_scheme=TEST_ENTITY_SCHEME,
        period_type=TaxonomyPeriodType.DURATION,
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
    )

    with pytest.raises(
        TypeError,
        match="concept must be a TaxonomyConcept",
    ):
        TaxonomyTextFact(
            concept="invalid",  # type: ignore[arg-type]
            value="Test",
            context=context,
        )

def test_taxonomy_text_fact_rejects_invalid_context() -> None:
    """Ein Text-Fact benötigt einen gültigen Taxonomie-Context."""

    concept = TaxonomyConcept(
        name="nt.registerAgriculture",
        concept_id="de-gaap-ci_nt.registerAgriculture",
        type_name="xbrli:stringItemType",
        substitution_group="xbrli:item",
        period_type=TaxonomyPeriodType.DURATION,
        balance=TaxonomyBalance.NONE,
        abstract=False,
        nillable=True,
    )

    with pytest.raises(
        TypeError,
        match="context must be a TaxonomyContext",
    ):
        TaxonomyTextFact(
            concept=concept,
            value="Test",
            context="invalid",  # type: ignore[arg-type]
        )
        
def test_taxonomy_text_fact_rejects_numeric_concept() -> None:
    """Ein Text-Fact darf kein numerisches Concept verwenden."""

    concept = TaxonomyConcept(
        name="bs.ass.fixAss",
        concept_id="de-gaap-ci_bs.ass.fixAss",
        type_name="xbrli:monetaryItemType",
        substitution_group="xbrli:item",
        period_type=TaxonomyPeriodType.INSTANT,
        balance=TaxonomyBalance.DEBIT,
        abstract=False,
        nillable=True,
    )

    context = TaxonomyContext(
        entity_identifier="DE123456789",
        entity_scheme=TEST_ENTITY_SCHEME,
        period_type=TaxonomyPeriodType.INSTANT,
        start_date=None,
        end_date=date(2025, 12, 31),
    )

    with pytest.raises(
        ValueError,
        match="concept must not be numeric",
    ):
        TaxonomyTextFact(
            concept=concept,
            value="Test",
            context=context,
        )
        
def test_taxonomy_text_fact_rejects_mismatching_context_period_type() -> None:
    """Context und Concept müssen denselben Periodentyp verwenden."""

    concept = TaxonomyConcept(
        name="nt.registerAgriculture",
        concept_id="de-gaap-ci_nt.registerAgriculture",
        type_name="xbrli:stringItemType",
        substitution_group="xbrli:item",
        period_type=TaxonomyPeriodType.DURATION,
        balance=TaxonomyBalance.NONE,
        abstract=False,
        nillable=True,
    )

    context = TaxonomyContext(
        entity_identifier="DE123456789",
        entity_scheme=TEST_ENTITY_SCHEME,
        period_type=TaxonomyPeriodType.INSTANT,
        start_date=None,
        end_date=date(2025, 12, 31),
    )

    with pytest.raises(
        ValueError,
        match="context period type does not match concept",
    ):
        TaxonomyTextFact(
            concept=concept,
            value="Test",
            context=context,
        )
        

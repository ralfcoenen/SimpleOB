"""Tests für den Aufbau taxonomischer Facts."""

from datetime import date
from decimal import Decimal

import pytest

from openbilanz.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
from openbilanz.accounting.statement_category import StatementCategory
from openbilanz.taxonomy.concept import (
    TaxonomyBalance,
    TaxonomyConcept,
    TaxonomyPeriodType,
)
from openbilanz.taxonomy.context import TaxonomyContext
from openbilanz.taxonomy.fact_builder import TaxonomyFactBuilder
from openbilanz.taxonomy.mapper import TaxonomyMapper
from openbilanz.taxonomy.mapping import TaxonomyMappingRule
from openbilanz.taxonomy.mapping_set import TaxonomyMappingSet
from openbilanz.taxonomy.unit import TaxonomyUnit

TEST_ENTITY_SCHEME = "http://www.bundesfinanzministerium.de"


def _instant_context() -> TaxonomyContext:
    """Erzeugt einen gültigen Instant-Kontext für Tests."""

    return TaxonomyContext(
        entity_identifier="DE123456789",
        entity_scheme=TEST_ENTITY_SCHEME,
        period_type=TaxonomyPeriodType.INSTANT,
        start_date=None,
        end_date=date(2025, 12, 31),
    )


def _duration_context() -> TaxonomyContext:
    """Erzeugt einen gültigen Duration-Kontext für Tests."""

    return TaxonomyContext(
        entity_identifier="DE123456789",
        entity_scheme=TEST_ENTITY_SCHEME,
        period_type=TaxonomyPeriodType.DURATION,
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
    )


def _euro_unit() -> TaxonomyUnit:
    """Erzeugt die EUR-Einheit für Tests."""

    return TaxonomyUnit.eur()


def test_fact_builder_maps_position_and_amount_to_concept() -> None:
    """Eine Abschlussposition mit Betrag wird zum taxonomischen Fact."""

    position = FinancialStatementPosition(
        code="HGB.266.AKTIVA.A",
        name="Anlagevermögen",
        category=StatementCategory.ASSET,
    )

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

    mapper = TaxonomyMapper(
        mappings=TaxonomyMappingSet(
            rules=(
                TaxonomyMappingRule(
                    position=position,
                    concept=concept,
                ),
            )
        )
    )

    builder = TaxonomyFactBuilder(
        mapper=mapper
    )

    context = _instant_context()
    unit = _euro_unit()

    facts = builder.build(
        amounts={
            position: Decimal("125000.00"),
        },
        context=context,
        unit=unit,
    )

    assert len(facts) == 1

    fact = facts[0]

    assert fact.concept is concept
    assert fact.amount == Decimal("125000.00")
    assert fact.context is context
    assert fact.unit is unit


def test_fact_builder_aggregates_positions_for_same_concept() -> None:
    """Mehrere interne Positionen für dasselbe Concept werden summiert."""

    first_position = FinancialStatementPosition(
        code="HGB.266.AKTIVA.A.I",
        name="Immaterielle Vermögensgegenstände",
        category=StatementCategory.ASSET,
    )

    second_position = FinancialStatementPosition(
        code="HGB.266.AKTIVA.A.II",
        name="Sachanlagen",
        category=StatementCategory.ASSET,
    )

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

    mapper = TaxonomyMapper(
        mappings=TaxonomyMappingSet(
            rules=(
                TaxonomyMappingRule(
                    position=first_position,
                    concept=concept,
                ),
                TaxonomyMappingRule(
                    position=second_position,
                    concept=concept,
                ),
            )
        )
    )

    builder = TaxonomyFactBuilder(
        mapper=mapper
    )

    context = _instant_context()
    unit = _euro_unit()

    facts = builder.build(
        amounts={
            first_position: Decimal("25000.00"),
            second_position: Decimal("75000.00"),
        },
        context=context,
        unit=unit,
    )

    assert len(facts) == 1

    fact = facts[0]

    assert fact.concept is concept
    assert fact.amount == Decimal("100000.00")
    assert fact.context is context
    assert fact.unit is unit


def test_fact_builder_ignores_zero_amounts() -> None:
    """Nullbeträge erzeugen keinen taxonomischen Fact."""

    position = FinancialStatementPosition(
        code="HGB.266.AKTIVA.A",
        name="Anlagevermögen",
        category=StatementCategory.ASSET,
    )

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

    mapper = TaxonomyMapper(
        mappings=TaxonomyMappingSet(
            rules=(
                TaxonomyMappingRule(
                    position=position,
                    concept=concept,
                ),
            )
        )
    )

    builder = TaxonomyFactBuilder(
        mapper=mapper
    )

    facts = builder.build(
        amounts={
            position: Decimal("0.00"),
        },
        context=_instant_context(),
        unit=_euro_unit(),
    )

    assert facts == ()


def test_fact_builder_removes_zero_after_aggregation() -> None:
    """Ein auf 0 aggregierter Fact wird nicht ausgegeben."""

    first_position = FinancialStatementPosition(
        code="HGB.TEST.1",
        name="Erste Position",
        category=StatementCategory.NEUTRAL,
    )

    second_position = FinancialStatementPosition(
        code="HGB.TEST.2",
        name="Zweite Position",
        category=StatementCategory.NEUTRAL,
    )

    concept = TaxonomyConcept(
        name="test.concept",
        concept_id="test_concept",
        type_name="xbrli:monetaryItemType",
        substitution_group="xbrli:item",
        period_type=TaxonomyPeriodType.DURATION,
        balance=TaxonomyBalance.NONE,
        abstract=False,
        nillable=True,
    )

    mapper = TaxonomyMapper(
        mappings=TaxonomyMappingSet(
            rules=(
                TaxonomyMappingRule(
                    position=first_position,
                    concept=concept,
                ),
                TaxonomyMappingRule(
                    position=second_position,
                    concept=concept,
                ),
            )
        )
    )

    builder = TaxonomyFactBuilder(
        mapper=mapper
    )

    facts = builder.build(
        amounts={
            first_position: Decimal("100.00"),
            second_position: Decimal("-100.00"),
        },
        context=_duration_context(),
        unit=_euro_unit(),
    )

    assert facts == ()


def test_fact_builder_rejects_non_numeric_concept() -> None:
    """Nicht numerische Concepts können keinen Decimal-Fact erzeugen."""

    position = FinancialStatementPosition(
        code="HGB.TEST.STRING",
        name="Textposition",
        category=StatementCategory.NEUTRAL,
    )

    concept = TaxonomyConcept(
        name="test.text",
        concept_id="test_text",
        type_name="xbrli:stringItemType",
        substitution_group="xbrli:item",
        period_type=TaxonomyPeriodType.DURATION,
        balance=TaxonomyBalance.NONE,
        abstract=False,
        nillable=True,
    )

    mapper = TaxonomyMapper(
        mappings=TaxonomyMappingSet(
            rules=(
                TaxonomyMappingRule(
                    position=position,
                    concept=concept,
                ),
            )
        )
    )

    builder = TaxonomyFactBuilder(
        mapper=mapper
    )

    with pytest.raises(
        ValueError,
        match="concept is not numeric",
    ):
        builder.build(
            amounts={
                position: Decimal("100.00"),
            },
            context=_duration_context(),
            unit=_euro_unit(),
        )
    
"""Tests für taxonomische Facts."""

from datetime import date
from decimal import Decimal

import pytest

from openbilanz.taxonomy.concept import (
    TaxonomyBalance,
    TaxonomyConcept,
    TaxonomyPeriodType,
)
from openbilanz.taxonomy.context import TaxonomyContext
from openbilanz.taxonomy.fact import TaxonomyFact
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


def _euro_unit() -> TaxonomyUnit:
    """Erzeugt die EUR-Einheit für Tests."""

    return TaxonomyUnit.eur()


def test_taxonomy_fact_rejects_non_decimal_amount() -> None:
    """Ein numerischer Fact benötigt einen Decimal-Wert."""

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

    with pytest.raises(
        TypeError,
        match="amount must be a Decimal",
    ):
        TaxonomyFact(
            concept=concept,
            amount=100,  # type: ignore[arg-type]
            context=_instant_context(),
            unit=_euro_unit(),
        )


def test_taxonomy_fact_rejects_invalid_concept() -> None:
    """Ein Fact benötigt ein gültiges Taxonomie-Concept."""

    with pytest.raises(
        TypeError,
        match="concept must be a TaxonomyConcept",
    ):
        TaxonomyFact(
            concept="invalid",  # type: ignore[arg-type]
            amount=Decimal("100.00"),
            context=_instant_context(),
            unit=_euro_unit(),
        )


def test_taxonomy_fact_rejects_non_numeric_concept() -> None:
    """Ein Decimal-Fact benötigt ein numerisches Concept."""

    concept = TaxonomyConcept(
        name="test.text",
        concept_id="test_text",
        type_name="xbrli:stringItemType",
        substitution_group="xbrli:item",
        period_type=TaxonomyPeriodType.INSTANT,
        balance=TaxonomyBalance.NONE,
        abstract=False,
        nillable=True,
    )

    with pytest.raises(
        ValueError,
        match="concept is not numeric",
    ):
        TaxonomyFact(
            concept=concept,
            amount=Decimal("100.00"),
            context=_instant_context(),
            unit=_euro_unit(),
        )


def test_taxonomy_fact_rejects_mismatching_context_period_type() -> None:
    """Context und Concept müssen denselben Periodentyp verwenden."""

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
        period_type=TaxonomyPeriodType.DURATION,
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
    )

    with pytest.raises(
        ValueError,
        match="context period type does not match concept",
    ):
        TaxonomyFact(
            concept=concept,
            amount=Decimal("100.00"),
            context=context,
            unit=_euro_unit(),
        )


def test_taxonomy_fact_stores_unit() -> None:
    """Ein numerischer Fact trägt eine XBRL-Einheit."""

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

    context = _instant_context()
    unit = _euro_unit()

    fact = TaxonomyFact(
        concept=concept,
        amount=Decimal("100.00"),
        context=context,
        unit=unit,
    )

    assert fact.unit is unit


def test_taxonomy_fact_rejects_non_monetary_unit_for_monetary_concept() -> None:
    """Ein monetäres Concept benötigt eine ISO-4217-Währungseinheit."""

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

    unit = TaxonomyUnit(
        measure="xbrli:pure",
    )

    with pytest.raises(
        ValueError,
        match="monetary concept requires ISO 4217 unit",
    ):
        TaxonomyFact(
            concept=concept,
            amount=Decimal("100.00"),
            context=_instant_context(),
            unit=unit,
        )


def test_taxonomy_fact_rejects_non_pure_unit_for_pure_concept() -> None:
    """Ein pureItemType benötigt die XBRL-Einheit xbrli:pure."""

    concept = TaxonomyConcept(
        name="nt.particip.listRow.quota.direct",
        concept_id="de-gaap-ci_nt.particip.listRow.quota.direct",
        type_name="xbrli:pureItemType",
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
        ValueError,
        match="pure concept requires xbrli:pure unit",
    ):
        TaxonomyFact(
            concept=concept,
            amount=Decimal("0.75"),
            context=context,
            unit=TaxonomyUnit.eur(),
        )

def test_taxonomy_fact_stores_decimals() -> None:
    """Ein numerischer Fact speichert seine Dezimalgenauigkeit."""

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

    fact = TaxonomyFact(
        concept=concept,
        amount=Decimal("125000.00"),
        context=_instant_context(),
        unit=_euro_unit(),
        decimals=2,
    )

    assert fact.decimals == 2


def test_taxonomy_fact_accepts_infinite_decimals() -> None:
    """Ein exakter numerischer Fact kann decimals=INF verwenden."""

    concept = TaxonomyConcept(
        name="nt.other.specialKindOfShares",
        concept_id="de-gaap-ci_nt.other.specialKindOfShares",
        type_name="xbrli:longItemType",
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

    fact = TaxonomyFact(
        concept=concept,
        amount=Decimal("3"),
        context=context,
        unit=TaxonomyUnit(
            measure="xbrli:pure",
        ),
        decimals="INF",
    )

    assert fact.decimals == "INF"

@pytest.mark.parametrize(
    "decimals",
    (
        "2",
        "exact",
        "",
    ),
)
def test_taxonomy_fact_rejects_invalid_decimals_string(
    decimals: str,
) -> None:
    """Ungültige String-Werte für decimals werden abgelehnt."""

    concept = TaxonomyConcept(
        name="nt.other.specialKindOfShares",
        concept_id="de-gaap-ci_nt.other.specialKindOfShares",
        type_name="xbrli:longItemType",
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
        match='decimals must be an int or "INF"',
    ):
        TaxonomyFact(
            concept=concept,
            amount=Decimal("3"),
            context=context,
            unit=TaxonomyUnit(
                measure="xbrli:pure",
            ),
            decimals=decimals,
        )

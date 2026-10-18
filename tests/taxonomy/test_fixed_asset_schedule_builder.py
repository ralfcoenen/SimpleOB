"""Tests für die GAAP-CI-Abbildung des Anlagenspiegels."""

from datetime import date
from decimal import Decimal

from simpleob.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
from simpleob.accounting.statement_category import (
    StatementCategory,
)
from simpleob.services.fixed_asset_schedule_service import (
    FixedAssetSchedulePosition,
)
from simpleob.taxonomy.concept import (
    TaxonomyBalance,
    TaxonomyConcept,
    TaxonomyPeriodType,
)
from simpleob.taxonomy.concept_set import TaxonomyConceptSet
from simpleob.taxonomy.fixed_asset_schedule_builder import (
    FixedAssetScheduleBuilder,
)
from simpleob.taxonomy.label_set import TaxonomyLabelSet
from simpleob.taxonomy.mapper import TaxonomyMapper
from simpleob.taxonomy.mapping import TaxonomyMappingRule
from simpleob.taxonomy.mapping_set import TaxonomyMappingSet
from simpleob.taxonomy.model import TaxonomyModel
from simpleob.taxonomy.presentation import (
    TaxonomyPresentationRelation,
)
from simpleob.taxonomy.presentation_set import (
    TaxonomyPresentationSet,
)

TEST_ENTITY_IDENTIFIER = "DE123456789"

TEST_ENTITY_SCHEME = (
    "http://www.bundesfinanzministerium.de"
)

NOTES_ROLE = (
    "http://www.xbrl.de/taxonomies/"
    "de-gaap-ci/role/notes"
)


def _monetary_duration_concept(
    name: str,
) -> TaxonomyConcept:
    return TaxonomyConcept(
        name=name,
        concept_id=f"de-gaap-ci_{name}",
        type_name="xbrli:monetaryItemType",
        substitution_group="xbrli:item",
        period_type=TaxonomyPeriodType.DURATION,
        balance=None,
        abstract=False,
        nillable=True,
    )


def _monetary_instant_concept(
    name: str,
) -> TaxonomyConcept:
    return TaxonomyConcept(
        name=name,
        concept_id=f"de-gaap-ci_{name}",
        type_name="xbrli:monetaryItemType",
        substitution_group="xbrli:item",
        period_type=TaxonomyPeriodType.INSTANT,
        balance=TaxonomyBalance.DEBIT,
        abstract=False,
        nillable=True,
    )


def _relation(
    parent_name: str,
    child_name: str,
    order: str,
) -> TaxonomyPresentationRelation:
    return TaxonomyPresentationRelation(
        parent_concept_id=f"de-gaap-ci_{parent_name}",
        child_concept_id=f"de-gaap-ci_{child_name}",
        order=Decimal(order),
        role_uri=NOTES_ROLE,
        preferred_label_role_uri=None,
    )


def _taxonomy_model() -> TaxonomyModel:
    asset_concepts = (
        _monetary_instant_concept(
            "bs.ass.fixAss"
        ),
        _monetary_instant_concept(
            "bs.ass.fixAss.tan"
        ),
        _monetary_instant_concept(
            "bs.ass.fixAss.tan.machinery"
        ),
        _monetary_instant_concept(
            "bs.ass.fixAss.tan.otherEquipm"
        ),
        _monetary_instant_concept(
            "bs.ass.fixAss.tan.otherEquipm.otherbga"
        ),
    )

    movement_concepts = tuple(
        _monetary_duration_concept(name)
        for name in (
            "grossCost.beginning",
            "gross.addition",
            "gross.release",
            "gross",
            "accDepr.beginning",
            "accDepr.DeprPeriod.regular",
            "accDepr.DeprPeriod",
            "accDepr.release",
            "accDepr",
            "all",
            "gross.movements",
            "revaluation",
            "accDepr.addition",
            "accDepr.movements",
            "accDepr.DeprPeriod.extraordinary",
            "accDepr.DeprPeriod.impairment",
            "accDepr.DeprPeriod.EStG7g_2",
            "accDepr.DeprPeriod.EStG6b_3",
        )
    )

    return TaxonomyModel(
        concepts=TaxonomyConceptSet(
            concepts=(
                *asset_concepts,
                *movement_concepts,
            ),
        ),
        labels=TaxonomyLabelSet(
            labels=(),
        ),
        presentation=TaxonomyPresentationSet(
            relations=(
                _relation(
                    "bs.ass.fixAss",
                    "bs.ass.fixAss.tan",
                    "1",
                ),
                _relation(
                    "bs.ass.fixAss.tan",
                    "bs.ass.fixAss.tan.machinery",
                    "1",
                ),
                _relation(
                    "bs.ass.fixAss.tan",
                    "bs.ass.fixAss.tan.otherEquipm",
                    "2",
                ),
                _relation(
                    "bs.ass.fixAss.tan.otherEquipm",
                    "bs.ass.fixAss.tan.otherEquipm.otherbga",
                    "1",
                ),
            ),
        ),
    )


def _taxonomy_mapper(
    taxonomy_model: TaxonomyModel,
) -> TaxonomyMapper:
    machinery = FinancialStatementPosition(
        code="HGB.266.AKTIVA.A.II.2",
        name="Technische Anlagen und Maschinen",
        category=StatementCategory.ASSET,
    )
    other_equipment = FinancialStatementPosition(
        code="HGB.266.AKTIVA.A.II.3",
        name=(
            "Andere Anlagen, Betriebs- "
            "und Geschäftsausstattung"
        ),
        category=StatementCategory.ASSET,
    )

    mappings = TaxonomyMappingSet(
        rules=(
            TaxonomyMappingRule(
                position=machinery,
                concept_name=(
                    "bs.ass.fixAss.tan.machinery"
                ),
            ),
            TaxonomyMappingRule(
                position=other_equipment,
                concept_name=(
                    "bs.ass.fixAss.tan.otherEquipm"
                ),
            ),
        )
    )
    return TaxonomyMapper(
        mappings=mappings,
        taxonomy_model=taxonomy_model,
    )


def _schedule_position(
    *,
    position_code: str = "HGB.266.AKTIVA.A.II.2",
    acquisition_cost_beginning: str = "10000.00",
    additions: str = "12000.00",
    disposals: str = "3000.00",
    acquisition_cost_ending: str = "19000.00",
    accumulated_depreciation_beginning: str = "2000.00",
    depreciation_current_year: str = "2400.00",
    depreciation_disposals: str = "600.00",
    accumulated_depreciation_ending: str = "3800.00",
    carrying_amount_ending: str = "15200.00",
) -> FixedAssetSchedulePosition:
    return FixedAssetSchedulePosition(
        position_code=position_code,
        acquisition_cost_beginning=Decimal(
            acquisition_cost_beginning
        ),
        additions=Decimal(additions),
        disposals=Decimal(disposals),
        acquisition_cost_ending=Decimal(
            acquisition_cost_ending
        ),
        accumulated_depreciation_beginning=Decimal(
            accumulated_depreciation_beginning
        ),
        depreciation_current_year=Decimal(
            depreciation_current_year
        ),
        depreciation_disposals=Decimal(
            depreciation_disposals
        ),
        accumulated_depreciation_ending=Decimal(
            accumulated_depreciation_ending
        ),
        carrying_amount_ending=Decimal(
            carrying_amount_ending
        ),
    )


def _member_name(context) -> str:
    return context.dimensions[1].member_name


def _facts_for_member(result, member_name: str):
    context = next(
        context
        for context in result.contexts.values()
        if _member_name(context) == member_name
    )
    return {
        fact.concept.name: fact
        for fact in result.facts
        if fact.context is context
    }


def _nil_facts_for_member(result, member_name: str):
    context = next(
        context
        for context in result.contexts.values()
        if _member_name(context) == member_name
    )
    return {
        fact.concept.name: fact
        for fact in result.nil_facts
        if fact.context is context
    }


def test_builds_leaf_and_parent_fixed_asset_schedule() -> None:
    """Eine Anlagenposition erzeugt Blatt- und Parent-Kontexte."""

    taxonomy_model = _taxonomy_model()

    builder = FixedAssetScheduleBuilder(
        taxonomy_model=taxonomy_model,
        taxonomy_mapper=_taxonomy_mapper(
            taxonomy_model
        ),
    )
    result = builder.build(
        positions=(
            _schedule_position(),
        ),
        entity_identifier=TEST_ENTITY_IDENTIFIER,
        entity_scheme=TEST_ENTITY_SCHEME,
        fiscal_year_start=date(
            2025,
            1,
            1,
        ),
        fiscal_year_end=date(
            2025,
            12,
            31,
        ),
    )

    assert len(result.contexts) == 3
    assert len(result.facts) == 30
    assert len(result.nil_facts) == 24

    members = {
        _member_name(context)
        for context in result.contexts.values()
    }
    assert members == {
        "de-gaap-ci:bs.ass.fixAss",
        "de-gaap-ci:bs.ass.fixAss.tan",
        "de-gaap-ci:bs.ass.fixAss.tan.machinery",
    }

    leaf_facts = _facts_for_member(
        result,
        "de-gaap-ci:bs.ass.fixAss.tan.machinery",
    )

    assert set(leaf_facts) == {
        "grossCost.beginning",
        "gross.addition",
        "gross.release",
        "gross",
        "accDepr.beginning",
        "accDepr.DeprPeriod.regular",
        "accDepr.DeprPeriod",
        "accDepr.release",
        "accDepr",
        "all",
    }

    leaf_nil_facts = _nil_facts_for_member(
        result,
        "de-gaap-ci:bs.ass.fixAss.tan.machinery",
    )
    assert set(leaf_nil_facts) == {
        "gross.movements",
        "revaluation",
        "accDepr.addition",
        "accDepr.movements",
        "accDepr.DeprPeriod.extraordinary",
        "accDepr.DeprPeriod.impairment",
        "accDepr.DeprPeriod.EStG7g_2",
        "accDepr.DeprPeriod.EStG6b_3",
    }
    for nil_fact in leaf_nil_facts.values():
        assert nil_fact.unit.measure == "iso4217:EUR"

    assert (
        leaf_facts[
            "grossCost.beginning"
        ].amount
        == Decimal("10000.00")
    )
    assert (
        leaf_facts["gross.addition"].amount
        == Decimal("12000.00")
    )
    assert (
        leaf_facts["gross.release"].amount
        == Decimal("3000.00")
    )
    assert (
        leaf_facts["gross"].amount
        == Decimal("19000.00")
    )
    assert (
        leaf_facts[
            "accDepr.beginning"
        ].amount
        == Decimal("2000.00")
    )
    assert (
        leaf_facts[
            "accDepr.DeprPeriod.regular"
        ].amount
        == Decimal("2400.00")
    )
    assert (
        leaf_facts[
            "accDepr.DeprPeriod"
        ].amount
        == Decimal("2400.00")
    )
    assert (
        leaf_facts[
            "accDepr.release"
        ].amount
        == Decimal("600.00")
    )
    assert (
        leaf_facts["accDepr"].amount
        == Decimal("3800.00")
    )
    assert (
        leaf_facts["all"].amount
        == Decimal("15200.00")
    )

    for context in result.contexts.values():
        assert (
            context.period_type
            is TaxonomyPeriodType.DURATION
        )
        assert context.start_date == date(
            2025,
            1,
            1,
        )
        assert context.end_date == date(
            2025,
            12,
            31,
        )
        assert len(context.dimensions) == 2
        assert (
            context.dimensions[0].dimension_name
            == "de-gaap-ci:dim_taxTrans"
        )
        assert (
            context.dimensions[0].member_name
            == "de-gaap-ci:dim_comBal"
        )
        assert (
            context.dimensions[1].dimension_name
            == (
                "de-gaap-ci:"
                "dim_changes.nt.ass.gross"
            )
        )

    for fact in result.facts:
        assert fact.unit.measure == "iso4217:EUR"


def test_aggregates_sibling_positions_into_parent_contexts() -> None:
    """Parent-Kontexte summieren mehrere untergeordnete Anlageklassen."""

    taxonomy_model = _taxonomy_model()
    builder = FixedAssetScheduleBuilder(
        taxonomy_model=taxonomy_model,
        taxonomy_mapper=_taxonomy_mapper(
            taxonomy_model
        ),
    )

    machinery = _schedule_position()

    other_equipment = _schedule_position(
        position_code="HGB.266.AKTIVA.A.II.3",
        acquisition_cost_beginning="1000.00",
        additions="2000.00",
        disposals="0.00",
        acquisition_cost_ending="3000.00",
        accumulated_depreciation_beginning="100.00",
        depreciation_current_year="300.00",
        depreciation_disposals="0.00",
        accumulated_depreciation_ending="400.00",
        carrying_amount_ending="2600.00",
    )

    result = builder.build(
        positions=(
            machinery,
            other_equipment,
        ),
        entity_identifier=TEST_ENTITY_IDENTIFIER,
        entity_scheme=TEST_ENTITY_SCHEME,
        fiscal_year_start=date(
            2025,
            1,
            1,
        ),
        fiscal_year_end=date(
            2025,
            12,
            31,
        ),
    )

    assert len(result.contexts) == 5
    assert len(result.facts) == 50
    assert len(result.nil_facts) == 40

    tan_facts = _facts_for_member(
        result,
        "de-gaap-ci:bs.ass.fixAss.tan",
    )
    fixed_assets_facts = _facts_for_member(
        result,
        "de-gaap-ci:bs.ass.fixAss",
    )

    for parent_facts in (
        tan_facts,
        fixed_assets_facts,
    ):
        assert (
            parent_facts[
                "grossCost.beginning"
            ].amount
            == Decimal("11000.00")
        )
        assert (
            parent_facts["gross.addition"].amount
            == Decimal("14000.00")
        )
        assert (
            parent_facts["gross.release"].amount
            == Decimal("3000.00")
        )
        assert (
            parent_facts["gross"].amount
            == Decimal("22000.00")
        )
        assert (
            parent_facts[
                "accDepr.beginning"
            ].amount
            == Decimal("2100.00")
        )
        assert (
            parent_facts[
                "accDepr.DeprPeriod.regular"
            ].amount
            == Decimal("2700.00")
        )
        assert (
            parent_facts[
                "accDepr.DeprPeriod"
            ].amount
            == Decimal("2700.00")
        )
        assert (
            parent_facts[
                "accDepr.release"
            ].amount
            == Decimal("600.00")
        )
        assert (
            parent_facts["accDepr"].amount
            == Decimal("4200.00")
        )
        assert (
            parent_facts["all"].amount
            == Decimal("17800.00")
        )


def test_aggregates_duplicate_positions_into_one_taxonomy_context() -> None:
    """Mehrere Werte derselben Anlageklasse erzeugen keinen Doppelfakt."""

    taxonomy_model = _taxonomy_model()
    builder = FixedAssetScheduleBuilder(
        taxonomy_model=taxonomy_model,
        taxonomy_mapper=_taxonomy_mapper(
            taxonomy_model
        ),
    )

    first = _schedule_position()
    second = _schedule_position(
        acquisition_cost_beginning="5000.00",
        additions="0.00",
        disposals="0.00",
        acquisition_cost_ending="5000.00",
        accumulated_depreciation_beginning="1000.00",
        depreciation_current_year="500.00",
        depreciation_disposals="0.00",
        accumulated_depreciation_ending="1500.00",
        carrying_amount_ending="3500.00",
    )

    result = builder.build(
        positions=(
            first,
            second,
        ),
        entity_identifier=TEST_ENTITY_IDENTIFIER,
        entity_scheme=TEST_ENTITY_SCHEME,
        fiscal_year_start=date(
            2025,
            1,
            1,
        ),
        fiscal_year_end=date(
            2025,
            12,
            31,
        ),
    )

    assert len(result.contexts) == 3
    assert len(result.facts) == 30
    assert len(result.nil_facts) == 24

    leaf_facts = _facts_for_member(
        result,
        "de-gaap-ci:bs.ass.fixAss.tan.machinery",
    )
    assert (
        leaf_facts["gross"].amount
        == Decimal("24000.00")
    )
    assert (
        leaf_facts["accDepr"].amount
        == Decimal("5300.00")
    )
    assert (
        leaf_facts["all"].amount
        == Decimal("18700.00")
    )


def test_builds_empty_schedule_without_contexts_or_facts() -> None:
    """Ein leerer Anlagenspiegel erzeugt keine XBRL-Bestandteile."""

    taxonomy_model = _taxonomy_model()

    builder = FixedAssetScheduleBuilder(
        taxonomy_model=taxonomy_model,
        taxonomy_mapper=_taxonomy_mapper(
            taxonomy_model
        ),
    )
    result = builder.build(
        positions=(),
        entity_identifier=TEST_ENTITY_IDENTIFIER,
        entity_scheme=TEST_ENTITY_SCHEME,
        fiscal_year_start=date(
            2025,
            1,
            1,
        ),
        fiscal_year_end=date(
            2025,
            12,
            31,
        ),
    )

    assert result.contexts == {}
    assert result.facts == ()
    assert result.nil_facts == ()

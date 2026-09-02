"""Tests für die GAAP-CI-Abbildung des Anlagenspiegels."""

from datetime import date
from decimal import Decimal

from openbilanz.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
from openbilanz.accounting.statement_category import (
    StatementCategory,
)
from openbilanz.services.fixed_asset_schedule_service import (
    FixedAssetSchedulePosition,
)
from openbilanz.taxonomy.concept import (
    TaxonomyBalance,
    TaxonomyConcept,
    TaxonomyPeriodType,
)
from openbilanz.taxonomy.concept_set import TaxonomyConceptSet
from openbilanz.taxonomy.fixed_asset_schedule_builder import (
    FixedAssetScheduleBuilder,
)
from openbilanz.taxonomy.label_set import TaxonomyLabelSet
from openbilanz.taxonomy.mapper import TaxonomyMapper
from openbilanz.taxonomy.mapping import TaxonomyMappingRule
from openbilanz.taxonomy.mapping_set import TaxonomyMappingSet
from openbilanz.taxonomy.model import TaxonomyModel
from openbilanz.taxonomy.presentation_set import (
    TaxonomyPresentationSet,
)

TEST_ENTITY_IDENTIFIER = "DE123456789"

TEST_ENTITY_SCHEME = (
    "http://www.bundesfinanzministerium.de"
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


def _taxonomy_model() -> TaxonomyModel:
    concepts = (
        TaxonomyConcept(
            name="bs.ass.fixAss.tan.machinery",
            concept_id=(
                "de-gaap-ci_"
                "bs.ass.fixAss.tan.machinery"
            ),
            type_name="xbrli:monetaryItemType",
            substitution_group="xbrli:item",
            period_type=TaxonomyPeriodType.INSTANT,
            balance=TaxonomyBalance.DEBIT,
            abstract=False,
            nillable=True,
        ),
        _monetary_duration_concept(
            "grossCost.beginning"
        ),
        _monetary_duration_concept(
            "gross.addition"
        ),
        _monetary_duration_concept(
            "gross.release"
        ),
        _monetary_duration_concept(
            "accDepr.beginning"
        ),
        _monetary_duration_concept(
            "accDepr.DeprPeriod.regular"
        ),
        _monetary_duration_concept(
            "accDepr.release"
        ),
    )

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


def _taxonomy_mapper(
    taxonomy_model: TaxonomyModel,
) -> TaxonomyMapper:
    position = FinancialStatementPosition(
        code="HGB.266.AKTIVA.A.II.2",
        name="Technische Anlagen und Maschinen",
        category=StatementCategory.ASSET,
    )

    mappings = TaxonomyMappingSet(
        rules=(
            TaxonomyMappingRule(
                position=position,
                concept_name=(
                    "bs.ass.fixAss.tan.machinery"
                ),
            ),
        )
    )

    return TaxonomyMapper(
        mappings=mappings,
        taxonomy_model=taxonomy_model,
    )


def _schedule_position() -> FixedAssetSchedulePosition:
    return FixedAssetSchedulePosition(
        position_code="HGB.266.AKTIVA.A.II.2",
        acquisition_cost_beginning=Decimal(
            "10000.00"
        ),
        additions=Decimal(
            "12000.00"
        ),
        disposals=Decimal(
            "3000.00"
        ),
        acquisition_cost_ending=Decimal(
            "19000.00"
        ),
        accumulated_depreciation_beginning=Decimal(
            "2000.00"
        ),
        depreciation_current_year=Decimal(
            "2400.00"
        ),
        depreciation_disposals=Decimal(
            "600.00"
        ),
        accumulated_depreciation_ending=Decimal(
            "3800.00"
        ),
        carrying_amount_ending=Decimal(
            "15200.00"
        ),
    )


def test_builds_dimensional_fixed_asset_schedule() -> None:
    """Eine Anlagenposition erzeugt einen Kontext und sechs Facts."""

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

    assert tuple(
        result.contexts
    ) == (
        "ctx-fixed-assets-1",
    )

    context = result.contexts[
        "ctx-fixed-assets-1"
    ]

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

    assert len(
        context.dimensions
    ) == 2

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
    assert (
        context.dimensions[1].member_name
        == (
            "de-gaap-ci:"
            "bs.ass.fixAss.tan.machinery"
        )
    )

    assert len(
        result.facts
    ) == 6

    facts_by_name = {
        fact.concept.name: fact
        for fact in result.facts
    }

    assert set(
        facts_by_name
    ) == {
        "grossCost.beginning",
        "gross.addition",
        "gross.release",
        "accDepr.beginning",
        "accDepr.DeprPeriod.regular",
        "accDepr.release",
    }

    assert (
        facts_by_name[
            "grossCost.beginning"
        ].amount
        == Decimal("10000.00")
    )

    assert (
        facts_by_name[
            "gross.addition"
        ].amount
        == Decimal("12000.00")
    )

    assert (
        facts_by_name[
            "gross.release"
        ].amount
        == Decimal("3000.00")
    )

    assert (
        facts_by_name[
            "accDepr.beginning"
        ].amount
        == Decimal("2000.00")
    )

    assert (
        facts_by_name[
            "accDepr.DeprPeriod.regular"
        ].amount
        == Decimal("2400.00")
    )

    assert (
        facts_by_name[
            "accDepr.release"
        ].amount
        == Decimal("600.00")
    )

    for fact in result.facts:
        assert fact.context is context
        assert fact.unit.measure == "iso4217:EUR"


def test_builds_one_context_per_fixed_asset_position() -> None:
    """Jede Anlagenposition erhält ihren eigenen Kontext."""

    taxonomy_model = _taxonomy_model()

    builder = FixedAssetScheduleBuilder(
        taxonomy_model=taxonomy_model,
        taxonomy_mapper=_taxonomy_mapper(
            taxonomy_model
        ),
    )

    first = _schedule_position()

    second = FixedAssetSchedulePosition(
        position_code="HGB.266.AKTIVA.A.II.2",
        acquisition_cost_beginning=Decimal(
            "5000.00"
        ),
        additions=Decimal(
            "0.00"
        ),
        disposals=Decimal(
            "0.00"
        ),
        acquisition_cost_ending=Decimal(
            "5000.00"
        ),
        accumulated_depreciation_beginning=Decimal(
            "1000.00"
        ),
        depreciation_current_year=Decimal(
            "500.00"
        ),
        depreciation_disposals=Decimal(
            "0.00"
        ),
        accumulated_depreciation_ending=Decimal(
            "1500.00"
        ),
        carrying_amount_ending=Decimal(
            "3500.00"
        ),
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

    assert tuple(
        result.contexts
    ) == (
        "ctx-fixed-assets-1",
        "ctx-fixed-assets-2",
    )

    assert len(
        result.facts
    ) == 12


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

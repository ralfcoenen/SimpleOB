"""Tests für die E-Bilanz-Facts des Anlagenspiegels."""

from datetime import date
from decimal import Decimal
from unittest.mock import Mock

import pytest

from openbilanz.reporting.fixed_asset_schedule import (
    FixedAssetSchedule,
    FixedAssetScheduleRow,
)
from openbilanz.taxonomy.concept import (
    TaxonomyConcept,
    TaxonomyPeriodType,
)
from openbilanz.taxonomy.fixed_asset_schedule_fact_builder import (
    FixedAssetScheduleFactBuilder,
)
from openbilanz.taxonomy.unit import TaxonomyUnit


def _concept(
    *,
    concept_id: str,
    name: str,
) -> TaxonomyConcept:
    return TaxonomyConcept(
        concept_id=concept_id,
        name=name,
        type_name="xbrli:monetaryItemType",
        substitution_group="xbrli:item",
        period_type=TaxonomyPeriodType.DURATION,
        balance=None,
        abstract=False,
        nillable=True,
    )

def test_builds_fixed_asset_schedule_facts() -> None:
    """Anfangsbestand und AfA werden dimensional abgebildet."""

    concepts = {
        "de-gaap-ci_grossCost.beginning_short": _concept(
            concept_id=(
                "de-gaap-ci_grossCost.beginning_short"
            ),
            name="grossCost.beginning_short",
        ),
        "de-gaap-ci_accDepr.DeprPeriod_short": _concept(
            concept_id=(
                "de-gaap-ci_accDepr.DeprPeriod_short"
            ),
            name="accDepr.DeprPeriod_short",
        ),
    }

    taxonomy_model = Mock()
    taxonomy_model.concepts.by_id.side_effect = (
        concepts.get
    )

    schedule = FixedAssetSchedule(
        rows=(
            FixedAssetScheduleRow(
                position_code="HGB.266.AKTIVA.A.II.3",
                opening_cost=Decimal("12000.00"),
                additions=Decimal("0.00"),
                disposals=Decimal("0.00"),
                current_depreciation=Decimal("2400.00"),
                accumulated_depreciation=Decimal("4800.00"),
                closing_book_value=Decimal("7200.00"),
            ),
        )
    )

    unit = TaxonomyUnit(
        measure="iso4217:EUR"
    )

    builder = FixedAssetScheduleFactBuilder(
        taxonomy_model=taxonomy_model
    )

    facts = builder.build(
        schedule=schedule,
        entity_identifier="123456789",
        entity_scheme="http://example.com",
        fiscal_year_start=date(2026, 1, 1),
        fiscal_year_end=date(2026, 12, 31),
        unit=unit,
    )

    assert len(facts) == 2

    facts_by_id = {
        fact.concept.concept_id: fact
        for fact in facts
    }

    opening_fact = facts_by_id[
        "de-gaap-ci_grossCost.beginning_short"
    ]
    depreciation_fact = facts_by_id[
        "de-gaap-ci_accDepr.DeprPeriod_short"
    ]

    assert opening_fact.amount == Decimal("12000.00")
    assert depreciation_fact.amount == Decimal("2400.00")

    context = opening_fact.context

    assert context.period_type is TaxonomyPeriodType.DURATION
    assert context.start_date == date(2026, 1, 1)
    assert context.end_date == date(2026, 12, 31)

    assert len(context.dimensions) == 2

    dimensions = {
        dimension.dimension: dimension.member
        for dimension in context.dimensions
    }

    assert dimensions[
        "de-gaap-ci:dim_taxTrans"
    ] == "de-gaap-ci:dim_comBal"

    assert dimensions[
        "de-gaap-ci:dim_changes.nt.ass.gross_short"
    ] == "de-gaap-ci:bs.ass.fixAss.tan.otherEquipm"


def test_rejects_unsupported_fixed_asset_position() -> None:
    """Nicht unterstützte Anlagenpositionen werden abgewiesen."""

    taxonomy_model = Mock()

    schedule = FixedAssetSchedule(
        rows=(
            FixedAssetScheduleRow(
                position_code="HGB.266.AKTIVA.A.I.1",
                opening_cost=Decimal("1000.00"),
                additions=Decimal("0.00"),
                disposals=Decimal("0.00"),
                current_depreciation=Decimal("0.00"),
                accumulated_depreciation=Decimal("0.00"),
                closing_book_value=Decimal("1000.00"),
            ),
        )
    )

    builder = FixedAssetScheduleFactBuilder(
        taxonomy_model=taxonomy_model
    )

    with pytest.raises(
        ValueError,
        match="HGB.266.AKTIVA.A.I.1",
    ):
        builder.build(
            schedule=schedule,
            entity_identifier="123456789",
            entity_scheme="http://example.com",
            fiscal_year_start=date(2026, 1, 1),
            fiscal_year_end=date(2026, 12, 31),
            unit=TaxonomyUnit(
                measure="iso4217:EUR"
            ),
        )

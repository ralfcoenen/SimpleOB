"""Tests für die HGBM-Ergänzung des Anlagenspiegels."""

from datetime import date
from decimal import Decimal

import pytest

from simpleob.eric.bilanz_generation.hgbm_fixed_asset_schedule_builder import (
    HgbmFixedAssetScheduleBuilder,
)
from simpleob.taxonomy.concept import (
    TaxonomyBalance,
    TaxonomyConcept,
    TaxonomyPeriodType,
)
from simpleob.taxonomy.context import (
    TaxonomyContext,
    TaxonomyDimension,
)
from simpleob.taxonomy.fact import TaxonomyFact
from simpleob.taxonomy.unit import TaxonomyUnit
from simpleob.taxonomy.xbrl_writer import TaxonomyXbrlWriter


@pytest.mark.parametrize(
    (
        "concept_name",
        "current_difference",
        "previous_difference",
        "expected",
    ),
    [
        (
            "accDepr.beginning",
            Decimal("-83.33"),
            Decimal("0.00"),
            Decimal("0.00"),
        ),
        (
            "accDepr.DeprPeriod.regular",
            Decimal("-83.33"),
            Decimal("0.00"),
            Decimal("-83.33"),
        ),
        (
            "accDepr.DeprPeriod",
            Decimal("-83.33"),
            Decimal("0.00"),
            Decimal("-83.33"),
        ),
        (
            "accDepr",
            Decimal("-83.33"),
            Decimal("0.00"),
            Decimal("-83.33"),
        ),
        (
            "all",
            Decimal("-83.33"),
            Decimal("0.00"),
            Decimal("83.33"),
        ),
        (
            "accDepr.beginning",
            Decimal("-83.33"),
            Decimal("-83.33"),
            Decimal("-83.33"),
        ),
        (
            "accDepr.DeprPeriod.regular",
            Decimal("-83.33"),
            Decimal("-83.33"),
            Decimal("-83.33"),
        ),
        (
            "accDepr.DeprPeriod",
            Decimal("-83.33"),
            Decimal("-83.33"),
            Decimal("-83.33"),
        ),
        (
            "accDepr",
            Decimal("-83.33"),
            Decimal("-83.33"),
            Decimal("-166.66"),
        ),
        (
            "all",
            Decimal("-83.33"),
            Decimal("-83.33"),
            Decimal("166.66"),
        ),
        (
            "grossCost.beginning",
            Decimal("-83.33"),
            Decimal("-83.33"),
            Decimal("0.00"),
        ),
        (
            "gross.addition",
            Decimal("-83.33"),
            Decimal("-83.33"),
            Decimal("0.00"),
        ),
        (
            "gross.release",
            Decimal("-83.33"),
            Decimal("-83.33"),
            Decimal("0.00"),
        ),
        (
            "gross",
            Decimal("-83.33"),
            Decimal("-83.33"),
            Decimal("0.00"),
        ),
        (
            "accDepr.release",
            Decimal("-83.33"),
            Decimal("-83.33"),
            Decimal("0.00"),
        ),
    ],
)
def test_difference_for_eric_confirmed_bal_fact(
    concept_name: str,
    current_difference: Decimal,
    previous_difference: Decimal,
    expected: Decimal,
) -> None:
    result = HgbmFixedAssetScheduleBuilder._difference_for_concept(
        concept_name=concept_name,
        current_depreciation_difference=current_difference,
        previous_depreciation_difference=previous_difference,
    )

    assert result == expected

def test_rejects_zero_depreciation_reconciliation() -> None:
    with pytest.raises(
        ValueError,
        match="at least one depreciation difference must be non-zero",
    ):
        HgbmFixedAssetScheduleBuilder.build(
            commercial_contexts={},
            commercial_facts=(),
            commercial_nil_facts=(),
            current_depreciation_difference=Decimal("0.00"),
            previous_depreciation_difference=Decimal("0.00"),
        )

@pytest.mark.parametrize(
    (
        "current_difference",
        "previous_difference",
        "message",
    ),
    [
        (
            -83.33,
            Decimal("0.00"),
            "current_depreciation_difference must be a Decimal",
        ),
        (
            Decimal("-83.33"),
            -83.33,
            "previous_depreciation_difference must be a Decimal",
        ),
    ],
)
def test_rejects_non_decimal_depreciation_difference(
    current_difference,
    previous_difference,
    message: str,
) -> None:
    with pytest.raises(
        TypeError,
        match=message,
    ):
        HgbmFixedAssetScheduleBuilder.build(
            commercial_contexts={},
            commercial_facts=(),
            commercial_nil_facts=(),
            current_depreciation_difference=current_difference,
            previous_depreciation_difference=previous_difference,
        )

def test_builds_confirmed_v10_bal_values_with_real_objects() -> None:
    unit = TaxonomyUnit.eur()

    dimensions = (
        TaxonomyDimension(
            dimension_name="de-gaap-ci:dim_taxTrans",
            member_name="de-gaap-ci:dim_comBal",
        ),
        TaxonomyDimension(
            dimension_name=(
                "de-gaap-ci:dim_changes.nt.ass.gross"
            ),
            member_name=(
                "de-gaap-ci:"
                "bs.ass.fixAss.tan.otherEquipm.otherbga"
            ),
        ),
    )

    commercial_context = TaxonomyContext(
        entity_identifier="TEST-UG",
        entity_scheme="urn:simpleob:test",
        period_type=TaxonomyPeriodType.DURATION,
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
        dimensions=dimensions,
    )

    depreciation_concept = TaxonomyConcept(
        name="accDepr",
        concept_id="test-accDepr",
        type_name="xbrli:monetaryItemType",
        substitution_group="xbrli:item",
        period_type=TaxonomyPeriodType.DURATION,
        balance=TaxonomyBalance.NONE,
        abstract=False,
        nillable=True,
    )

    carrying_amount_concept = TaxonomyConcept(
        name="all",
        concept_id="test-all",
        type_name="xbrli:monetaryItemType",
        substitution_group="xbrli:item",
        period_type=TaxonomyPeriodType.DURATION,
        balance=TaxonomyBalance.NONE,
        abstract=False,
        nillable=True,
    )

    commercial_facts = (
        TaxonomyFact(
            concept=depreciation_concept,
            amount=Decimal("186.74"),
            context=commercial_context,
            unit=unit,
        ),
        TaxonomyFact(
            concept=carrying_amount_concept,
            amount=Decimal("1493.93"),
            context=commercial_context,
            unit=unit,
        ),
    )

    result = HgbmFixedAssetScheduleBuilder.build(
        commercial_contexts={
            "ctx-fixed-assets-1": commercial_context,
        },
        commercial_facts=commercial_facts,
        commercial_nil_facts=(),
        current_depreciation_difference=Decimal("13.26"),
        previous_depreciation_difference=Decimal("0.00"),
    )

    assert set(result.contexts) == {
        "ctx-fixed-assets-1-diff-tax",
        "ctx-fixed-assets-1-tax",
    }

    difference_context = result.contexts[
        "ctx-fixed-assets-1-diff-tax"
    ]
    tax_context = result.contexts[
        "ctx-fixed-assets-1-tax"
    ]

    assert difference_context.dimensions == (
        TaxonomyDimension(
            dimension_name="de-gaap-ci:dim_taxTrans",
            member_name=(
                "de-gaap-ci:dim_diffComToTaxBal"
            ),
        ),
        dimensions[1],
    )

    assert tax_context.dimensions == (
        TaxonomyDimension(
            dimension_name="de-gaap-ci:dim_taxTrans",
            member_name="de-gaap-ci:dim_taxBal",
        ),
        dimensions[1],
    )

    difference_facts = {
        fact.concept.name: fact
        for fact in result.facts
        if fact.context == difference_context
    }

    tax_facts = {
        fact.concept.name: fact
        for fact in result.facts
        if fact.context == tax_context
    }

    assert difference_facts["accDepr"].amount == Decimal(
        "13.26"
    )
    assert tax_facts["accDepr"].amount == Decimal(
        "200.00"
    )

    assert difference_facts["all"].amount == Decimal(
        "-13.26"
    )
    assert tax_facts["all"].amount == Decimal(
        "1480.67"
    )

    assert (
        difference_facts["accDepr"].context
        is difference_context
    )
    assert tax_facts["accDepr"].context is tax_context

def test_serializes_hgbm_bal_context_and_fact() -> None:
    unit = TaxonomyUnit.eur()

    commercial_context = TaxonomyContext(
        entity_identifier="TEST-UG",
        entity_scheme="urn:simpleob:test",
        period_type=TaxonomyPeriodType.DURATION,
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
        dimensions=(
            TaxonomyDimension(
                dimension_name="de-gaap-ci:dim_taxTrans",
                member_name="de-gaap-ci:dim_comBal",
            ),
            TaxonomyDimension(
                dimension_name=(
                    "de-gaap-ci:dim_changes.nt.ass.gross"
                ),
                member_name=(
                    "de-gaap-ci:"
                    "bs.ass.fixAss.tan.otherEquipm.otherbga"
                ),
            ),
        ),
    )

    concept = TaxonomyConcept(
        name="all",
        concept_id="test-all",
        type_name="xbrli:monetaryItemType",
        substitution_group="xbrli:item",
        period_type=TaxonomyPeriodType.DURATION,
        balance=TaxonomyBalance.NONE,
        abstract=False,
        nillable=True,
    )

    commercial_fact = TaxonomyFact(
        concept=concept,
        amount=Decimal("1493.93"),
        context=commercial_context,
        unit=unit,
    )

    result = HgbmFixedAssetScheduleBuilder.build(
        commercial_contexts={
            "ctx-fixed-assets-1": commercial_context,
        },
        commercial_facts=(commercial_fact,),
        commercial_nil_facts=(),
        current_depreciation_difference=Decimal("13.26"),
        previous_depreciation_difference=Decimal("0.00"),
    )

    difference_context = result.contexts[
        "ctx-fixed-assets-1-diff-tax"
    ]
    tax_context = result.contexts[
        "ctx-fixed-assets-1-tax"
    ]

    difference_fact = next(
        fact
        for fact in result.facts
        if fact.context is difference_context
    )
    tax_fact = next(
        fact
        for fact in result.facts
        if fact.context is tax_context
    )

    writer = TaxonomyXbrlWriter()

    difference_context_xml = writer.context_element(
        context=difference_context,
        context_id="ctx-fixed-assets-1-diff-tax",
    )
    tax_context_xml = writer.context_element(
        context=tax_context,
        context_id="ctx-fixed-assets-1-tax",
    )

    difference_fact_xml = writer.fact_element(
        fact=difference_fact,
        context_id="ctx-fixed-assets-1-diff-tax",
        unit_id="EUR",
        namespace="http://www.xbrl.de/taxonomies/de-gaap-ci",
    )
    tax_fact_xml = writer.fact_element(
        fact=tax_fact,
        context_id="ctx-fixed-assets-1-tax",
        unit_id="EUR",
        namespace="http://www.xbrl.de/taxonomies/de-gaap-ci",
    )

    difference_members = tuple(
        element.text
        for element in difference_context_xml.iter()
        if element.tag.endswith("explicitMember")
    )
    tax_members = tuple(
        element.text
        for element in tax_context_xml.iter()
        if element.tag.endswith("explicitMember")
    )

    assert difference_members == (
        "de-gaap-ci:dim_diffComToTaxBal",
        (
            "de-gaap-ci:"
            "bs.ass.fixAss.tan.otherEquipm.otherbga"
        ),
    )

    assert tax_members == (
        "de-gaap-ci:dim_taxBal",
        (
            "de-gaap-ci:"
            "bs.ass.fixAss.tan.otherEquipm.otherbga"
        ),
    )

    assert difference_fact_xml.attrib["contextRef"] == (
        "ctx-fixed-assets-1-diff-tax"
    )
    assert difference_fact_xml.text == "-13.26"

    assert tax_fact_xml.attrib["contextRef"] == (
        "ctx-fixed-assets-1-tax"
    )
    assert tax_fact_xml.text == "1480.67"

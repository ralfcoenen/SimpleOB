"""Tests für das geladene Taxonomiemodell."""
from decimal import Decimal

import pytest

from openbilanz.taxonomy.concept import (
    TaxonomyBalance,
    TaxonomyConcept,
    TaxonomyPeriodType,
)
from openbilanz.taxonomy.concept_set import TaxonomyConceptSet
from openbilanz.taxonomy.label import (
    TaxonomyLabel,
    TaxonomyLabelRole,
)
from openbilanz.taxonomy.label_set import TaxonomyLabelSet
from openbilanz.taxonomy.model import TaxonomyModel
from openbilanz.taxonomy.presentation import (
    TaxonomyPresentationRelation,
)
from openbilanz.taxonomy.presentation_set import (
    TaxonomyPresentationSet,
)


def test_taxonomy_model_returns_labels_for_concept() -> None:
    concept = TaxonomyConcept(
        name="bs.ass",
        concept_id="de-gaap-ci_bs.ass",
        type_name="xbrli:monetaryItemType",
        substitution_group="xbrli:item",
        period_type=TaxonomyPeriodType.INSTANT,
        balance=TaxonomyBalance.DEBIT,
        abstract=False,
        nillable=True,
    )

    label = TaxonomyLabel(
        concept_id="de-gaap-ci_bs.ass",
        text="Bilanzsumme, Summe Aktiva",
        role=TaxonomyLabelRole.LABEL,
        role_uri="http://www.xbrl.org/2003/role/label",
        language="de",
    )

    model = TaxonomyModel(
        concepts=TaxonomyConceptSet(
            concepts=(concept,),
        ),
        labels=TaxonomyLabelSet(
            labels=(label,),
        ),
        presentation=TaxonomyPresentationSet(
            relations=(),
        ),
    )

    assert model.labels_for(
        "de-gaap-ci_bs.ass"
    ) == (label,)

def test_taxonomy_model_rejects_labels_for_unknown_concepts() -> None:
    """Labels dürfen nur auf vorhandene Concepts verweisen."""

    concept = TaxonomyConcept(
        name="bs.ass",
        concept_id="de-gaap-ci_bs.ass",
        type_name="xbrli:monetaryItemType",
        substitution_group="xbrli:item",
        period_type=TaxonomyPeriodType.INSTANT,
        balance=TaxonomyBalance.DEBIT,
        abstract=False,
        nillable=True,
    )

    orphan_label = TaxonomyLabel(
        concept_id="de-gaap-ci_unknown",
        text="Unbekannt",
        role=TaxonomyLabelRole.LABEL,
        role_uri="http://www.xbrl.org/2003/role/label",
        language="de",
    )

    with pytest.raises(
        ValueError,
        match="label references unknown concept",
    ):
        TaxonomyModel(
            concepts=TaxonomyConceptSet(
                concepts=(concept,),
            ),
            labels=TaxonomyLabelSet(
                labels=(orphan_label,),
            ),
            presentation=TaxonomyPresentationSet(
                relations=(),
            ),
        )

def test_taxonomy_model_returns_child_concepts_in_presentation_order() -> None:
    assets = TaxonomyConcept(
        name="bs.ass",
        concept_id="concept_assets",
        type_name="xbrli:monetaryItemType",
        substitution_group="xbrli:item",
        period_type=TaxonomyPeriodType.INSTANT,
        balance=TaxonomyBalance.DEBIT,
        abstract=False,
        nillable=True,
    )

    cash = TaxonomyConcept(
        name="bs.ass.cash",
        concept_id="concept_cash",
        type_name="xbrli:monetaryItemType",
        substitution_group="xbrli:item",
        period_type=TaxonomyPeriodType.INSTANT,
        balance=TaxonomyBalance.DEBIT,
        abstract=False,
        nillable=True,
    )

    fixed_assets = TaxonomyConcept(
        name="bs.ass.fixAss",
        concept_id="concept_fixed_assets",
        type_name="xbrli:monetaryItemType",
        substitution_group="xbrli:item",
        period_type=TaxonomyPeriodType.INSTANT,
        balance=TaxonomyBalance.DEBIT,
        abstract=False,
        nillable=True,
    )

    presentation = TaxonomyPresentationSet(
        relations=(
            TaxonomyPresentationRelation(
                parent_concept_id="concept_assets",
                child_concept_id="concept_fixed_assets",
                order=Decimal("2"),
                role_uri="http://example.test/role/balanceSheet",
                preferred_label_role_uri=None,
            ),
            TaxonomyPresentationRelation(
                parent_concept_id="concept_assets",
                child_concept_id="concept_cash",
                order=Decimal("1"),
                role_uri="http://example.test/role/balanceSheet",
                preferred_label_role_uri=None,
            ),
        )
    )

    model = TaxonomyModel(
        concepts=TaxonomyConceptSet(
            concepts=(
                assets,
                cash,
                fixed_assets,
            ),
        ),
        labels=TaxonomyLabelSet(
            labels=(),
        ),
        presentation=presentation,
    )

    assert model.children_for(
        "concept_assets",
        role_uri="http://example.test/role/balanceSheet",
    ) == (
        cash,
        fixed_assets,
    )

def test_taxonomy_model_returns_preferred_german_label() -> None:
    """Das deutsche Standardlabel eines Concepts wird geliefert."""

    concept = TaxonomyConcept(
        name="bs.ass",
        concept_id="de-gaap-ci_bs.ass",
        type_name="xbrli:monetaryItemType",
        substitution_group="xbrli:item",
        period_type=TaxonomyPeriodType.INSTANT,
        balance=TaxonomyBalance.DEBIT,
        abstract=False,
        nillable=True,
    )

    terse_label = TaxonomyLabel(
        concept_id="de-gaap-ci_bs.ass",
        text="Summe Aktiva",
        role=TaxonomyLabelRole.TERSE_LABEL,
        role_uri="http://www.xbrl.org/2003/role/terseLabel",
        language="de",
    )

    standard_label = TaxonomyLabel(
        concept_id="de-gaap-ci_bs.ass",
        text="Bilanzsumme, Summe Aktiva",
        role=TaxonomyLabelRole.LABEL,
        role_uri="http://www.xbrl.org/2003/role/label",
        language="de",
    )

    model = TaxonomyModel(
        concepts=TaxonomyConceptSet(
            concepts=(concept,),
        ),
        labels=TaxonomyLabelSet(
            labels=(
                terse_label,
                standard_label,
            ),
        ),
        presentation=TaxonomyPresentationSet(
            relations=(),
        ),
    )

    assert model.label_for(
        "de-gaap-ci_bs.ass"
    ) == "Bilanzsumme, Summe Aktiva"

def test_taxonomy_model_falls_back_to_other_german_label() -> None:
    """Ohne Standardlabel wird ein anderes deutsches Label verwendet."""

    concept = TaxonomyConcept(
        name="bs.ass",
        concept_id="de-gaap-ci_bs.ass",
        type_name="xbrli:monetaryItemType",
        substitution_group="xbrli:item",
        period_type=TaxonomyPeriodType.INSTANT,
        balance=TaxonomyBalance.DEBIT,
        abstract=False,
        nillable=True,
    )

    terse_label = TaxonomyLabel(
        concept_id="de-gaap-ci_bs.ass",
        text="Summe Aktiva",
        role=TaxonomyLabelRole.TERSE_LABEL,
        role_uri="http://www.xbrl.org/2003/role/terseLabel",
        language="de",
    )

    english_label = TaxonomyLabel(
        concept_id="de-gaap-ci_bs.ass",
        text="Total assets",
        role=TaxonomyLabelRole.LABEL,
        role_uri="http://www.xbrl.org/2003/role/label",
        language="en",
    )

    model = TaxonomyModel(
        concepts=TaxonomyConceptSet(
            concepts=(concept,),
        ),
        labels=TaxonomyLabelSet(
            labels=(
                english_label,
                terse_label,
            ),
        ),
        presentation=TaxonomyPresentationSet(
            relations=(),
        ),
    )

    assert model.label_for(
        "de-gaap-ci_bs.ass"
    ) == "Summe Aktiva"

def test_taxonomy_model_returns_none_without_german_label() -> None:
    """Ohne deutsches Label wird None geliefert."""

    concept = TaxonomyConcept(
        name="bs.ass",
        concept_id="de-gaap-ci_bs.ass",
        type_name="xbrli:monetaryItemType",
        substitution_group="xbrli:item",
        period_type=TaxonomyPeriodType.INSTANT,
        balance=TaxonomyBalance.DEBIT,
        abstract=False,
        nillable=True,
    )

    english_label = TaxonomyLabel(
        concept_id="de-gaap-ci_bs.ass",
        text="Total assets",
        role=TaxonomyLabelRole.LABEL,
        role_uri="http://www.xbrl.org/2003/role/label",
        language="en",
    )

    model = TaxonomyModel(
        concepts=TaxonomyConceptSet(
            concepts=(concept,),
        ),
        labels=TaxonomyLabelSet(
            labels=(english_label,),
        ),
        presentation=TaxonomyPresentationSet(
            relations=(),
        ),
    )

    assert model.label_for(
        "de-gaap-ci_bs.ass"
    ) is None


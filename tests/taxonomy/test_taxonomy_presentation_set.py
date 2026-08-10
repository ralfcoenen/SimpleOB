"""Tests für die Abfrage von Presentation-Beziehungen."""

from decimal import Decimal

from openbilanz.taxonomy.presentation import (
    TaxonomyPresentationRelation,
)
from openbilanz.taxonomy.presentation_set import (
    TaxonomyPresentationSet,
)


def test_relations_can_be_filtered_by_role() -> None:
    """Presentation-Beziehungen können nach Rolle gefiltert werden."""

    balance_relation = TaxonomyPresentationRelation(
        parent_concept_id="concept_assets",
        child_concept_id="concept_fixed_assets",
        order=Decimal("1"),
        role_uri="http://example.test/role/balanceSheet",
        preferred_label_role_uri=None,
    )

    income_relation = TaxonomyPresentationRelation(
        parent_concept_id="concept_income",
        child_concept_id="concept_revenue",
        order=Decimal("1"),
        role_uri="http://example.test/role/incomeStatement",
        preferred_label_role_uri=None,
    )

    presentation_set = TaxonomyPresentationSet(
        relations=(
            balance_relation,
            income_relation,
        )
    )

    assert presentation_set.relations_for_role(
        "http://example.test/role/balanceSheet"
    ) == (
        balance_relation,
    )


def test_children_of_returns_children_sorted_by_order() -> None:
    """Kinder eines Concepts werden nach Presentation-Order sortiert."""

    first = TaxonomyPresentationRelation(
        parent_concept_id="concept_assets",
        child_concept_id="concept_cash",
        order=Decimal("1"),
        role_uri="http://example.test/role/balanceSheet",
        preferred_label_role_uri=None,
    )

    second = TaxonomyPresentationRelation(
        parent_concept_id="concept_assets",
        child_concept_id="concept_fixed_assets",
        order=Decimal("2"),
        role_uri="http://example.test/role/balanceSheet",
        preferred_label_role_uri=None,
    )

    presentation_set = TaxonomyPresentationSet(
        relations=(
            second,
            first,
        )
    )

    assert presentation_set.children_of(
        "concept_assets",
        role_uri="http://example.test/role/balanceSheet",
    ) == (
        first,
        second,
    )

def test_root_concepts_for_role_returns_top_level_parents() -> None:
    """Die Wurzel-Concepts einer Presentation-Rolle werden ermittelt."""

    root_to_first = TaxonomyPresentationRelation(
        parent_concept_id="concept_root",
        child_concept_id="concept_first",
        order=Decimal("1"),
        role_uri="http://example.test/role/balanceSheet",
        preferred_label_role_uri=None,
    )

    root_to_second = TaxonomyPresentationRelation(
        parent_concept_id="concept_root",
        child_concept_id="concept_second",
        order=Decimal("2"),
        role_uri="http://example.test/role/balanceSheet",
        preferred_label_role_uri=None,
    )

    first_to_child = TaxonomyPresentationRelation(
        parent_concept_id="concept_first",
        child_concept_id="concept_child",
        order=Decimal("1"),
        role_uri="http://example.test/role/balanceSheet",
        preferred_label_role_uri=None,
    )

    presentation_set = TaxonomyPresentationSet(
        relations=(
            root_to_first,
            root_to_second,
            first_to_child,
        )
    )

    assert presentation_set.root_concepts_for_role(
        "http://example.test/role/balanceSheet"
    ) == (
        "concept_root",
    )



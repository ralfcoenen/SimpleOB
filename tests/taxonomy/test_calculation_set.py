"""Tests für Calculation-Nachfolger und -Pfade."""

from decimal import Decimal

from simpleob.taxonomy.calculation import TaxonomyCalculationRelation
from simpleob.taxonomy.calculation_set import TaxonomyCalculationSet


def _relation(
    parent: str,
    child: str,
    *,
    role: str = "role-a",
    weight: str = "1",
) -> TaxonomyCalculationRelation:
    return TaxonomyCalculationRelation(
        parent_concept_id=parent,
        child_concept_id=child,
        order=Decimal("1"),
        weight=Decimal(weight),
        role_uri=role,
    )


def test_finds_transitive_descendants_and_calculation_path() -> None:
    root_to_subtotal = _relation("root", "subtotal")
    subtotal_to_leaf = _relation("subtotal", "leaf", weight="-1")
    calculation = TaxonomyCalculationSet(
        relations=(
            root_to_subtotal,
            subtotal_to_leaf,
            _relation("unrelated", "other"),
        )
    )

    assert calculation.descendants_of("root") == (
        "leaf",
        "subtotal",
    )
    assert calculation.paths_between("root", "leaf") == (
        (root_to_subtotal, subtotal_to_leaf),
    )
    assert calculation.paths_between("root", "other") == ()


def test_does_not_join_calculation_edges_from_different_roles() -> None:
    calculation = TaxonomyCalculationSet(
        relations=(
            _relation("root", "subtotal", role="role-a"),
            _relation("subtotal", "leaf", role="role-b"),
        )
    )

    assert calculation.descendants_of("root") == ("subtotal",)
    assert calculation.paths_between("root", "leaf") == ()

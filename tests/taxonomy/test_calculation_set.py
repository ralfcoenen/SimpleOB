"""Tests für Calculation-Nachfolger und -Pfade."""

from decimal import Decimal

import pytest

from simpleob.taxonomy.calculation import TaxonomyCalculationRelation
from simpleob.taxonomy.calculation_set import TaxonomyCalculationSet
from simpleob.taxonomy.errors import (
    AmbiguousCalculationPathError,
    CalculationPathNotFoundError,
)


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


def test_unique_path_reuses_calculation_paths_between():
    first = _relation("root", "leaf")
    calculation = TaxonomyCalculationSet((first,))

    assert calculation.unique_path_between("root", "leaf") == (first,)


def test_unique_path_rejects_missing_path():
    calculation = TaxonomyCalculationSet(())

    with pytest.raises(
        CalculationPathNotFoundError,
        match="kein Calculation-Pfad",
    ):
        calculation.unique_path_between("root", "leaf")


def test_unique_path_rejects_multiple_paths():
    calculation = TaxonomyCalculationSet(
        (
            _relation("root", "left"),
            _relation("left", "leaf"),
            _relation("root", "right"),
            _relation("right", "leaf"),
        )
    )

    with pytest.raises(
        AmbiguousCalculationPathError,
        match="mehrere Calculation-Pfade",
    ):
        calculation.unique_path_between("root", "leaf")

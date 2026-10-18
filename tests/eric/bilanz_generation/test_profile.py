"""Tests für versionierbare E-Bilanz-Profile."""

import pytest

from simpleob.eric.bilanz_generation.fact_plan import (
    FactPlan,
    FactPlanNode,
    FactPlanState,
)
from simpleob.eric.bilanz_generation.profile import (
    BilanzProfileDelta,
    BilanzProfileResolver,
    ProfileChange,
    ProfileChangeType,
)


def _base_plan() -> FactPlan:
    return FactPlan(
        nodes=(
            FactPlanNode(
                concept_name="concept.a",
                state=FactPlanState.VALUE,
            ),
            FactPlanNode(
                concept_name="concept.b",
                state=FactPlanState.NIL,
            ),
        ),
    )


def test_profile_delta_adds_node() -> None:
    delta = BilanzProfileDelta(
        taxonomy_version="6.9",
        changes=(
            ProfileChange(
                change_type=ProfileChangeType.ADD,
                concept_name="concept.c",
                node=FactPlanNode(
                    concept_name="concept.c",
                    state=FactPlanState.VALUE_OR_NIL,
                ),
            ),
        ),
    )

    profile = BilanzProfileResolver.apply_delta(
        base_plan=_base_plan(),
        delta=delta,
    )

    assert profile.taxonomy_version == "6.9"

    node = profile.fact_plan.node_for("concept.c")

    assert node is not None
    assert node.state is FactPlanState.VALUE_OR_NIL


def test_profile_delta_replaces_node() -> None:
    delta = BilanzProfileDelta(
        taxonomy_version="6.9",
        changes=(
            ProfileChange(
                change_type=ProfileChangeType.REPLACE,
                concept_name="concept.b",
                node=FactPlanNode(
                    concept_name="concept.b",
                    state=FactPlanState.CONDITIONAL,
                ),
            ),
        ),
    )

    profile = BilanzProfileResolver.apply_delta(
        base_plan=_base_plan(),
        delta=delta,
    )

    node = profile.fact_plan.node_for("concept.b")

    assert node is not None
    assert node.state is FactPlanState.CONDITIONAL


def test_profile_delta_removes_node() -> None:
    delta = BilanzProfileDelta(
        taxonomy_version="6.9",
        changes=(
            ProfileChange(
                change_type=ProfileChangeType.REMOVE,
                concept_name="concept.b",
            ),
        ),
    )

    profile = BilanzProfileResolver.apply_delta(
        base_plan=_base_plan(),
        delta=delta,
    )

    assert profile.fact_plan.node_for("concept.b") is None
    assert profile.fact_plan.node_for("concept.a") is not None


def test_profile_delta_applies_multiple_changes_in_order() -> None:
    delta = BilanzProfileDelta(
        taxonomy_version="6.9",
        changes=(
            ProfileChange(
                change_type=ProfileChangeType.REPLACE,
                concept_name="concept.a",
                node=FactPlanNode(
                    concept_name="concept.a",
                    state=FactPlanState.CONDITIONAL,
                ),
            ),
            ProfileChange(
                change_type=ProfileChangeType.REMOVE,
                concept_name="concept.b",
            ),
            ProfileChange(
                change_type=ProfileChangeType.ADD,
                concept_name="concept.c",
                node=FactPlanNode(
                    concept_name="concept.c",
                    state=FactPlanState.NIL,
                ),
            ),
        ),
    )

    profile = BilanzProfileResolver.apply_delta(
        base_plan=_base_plan(),
        delta=delta,
    )

    assert tuple(
        node.concept_name
        for node in profile.fact_plan.nodes
    ) == (
        "concept.a",
        "concept.c",
    )

    concept_a = profile.fact_plan.node_for("concept.a")

    assert concept_a is not None
    assert concept_a.state is FactPlanState.CONDITIONAL


def test_add_rejects_existing_concept() -> None:
    delta = BilanzProfileDelta(
        taxonomy_version="6.9",
        changes=(
            ProfileChange(
                change_type=ProfileChangeType.ADD,
                concept_name="concept.a",
                node=FactPlanNode(
                    concept_name="concept.a",
                    state=FactPlanState.NIL,
                ),
            ),
        ),
    )

    with pytest.raises(
        ValueError,
        match="ADD change requires a new concept",
    ):
        BilanzProfileResolver.apply_delta(
            base_plan=_base_plan(),
            delta=delta,
        )


def test_replace_rejects_unknown_concept() -> None:
    delta = BilanzProfileDelta(
        taxonomy_version="6.9",
        changes=(
            ProfileChange(
                change_type=ProfileChangeType.REPLACE,
                concept_name="concept.unknown",
                node=FactPlanNode(
                    concept_name="concept.unknown",
                    state=FactPlanState.NIL,
                ),
            ),
        ),
    )

    with pytest.raises(
        ValueError,
        match="REPLACE change requires an existing concept",
    ):
        BilanzProfileResolver.apply_delta(
            base_plan=_base_plan(),
            delta=delta,
        )


def test_remove_rejects_unknown_concept() -> None:
    delta = BilanzProfileDelta(
        taxonomy_version="6.9",
        changes=(
            ProfileChange(
                change_type=ProfileChangeType.REMOVE,
                concept_name="concept.unknown",
            ),
        ),
    )

    with pytest.raises(
        ValueError,
        match="REMOVE change requires an existing concept",
    ):
        BilanzProfileResolver.apply_delta(
            base_plan=_base_plan(),
            delta=delta,
        )


def test_add_requires_node() -> None:
    with pytest.raises(
        TypeError,
        match="ADD and REPLACE changes require a FactPlanNode",
    ):
        ProfileChange(
            change_type=ProfileChangeType.ADD,
            concept_name="concept.c",
        )


def test_remove_rejects_node() -> None:
    with pytest.raises(
        ValueError,
        match="REMOVE change must not contain a node",
    ):
        ProfileChange(
            change_type=ProfileChangeType.REMOVE,
            concept_name="concept.a",
            node=FactPlanNode(
                concept_name="concept.a",
                state=FactPlanState.NIL,
            ),
        )


def test_change_rejects_mismatching_node_concept() -> None:
    with pytest.raises(
        ValueError,
        match="node concept_name must match change concept_name",
    ):
        ProfileChange(
            change_type=ProfileChangeType.REPLACE,
            concept_name="concept.a",
            node=FactPlanNode(
                concept_name="concept.b",
                state=FactPlanState.NIL,
            ),
        )


def test_delta_rejects_duplicate_concept_changes() -> None:
    with pytest.raises(
        ValueError,
        match="delta concept names must be unique",
    ):
        BilanzProfileDelta(
            taxonomy_version="6.9",
            changes=(
                ProfileChange(
                    change_type=ProfileChangeType.REMOVE,
                    concept_name="concept.a",
                ),
                ProfileChange(
                    change_type=ProfileChangeType.REMOVE,
                    concept_name="concept.a",
                ),
            ),
        )

"""Tests für den strukturierten E-Bilanz-Fact-Plan."""

import pytest

from openbilanz.eric.bilanz_generation.fact_plan import (
    FactPlan,
    FactPlanNode,
    FactPlanState,
)

ST13_CONCEPT = (
    "genInfo.company.id.idNo.type.companyId.ST13"
)


def test_fact_plan_state_contains_supported_states() -> None:
    assert tuple(FactPlanState) == (
        FactPlanState.VALUE,
        FactPlanState.NIL,
        FactPlanState.VALUE_OR_NIL,
        FactPlanState.CONDITIONAL,
        FactPlanState.REQUIRED_NIL_TUPLE,
        FactPlanState.UNSUPPORTED,
    )


def test_fact_plan_node_accepts_simple_value() -> None:
    node = FactPlanNode(
        concept_name=ST13_CONCEPT,
        state=FactPlanState.VALUE,
    )

    assert node.concept_name == ST13_CONCEPT
    assert node.state is FactPlanState.VALUE
    assert node.children == ()


def test_fact_plan_node_accepts_required_nil_tuple() -> None:
    node = FactPlanNode(
        concept_name="genInfo.report.id.accordingTo",
        state=FactPlanState.REQUIRED_NIL_TUPLE,
        children=(
            FactPlanNode(
                concept_name="genInfo.report.id.accordingTo.name",
                state=FactPlanState.NIL,
            ),
            FactPlanNode(
                concept_name="genInfo.report.id.accordingTo.yearEnd",
                state=FactPlanState.NIL,
            ),
        ),
    )

    assert node.state is FactPlanState.REQUIRED_NIL_TUPLE
    assert len(node.children) == 2


def test_required_nil_tuple_requires_children() -> None:
    with pytest.raises(
        ValueError,
        match="required NIL tuple must contain children",
    ):
        FactPlanNode(
            concept_name="genInfo.report.id.accordingTo",
            state=FactPlanState.REQUIRED_NIL_TUPLE,
        )


def test_fact_plan_supports_nested_tuples() -> None:
    plan = FactPlan(
        nodes=(
            FactPlanNode(
                concept_name="genInfo.report.id.accordingTo",
                state=FactPlanState.REQUIRED_NIL_TUPLE,
                children=(
                    FactPlanNode(
                        concept_name=(
                            "genInfo.report.id.accordingTo.idNo"
                        ),
                        state=FactPlanState.REQUIRED_NIL_TUPLE,
                        children=(
                            FactPlanNode(
                                concept_name=ST13_CONCEPT,
                                state=FactPlanState.NIL,
                            ),
                        ),
                    ),
                ),
            ),
        ),
    )

    st13 = plan.node_for(ST13_CONCEPT)

    assert st13 is not None
    assert st13.state is FactPlanState.NIL


def test_fact_plan_returns_none_for_unknown_concept() -> None:
    plan = FactPlan(
        nodes=(
            FactPlanNode(
                concept_name=ST13_CONCEPT,
                state=FactPlanState.VALUE,
            ),
        ),
    )

    assert plan.node_for("unknown.concept") is None


def test_fact_plan_rejects_ambiguous_concept_lookup() -> None:
    plan = FactPlan(
        nodes=(
            FactPlanNode(
                concept_name="company.identifiers",
                state=FactPlanState.CONDITIONAL,
                children=(
                    FactPlanNode(
                        concept_name=ST13_CONCEPT,
                        state=FactPlanState.VALUE,
                    ),
                ),
            ),
            FactPlanNode(
                concept_name="report.accordingTo",
                state=FactPlanState.REQUIRED_NIL_TUPLE,
                children=(
                    FactPlanNode(
                        concept_name=ST13_CONCEPT,
                        state=FactPlanState.NIL,
                    ),
                ),
            ),
        ),
    )

    with pytest.raises(
        ValueError,
        match="concept name is ambiguous",
    ):
        plan.node_for(ST13_CONCEPT)


def test_fact_plan_resolves_reused_concept_by_path() -> None:
    plan = FactPlan(
        nodes=(
            FactPlanNode(
                concept_name="company.identifiers",
                state=FactPlanState.CONDITIONAL,
                children=(
                    FactPlanNode(
                        concept_name=ST13_CONCEPT,
                        state=FactPlanState.VALUE,
                    ),
                ),
            ),
            FactPlanNode(
                concept_name="report.accordingTo",
                state=FactPlanState.REQUIRED_NIL_TUPLE,
                children=(
                    FactPlanNode(
                        concept_name=ST13_CONCEPT,
                        state=FactPlanState.NIL,
                    ),
                ),
            ),
        ),
    )

    company_st13 = plan.node_for_path(
        "company.identifiers",
        ST13_CONCEPT,
    )
    according_to_st13 = plan.node_for_path(
        "report.accordingTo",
        ST13_CONCEPT,
    )

    assert company_st13 is not None
    assert company_st13.state is FactPlanState.VALUE

    assert according_to_st13 is not None
    assert according_to_st13.state is FactPlanState.NIL


def test_fact_plan_returns_none_for_unknown_path() -> None:
    plan = FactPlan(
        nodes=(
            FactPlanNode(
                concept_name="company.identifiers",
                state=FactPlanState.CONDITIONAL,
                children=(
                    FactPlanNode(
                        concept_name=ST13_CONCEPT,
                        state=FactPlanState.VALUE,
                    ),
                ),
            ),
        ),
    )

    assert (
        plan.node_for_path(
            "company.identifiers",
            "unknown.concept",
        )
        is None
    )


def test_fact_plan_rejects_empty_path() -> None:
    plan = FactPlan(nodes=())

    with pytest.raises(
        ValueError,
        match="concept path must not be empty",
    ):
        plan.node_for_path()


def test_fact_plan_rejects_duplicate_top_level_concepts() -> None:
    node = FactPlanNode(
        concept_name=ST13_CONCEPT,
        state=FactPlanState.VALUE,
    )

    with pytest.raises(
        ValueError,
        match="top-level concept names must be unique",
    ):
        FactPlan(
            nodes=(
                node,
                node,
            ),
        )


def test_fact_plan_node_rejects_duplicate_children() -> None:
    child = FactPlanNode(
        concept_name="genInfo.report.id.accordingTo.name",
        state=FactPlanState.NIL,
    )

    with pytest.raises(
        ValueError,
        match="child concept names must be unique",
    ):
        FactPlanNode(
            concept_name="genInfo.report.id.accordingTo",
            state=FactPlanState.REQUIRED_NIL_TUPLE,
            children=(
                child,
                child,
            ),
        )


def test_fact_plan_rejects_blank_concept_name() -> None:
    with pytest.raises(
        ValueError,
        match="concept_name must not be blank",
    ):
        FactPlanNode(
            concept_name="   ",
            state=FactPlanState.VALUE,
        )


def test_fact_plan_rejects_invalid_state() -> None:
    with pytest.raises(
        TypeError,
        match="state must be a FactPlanState",
    ):
        FactPlanNode(
            concept_name=ST13_CONCEPT,
            state="value",  # type: ignore[arg-type]
        )


def test_fact_plan_with_conditional_child_adds_child_to_existing_parent() -> None:
    plan = FactPlan(
        nodes=(
            FactPlanNode(
                concept_name="parent",
                state=FactPlanState.CONDITIONAL,
            ),
        )
    )

    extended = plan.with_conditional_child(
        parent_concept_name="parent",
        child_concept_name="parent.child",
    )

    parent = extended.node_for(
        "parent"
    )

    assert parent is not None
    assert parent.state is FactPlanState.CONDITIONAL
    assert len(parent.children) == 1
    assert parent.children[0] == FactPlanNode(
        concept_name="parent.child",
        state=FactPlanState.CONDITIONAL,
    )

    assert extended.path_for(
        "parent.child"
    ) == (
        "parent",
        "parent.child",
    )

    assert plan.node_for(
        "parent.child"
    ) is None

    assert plan.path_for(
        "parent.child"
    ) is None

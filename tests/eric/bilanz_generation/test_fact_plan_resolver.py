"""Tests für die Auflösung eines E-Bilanz-Fact-Plans."""

from datetime import date
from decimal import Decimal

import pytest

from openbilanz.eric.bilanz_generation.fact_plan import (
    FactPlan,
    FactPlanNode,
    FactPlanState,
)
from openbilanz.eric.bilanz_generation.fact_plan_resolver import (
    FactPlanResolver,
)
from openbilanz.taxonomy.concept import (
    TaxonomyBalance,
    TaxonomyConcept,
    TaxonomyPeriodType,
)
from openbilanz.taxonomy.concept_set import TaxonomyConceptSet
from openbilanz.taxonomy.context import TaxonomyContext
from openbilanz.taxonomy.fact import TaxonomyFact
from openbilanz.taxonomy.nil_fact import TaxonomyNilFact
from openbilanz.taxonomy.text_fact import TaxonomyTextFact


def _concept(
    *,
    name: str,
    concept_id: str,
    type_name: str,
    period_type: TaxonomyPeriodType = TaxonomyPeriodType.DURATION,
    nillable: bool = True,
    substitution_group: str = "xbrli:item",
) -> TaxonomyConcept:
    return TaxonomyConcept(
        name=name,
        concept_id=concept_id,
        type_name=type_name,
        substitution_group=substitution_group,
        period_type=period_type,
        balance=TaxonomyBalance.NONE,
        abstract=False,
        nillable=nillable,
    )


def _duration_context() -> TaxonomyContext:
    return TaxonomyContext(
        entity_identifier="1234567890123",
        entity_scheme="http://www.elster.de",
        period_type=TaxonomyPeriodType.DURATION,
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
    )


def _contexts() -> dict[
    TaxonomyPeriodType,
    TaxonomyContext,
]:
    return {
        TaxonomyPeriodType.DURATION: _duration_context(),
    }


def test_value_creates_text_fact() -> None:
    concept_name = "genInfo.company.name"

    plan = FactPlan(
        nodes=(
            FactPlanNode(
                concept_name=concept_name,
                state=FactPlanState.VALUE,
            ),
        ),
    )

    concept = _concept(
        name=concept_name,
        concept_id="de-gcd_genInfo.company.name",
        type_name="xbrli:stringItemType",
    )

    resolved = FactPlanResolver.resolve(
        fact_plan=plan,
        concepts=TaxonomyConceptSet(
            concepts=(concept,)
        ),
        contexts=_contexts(),
        values={
            (concept_name,): "Muster UG",
        },
    )

    fact = resolved.nodes[0].fact

    assert isinstance(
        fact,
        TaxonomyTextFact,
    )
    assert fact.value == "Muster UG"


def test_value_creates_monetary_fact_including_zero() -> None:
    concept_name = "is.netIncome"

    plan = FactPlan(
        nodes=(
            FactPlanNode(
                concept_name=concept_name,
                state=FactPlanState.VALUE,
            ),
        ),
    )

    concept = _concept(
        name=concept_name,
        concept_id="de-gaap-ci_is.netIncome",
        type_name="xbrli:monetaryItemType",
    )

    resolved = FactPlanResolver.resolve(
        fact_plan=plan,
        concepts=TaxonomyConceptSet(
            concepts=(concept,)
        ),
        contexts=_contexts(),
        values={
            (concept_name,): Decimal("0"),
        },
    )

    fact = resolved.nodes[0].fact

    assert isinstance(
        fact,
        TaxonomyFact,
    )
    assert fact.amount == Decimal("0")
    assert fact.unit.measure == "iso4217:EUR"
    assert fact.decimals == 2


def test_nil_creates_nil_fact() -> None:
    concept_name = "optional.identifier"

    plan = FactPlan(
        nodes=(
            FactPlanNode(
                concept_name=concept_name,
                state=FactPlanState.NIL,
            ),
        ),
    )

    concept = _concept(
        name=concept_name,
        concept_id="optional_identifier",
        type_name="xbrli:stringItemType",
    )

    resolved = FactPlanResolver.resolve(
        fact_plan=plan,
        concepts=TaxonomyConceptSet(
            concepts=(concept,)
        ),
        contexts=_contexts(),
        values={},
    )

    assert isinstance(
        resolved.nodes[0].fact,
        TaxonomyNilFact,
    )


def test_value_or_nil_uses_nil_when_value_is_absent() -> None:
    concept_name = "optional.identifier"

    plan = FactPlan(
        nodes=(
            FactPlanNode(
                concept_name=concept_name,
                state=FactPlanState.VALUE_OR_NIL,
            ),
        ),
    )

    concept = _concept(
        name=concept_name,
        concept_id="optional_identifier",
        type_name="xbrli:stringItemType",
    )

    resolved = FactPlanResolver.resolve(
        fact_plan=plan,
        concepts=TaxonomyConceptSet(
            concepts=(concept,)
        ),
        contexts=_contexts(),
        values={},
    )

    assert isinstance(
        resolved.nodes[0].fact,
        TaxonomyNilFact,
    )


def test_conditional_node_is_omitted_without_data() -> None:
    concept_name = "conditional.value"

    plan = FactPlan(
        nodes=(
            FactPlanNode(
                concept_name=concept_name,
                state=FactPlanState.CONDITIONAL,
            ),
        ),
    )

    concept = _concept(
        name=concept_name,
        concept_id="conditional_value",
        type_name="xbrli:stringItemType",
    )

    resolved = FactPlanResolver.resolve(
        fact_plan=plan,
        concepts=TaxonomyConceptSet(
            concepts=(concept,)
        ),
        contexts=_contexts(),
        values={},
    )

    assert resolved.nodes == ()


def test_conditional_tuple_is_activated_by_child_value() -> None:
    tuple_name = "genInfo.company.id.idNo"
    st13_name = (
        "genInfo.company.id.idNo.type.companyId.ST13"
    )

    plan = FactPlan(
        nodes=(
            FactPlanNode(
                concept_name=tuple_name,
                state=FactPlanState.CONDITIONAL,
                children=(
                    FactPlanNode(
                        concept_name=st13_name,
                        state=FactPlanState.VALUE,
                    ),
                ),
            ),
        ),
    )

    tuple_concept = _concept(
        name=tuple_name,
        concept_id="de-gcd_idNo",
        type_name=None,
        substitution_group="xbrli:tuple",
    )

    st13_concept = _concept(
        name=st13_name,
        concept_id="de-gcd_ST13",
        type_name="xbrli:stringItemType",
    )

    resolved = FactPlanResolver.resolve(
        fact_plan=plan,
        concepts=TaxonomyConceptSet(
            concepts=(
                tuple_concept,
                st13_concept,
            )
        ),
        contexts=_contexts(),
        values={
            (
                tuple_name,
                st13_name,
            ): "1234567890123",
        },
    )

    tuple_node = resolved.nodes[0]

    assert tuple_node.fact is None
    assert len(tuple_node.children) == 1
    assert isinstance(
        tuple_node.children[0].fact,
        TaxonomyTextFact,
    )


def test_same_concept_can_have_different_states_by_path() -> None:
    company_tuple = "company.identifiers"
    according_to_tuple = "report.accordingTo"
    shared_name = (
        "genInfo.company.id.idNo.type.companyId.ST13"
    )

    plan = FactPlan(
        nodes=(
            FactPlanNode(
                concept_name=company_tuple,
                state=FactPlanState.CONDITIONAL,
                children=(
                    FactPlanNode(
                        concept_name=shared_name,
                        state=FactPlanState.VALUE,
                    ),
                ),
            ),
            FactPlanNode(
                concept_name=according_to_tuple,
                state=FactPlanState.REQUIRED_NIL_TUPLE,
                children=(
                    FactPlanNode(
                        concept_name=shared_name,
                        state=FactPlanState.NIL,
                    ),
                ),
            ),
        ),
    )

    company_concept = _concept(
        name=company_tuple,
        concept_id="company_identifiers",
        type_name=None,
        substitution_group="xbrli:tuple",
    )

    according_to_concept = _concept(
        name=according_to_tuple,
        concept_id="report_according_to",
        type_name=None,
        substitution_group="xbrli:tuple",
    )

    shared_concept = _concept(
        name=shared_name,
        concept_id="de-gcd_ST13",
        type_name="xbrli:stringItemType",
    )

    resolved = FactPlanResolver.resolve(
        fact_plan=plan,
        concepts=TaxonomyConceptSet(
            concepts=(
                company_concept,
                according_to_concept,
                shared_concept,
            )
        ),
        contexts=_contexts(),
        values={
            (
                company_tuple,
                shared_name,
            ): "1234567890123",
        },
    )

    company_st13 = resolved.nodes[0].children[0]
    according_to_st13 = resolved.nodes[1].children[0]

    assert isinstance(
        company_st13.fact,
        TaxonomyTextFact,
    )
    assert isinstance(
        according_to_st13.fact,
        TaxonomyNilFact,
    )


def test_unsupported_node_rejects_supplied_data() -> None:
    concept_name = "unsupported.value"

    plan = FactPlan(
        nodes=(
            FactPlanNode(
                concept_name=concept_name,
                state=FactPlanState.UNSUPPORTED,
            ),
        ),
    )

    with pytest.raises(
        ValueError,
        match="unsupported fact plan node received data",
    ):
        FactPlanResolver.resolve(
            fact_plan=plan,
            concepts=TaxonomyConceptSet(
                concepts=()
            ),
            contexts=_contexts(),
            values={
                (concept_name,): "not allowed",
            },
        )


def test_required_value_must_be_supplied() -> None:
    concept_name = "required.value"

    plan = FactPlan(
        nodes=(
            FactPlanNode(
                concept_name=concept_name,
                state=FactPlanState.VALUE,
            ),
        ),
    )

    concept = _concept(
        name=concept_name,
        concept_id="required_value",
        type_name="xbrli:stringItemType",
    )

    with pytest.raises(
        ValueError,
        match="required fact value is missing",
    ):
        FactPlanResolver.resolve(
            fact_plan=plan,
            concepts=TaxonomyConceptSet(
                concepts=(concept,)
            ),
            contexts=_contexts(),
            values={},
        )

"""Tests für die XBRL-Serialisierung eines ResolvedFactPlan."""

from datetime import date
from decimal import Decimal

import pytest

from simpleob.eric.bilanz_generation.fact_plan import (
    FactPlanNode,
    FactPlanState,
)
from simpleob.eric.bilanz_generation.fact_plan_resolver import (
    ResolvedFactPlan,
    ResolvedFactPlanNode,
)
from simpleob.eric.bilanz_generation.resolved_fact_plan_xbrl_serializer import (
    ResolvedFactPlanXbrlSerializer,
)
from simpleob.taxonomy.concept import (
    TaxonomyBalance,
    TaxonomyConcept,
    TaxonomyPeriodType,
)
from simpleob.taxonomy.context import TaxonomyContext
from simpleob.taxonomy.fact import TaxonomyFact
from simpleob.taxonomy.nil_fact import TaxonomyNilFact
from simpleob.taxonomy.text_fact import TaxonomyTextFact
from simpleob.taxonomy.unit import TaxonomyUnit

GCD_NAMESPACE = (
    "http://www.xbrl.de/taxonomies/"
    "de-gcd-2025-04-01"
)

GAAP_CI_NAMESPACE = (
    "http://www.xbrl.de/taxonomies/"
    "de-gaap-ci-2025-04-01"
)

XSI_NAMESPACE = (
    "http://www.w3.org/2001/XMLSchema-instance"
)


def create_context() -> TaxonomyContext:
    """Erzeugt einen Duration-Kontext für die Serializer-Tests."""

    return TaxonomyContext(
        entity_identifier="DE123456789",
        entity_scheme="urn:openbilanz:test",
        period_type=TaxonomyPeriodType.DURATION,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )


def create_text_concept(
    *,
    name: str,
    prefix: str = "de-gcd",
) -> TaxonomyConcept:
    """Erzeugt ein nichtnumerisches Test-Concept."""

    return TaxonomyConcept(
        name=name,
        concept_id=f"{prefix}_{name}",
        type_name="xbrli:stringItemType",
        substitution_group="xbrli:item",
        period_type=TaxonomyPeriodType.DURATION,
        balance=TaxonomyBalance.NONE,
        abstract=False,
        nillable=True,
    )


def create_tuple_concept(
    *,
    name: str,
    prefix: str = "de-gcd",
) -> TaxonomyConcept:
    """Erzeugt ein strukturelles Test-Concept."""

    return TaxonomyConcept(
        name=name,
        concept_id=f"{prefix}_{name}",
        type_name="xbrli:stringItemType",
        substitution_group="xbrli:tuple",
        period_type=TaxonomyPeriodType.DURATION,
        balance=TaxonomyBalance.NONE,
        abstract=False,
        nillable=True,
    )


def create_monetary_concept(
    *,
    name: str,
) -> TaxonomyConcept:
    """Erzeugt ein monetäres GAAP-CI-Test-Concept."""

    return TaxonomyConcept(
        name=name,
        concept_id=f"de-gaap-ci_{name}",
        type_name="xbrli:monetaryItemType",
        substitution_group="xbrli:item",
        period_type=TaxonomyPeriodType.DURATION,
        balance=TaxonomyBalance.NONE,
        abstract=False,
        nillable=True,
    )


def test_serializer_serializes_text_fact() -> None:
    """Ein Text-Fact wird mit Context und GCD-Namespace serialisiert."""

    context = create_context()

    concept = create_text_concept(
        name="genInfo.company.id.name",
    )

    plan_node = FactPlanNode(
        concept_name=concept.name,
        state=FactPlanState.VALUE,
    )

    resolved = ResolvedFactPlan(
        nodes=(
            ResolvedFactPlanNode(
                plan_node=plan_node,
                concept=concept,
                fact=TaxonomyTextFact(
                    concept=concept,
                    value="Beispiel UG",
                    context=context,
                ),
            ),
        )
    )

    serializer = ResolvedFactPlanXbrlSerializer()

    elements = serializer.serialize(
        resolved_fact_plan=resolved,
        contexts={
            "ctx-duration-2026": context,
        },
        units={},
        taxonomy_namespace=GAAP_CI_NAMESPACE,
        taxonomy_namespaces={
            "de-gcd": GCD_NAMESPACE,
            "de-gaap-ci": GAAP_CI_NAMESPACE,
        },
    )

    assert len(elements) == 1

    element = elements[0]

    assert element.tag == (
        f"{{{GCD_NAMESPACE}}}"
        "genInfo.company.id.name"
    )
    assert element.attrib["contextRef"] == (
        "ctx-duration-2026"
    )
    assert element.text == "Beispiel UG"


def test_serializer_serializes_nested_tuple_structure() -> None:
    """Verschachtelte FactPlan-Tuples bleiben strukturell erhalten."""

    context = create_context()

    according_to_concept = create_tuple_concept(
        name="genInfo.report.id.accordingTo",
    )

    id_no_concept = create_tuple_concept(
        name="genInfo.report.id.accordingTo.idNo",
    )

    st13_concept = create_text_concept(
        name="genInfo.company.id.idNo.type.companyId.ST13",
    )

    st13_plan_node = FactPlanNode(
        concept_name=st13_concept.name,
        state=FactPlanState.NIL,
    )

    id_no_plan_node = FactPlanNode(
        concept_name=id_no_concept.name,
        state=FactPlanState.REQUIRED_NIL_TUPLE,
        children=(
            st13_plan_node,
        ),
    )

    according_to_plan_node = FactPlanNode(
        concept_name=according_to_concept.name,
        state=FactPlanState.REQUIRED_NIL_TUPLE,
        children=(
            id_no_plan_node,
        ),
    )

    resolved = ResolvedFactPlan(
        nodes=(
            ResolvedFactPlanNode(
                plan_node=according_to_plan_node,
                concept=according_to_concept,
                fact=None,
                children=(
                    ResolvedFactPlanNode(
                        plan_node=id_no_plan_node,
                        concept=id_no_concept,
                        fact=None,
                        children=(
                            ResolvedFactPlanNode(
                                plan_node=st13_plan_node,
                                concept=st13_concept,
                                fact=TaxonomyNilFact(
                                    concept=st13_concept,
                                    context=context,
                                ),
                            ),
                        ),
                    ),
                ),
            ),
        )
    )

    serializer = ResolvedFactPlanXbrlSerializer()

    elements = serializer.serialize(
        resolved_fact_plan=resolved,
        contexts={
            "ctx-duration-2026": context,
        },
        units={},
        taxonomy_namespace=GAAP_CI_NAMESPACE,
        taxonomy_namespaces={
            "de-gcd": GCD_NAMESPACE,
            "de-gaap-ci": GAAP_CI_NAMESPACE,
        },
    )

    assert len(elements) == 1

    according_to_element = elements[0]

    assert according_to_element.tag == (
        f"{{{GCD_NAMESPACE}}}"
        "genInfo.report.id.accordingTo"
    )
    assert "contextRef" not in (
        according_to_element.attrib
    )

    id_no_elements = list(
        according_to_element
    )

    assert len(id_no_elements) == 1

    id_no_element = id_no_elements[0]

    assert id_no_element.tag == (
        f"{{{GCD_NAMESPACE}}}"
        "genInfo.report.id.accordingTo.idNo"
    )
    assert "contextRef" not in (
        id_no_element.attrib
    )

    st13_elements = list(
        id_no_element
    )

    assert len(st13_elements) == 1

    st13_element = st13_elements[0]

    assert st13_element.tag == (
        f"{{{GCD_NAMESPACE}}}"
        "genInfo.company.id.idNo.type.companyId.ST13"
    )
    assert st13_element.attrib["contextRef"] == (
        "ctx-duration-2026"
    )
    assert st13_element.attrib[
        f"{{{XSI_NAMESPACE}}}nil"
    ] == "true"


def test_serializer_serializes_numeric_fact_with_unit() -> None:
    """Ein monetärer GAAP-CI-Fact erhält Context, Unit und Decimals."""

    context = create_context()
    unit = TaxonomyUnit.eur()

    concept = create_monetary_concept(
        name="is.netIncome",
    )

    plan_node = FactPlanNode(
        concept_name=concept.name,
        state=FactPlanState.VALUE,
    )

    resolved = ResolvedFactPlan(
        nodes=(
            ResolvedFactPlanNode(
                plan_node=plan_node,
                concept=concept,
                fact=TaxonomyFact(
                    concept=concept,
                    amount=Decimal("4500.00"),
                    context=context,
                    unit=unit,
                    decimals=2,
                ),
            ),
        )
    )

    serializer = ResolvedFactPlanXbrlSerializer()

    elements = serializer.serialize(
        resolved_fact_plan=resolved,
        contexts={
            "ctx-duration-2026": context,
        },
        units={
            "EUR": unit,
        },
        taxonomy_namespace=GAAP_CI_NAMESPACE,
        taxonomy_namespaces={
            "de-gcd": GCD_NAMESPACE,
            "de-gaap-ci": GAAP_CI_NAMESPACE,
        },
    )

    element = elements[0]

    assert element.tag == (
        f"{{{GAAP_CI_NAMESPACE}}}"
        "is.netIncome"
    )
    assert element.attrib["contextRef"] == (
        "ctx-duration-2026"
    )
    assert element.attrib["unitRef"] == "EUR"
    assert element.attrib["decimals"] == "2"
    assert element.text == "4500.00"


def test_serializer_serializes_fact_node_with_children_as_siblings() -> None:
    """Item-Fact und Item-Kinder werden als eigenständige Facts serialisiert."""

    context = create_context()
    unit = TaxonomyUnit.eur()

    parent_concept = create_monetary_concept(
        name="test.parent",
    )

    child_concept = create_monetary_concept(
        name="test.child",
    )

    child_plan_node = FactPlanNode(
        concept_name=child_concept.name,
        state=FactPlanState.VALUE,
    )

    parent_plan_node = FactPlanNode(
        concept_name=parent_concept.name,
        state=FactPlanState.VALUE,
        children=(
            child_plan_node,
        ),
    )

    resolved = ResolvedFactPlan(
        nodes=(
            ResolvedFactPlanNode(
                plan_node=parent_plan_node,
                concept=parent_concept,
                fact=TaxonomyFact(
                    concept=parent_concept,
                    amount=Decimal("2500.00"),
                    context=context,
                    unit=unit,
                    decimals=2,
                ),
                children=(
                    ResolvedFactPlanNode(
                        plan_node=child_plan_node,
                        concept=child_concept,
                        fact=TaxonomyFact(
                            concept=child_concept,
                            amount=Decimal("2500.00"),
                            context=context,
                            unit=unit,
                            decimals=2,
                        ),
                    ),
                ),
            ),
        )
    )

    serializer = ResolvedFactPlanXbrlSerializer()

    elements = serializer.serialize(
        resolved_fact_plan=resolved,
        contexts={
            "ctx-duration-2026": context,
        },
        units={
            "EUR": unit,
        },
        taxonomy_namespace=GAAP_CI_NAMESPACE,
        taxonomy_namespaces={
            "de-gaap-ci": GAAP_CI_NAMESPACE,
        },
    )

    assert len(elements) == 2

    parent_element = elements[0]
    child_element = elements[1]

    assert parent_element.tag == (
        f"{{{GAAP_CI_NAMESPACE}}}"
        "test.parent"
    )

    assert parent_element.text == "2500.00"

    assert child_element.tag == (
        f"{{{GAAP_CI_NAMESPACE}}}"
        "test.child"
    )

    assert child_element.text == "2500.00"

    assert list(parent_element) == []
    assert list(child_element) == []

"""Tests für den GCD-Kern des ERiC-Profils Taxonomie 6.9."""

from openbilanz.eric.bilanz_generation.fact_plan import (
    FactPlanState,
)
from openbilanz.eric.bilanz_generation.taxonomy_6_9 import (
    create_profile_6_9,
)


def test_standard_report_profile_tuples_are_structured() -> None:
    plan = create_profile_6_9().fact_plan

    expected = {
        "genInfo.report.id.reportStatus": (
            "genInfo.report.id.reportStatus.reportStatus.E"
        ),
        "genInfo.report.id.revisionStatus": (
            "genInfo.report.id.revisionStatus.revisionStatus.E"
        ),
        "genInfo.report.id.statementType": (
            "genInfo.report.id.statementType.statementType.E"
        ),
        "genInfo.report.id.accountingStandard": (
            "genInfo.report.id.accountingStandard."
            "accountingStandard.HGBM"
        ),
        "genInfo.report.id.specialAccountingStandard": (
            "genInfo.report.id.specialAccountingStandard.K"
        ),
        "genInfo.report.id.incomeStatementFormat": (
            "genInfo.report.id.incomeStatementFormat."
            "incomeStatementFormat.GKV"
        ),
        "genInfo.report.id.consolidationRange": (
            "genInfo.report.id.consolidationRange."
            "consolidationRange.EA"
        ),
        "genInfo.company.id.incomeClassification": (
            "genInfo.company.id.incomeClassification.trade"
        ),
    }

    for parent_name, child_name in expected.items():
        parent = plan.node_for(
            parent_name
        )

        assert parent is not None
        assert parent.state is FactPlanState.CONDITIONAL
        assert len(parent.children) == 1

        child = parent.children[0]

        assert child.concept_name == child_name
        assert child.state is FactPlanState.VALUE


def test_supported_legal_forms_are_conditional_children() -> None:
    plan = create_profile_6_9().fact_plan

    legal_status = plan.node_for(
        "genInfo.company.id.legalStatus"
    )

    assert legal_status is not None
    assert legal_status.state is FactPlanState.CONDITIONAL

    assert tuple(
        child.concept_name
        for child in legal_status.children
    ) == (
        "genInfo.company.id.legalStatus.legalStatus.UG",
        "genInfo.company.id.legalStatus.legalStatus.GMBH",
    )

    assert all(
        child.state is FactPlanState.CONDITIONAL
        for child in legal_status.children
    )


def test_current_fiscal_year_facts_are_required_values() -> None:
    plan = create_profile_6_9().fact_plan

    concept_names = (
        "genInfo.report.period.reportPeriodBegin",
        "genInfo.report.period.reportPeriodEnd",
        "genInfo.report.period.fiscalYearBegin",
        "genInfo.report.period.fiscalYearEnd",
        "genInfo.report.period.balSheetClosingDate",
    )

    for concept_name in concept_names:
        node = plan.node_for(
            concept_name
        )

        assert node is not None
        assert node.state is FactPlanState.VALUE


def test_company_name_and_address_are_flat_fact_plan_nodes() -> None:
    plan = create_profile_6_9().fact_plan

    required_names = (
        "genInfo.company.id.name",
        "genInfo.company.id.location.street",
        "genInfo.company.id.location.houseNo",
        "genInfo.company.id.location.zipCode",
        "genInfo.company.id.location.city",
        "genInfo.company.id.location.country",
    )

    for concept_name in required_names:
        node = plan.node_for(
            concept_name
        )

        assert node is not None
        assert node.state is FactPlanState.VALUE

    assert plan.node_for(
        "genInfo.company.id.location"
    ) is None


def test_country_iso_code_is_optional_value_or_nil() -> None:
    plan = create_profile_6_9().fact_plan

    node = plan.node_for(
        "genInfo.company.id.location.country.isoCode"
    )

    assert node is not None
    assert node.state is FactPlanState.VALUE_OR_NIL


def test_previous_year_period_facts_are_optional_in_standard_profile() -> None:
    plan = create_profile_6_9().fact_plan

    concept_names = (
        "genInfo.report.period.fiscalPreviousYearBegin",
        "genInfo.report.period.fiscalPreviousYearEnd",
        "genInfo.report.period.balSheetClosingDatePreviousYear",
    )

    for concept_name in concept_names:
        node = plan.node_for(
            concept_name
        )

        assert node is not None
        assert node.state is FactPlanState.VALUE_OR_NIL

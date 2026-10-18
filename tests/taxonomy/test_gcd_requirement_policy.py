"""Tests für fachliche GCD-Anforderungsregeln."""

import pytest

from simpleob.taxonomy.gcd_requirement_policy import (
    GcdRequirement,
    GcdRequirementPolicy,
)


@pytest.mark.parametrize(
    ("concept_name", "expected"),
    (
        (
            "genInfo.company.id.shareholder",
            GcdRequirement.REQUIRED,
        ),
        (
            "genInfo.company.id.idNo",
            GcdRequirement.REQUIRED,
        ),
        (
            "genInfo.report.id.accordingTo",
            GcdRequirement.NOT_APPLICABLE,
        ),
        (
            "genInfo.company.id.domesticBranchOfForeignCompany",
            GcdRequirement.CONDITIONAL,
        ),
        (
            "genInfo.company.id.entityWithTaxablePurposeBusiness",
            GcdRequirement.CONDITIONAL,
        ),
    ),
)
def test_standard_corporation_requirements(
    concept_name: str,
    expected: GcdRequirement,
) -> None:
    """Der normale Körperschaftsteuerfall wird klassifiziert."""

    policy = GcdRequirementPolicy.standard_corporation()

    assert policy.requirement_for(
        concept_name
    ) is expected

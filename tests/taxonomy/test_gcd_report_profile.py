"""Tests für das fachliche GCD-Berichtsprofil."""
import pytest

from openbilanz.taxonomy.gcd_report_profile import (
    GcdReportProfile,
)


def test_standard_profile_uses_required_gcd_values() -> None:
    """Der Standardfall verwendet die GCD-Werte für UG/GmbH."""

    profile = GcdReportProfile.standard()

    assert profile.report_status == (
        "genInfo.report.id.reportStatus.reportStatus.E"
    )

    assert profile.revision_status == (
        "genInfo.report.id.revisionStatus.revisionStatus.E"
    )

    assert profile.statement_type == (
        "genInfo.report.id.statementType.statementType.E"
    )

    assert profile.accounting_standard == (
        "genInfo.report.id.accountingStandard."
        "accountingStandard.HGBM"
    )

    assert profile.special_accounting_standard == (
        "genInfo.report.id.specialAccountingStandard.K"
    )

    assert profile.income_statement_format == (
        "genInfo.report.id.incomeStatementFormat."
        "incomeStatementFormat.GKV"
    )

    assert profile.consolidation_range == (
        "genInfo.report.id.consolidationRange."
        "consolidationRange.EA"
    )

    assert profile.income_classification == (
        "genInfo.company.id.incomeClassification.trade"
    )




@pytest.mark.parametrize(
    ("legal_form", "expected"),
    (
        (
            "UG (haftungsbeschränkt)",
            "genInfo.company.id.legalStatus.legalStatus.UG",
        ),
        (
            "GmbH",
            "genInfo.company.id.legalStatus.legalStatus.GMBH",
        ),
    ),
)
def test_report_profile_resolves_supported_legal_form(
    legal_form: str,
    expected: str,
) -> None:
    """UG und GmbH werden auf die richtige GCD-Rechtsform abgebildet."""

    profile = GcdReportProfile.standard()

    assert profile.legal_status_for(
        legal_form
    ) == expected
    
def test_report_profile_rejects_unsupported_legal_form() -> None:
    """Andere Rechtsformen gehören nicht zum unterstützten Scope."""

    profile = GcdReportProfile.standard()

    with pytest.raises(
        ValueError,
        match="unsupported legal form: AG",
    ):
        profile.legal_status_for(
            "AG"
        )

"""Tests für das fachliche GCD-Berichtsprofil."""

import pytest

from simpleob.taxonomy.gcd_report_profile import (
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

    assert profile.report_elements == (
        "genInfo.report.id.reportElement."
        "reportElements.B",
        "genInfo.report.id.reportElement."
        "reportElements.GuV",
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


def test_with_report_element_adds_stu() -> None:
    """STU kann dem bestehenden Berichtsprofil hinzugefügt werden."""

    profile = (
        GcdReportProfile.standard()
        .with_report_element(
            "genInfo.report.id.reportElement."
            "reportElements.STU"
        )
    )

    assert profile.report_elements == (
        "genInfo.report.id.reportElement."
        "reportElements.B",
        "genInfo.report.id.reportElement."
        "reportElements.GuV",
        "genInfo.report.id.reportElement."
        "reportElements.STU",
    )


def test_with_report_element_does_not_duplicate_existing_element() -> None:
    """Ein bereits vorhandenes Report-Element wird nicht dupliziert."""

    profile = GcdReportProfile.standard()

    result = profile.with_report_element(
        "genInfo.report.id.reportElement."
        "reportElements.B"
    )

    assert result is profile


@pytest.mark.parametrize(
    "concept_name",
    (
        "",
        "   ",
    ),
)
def test_with_report_element_rejects_empty_concept_name(
    concept_name: str,
) -> None:
    """Leere Concept-Namen sind ungültig."""

    profile = GcdReportProfile.standard()

    with pytest.raises(
        ValueError,
        match="concept_name must not be empty",
    ):
        profile.with_report_element(
            concept_name
        )


def test_with_report_element_rejects_non_string() -> None:
    """Der Concept-Name muss eine Zeichenkette sein."""

    profile = GcdReportProfile.standard()

    with pytest.raises(
        TypeError,
        match="concept_name must be a string",
    ):
        profile.with_report_element(
            123,  # type: ignore[arg-type]
        )

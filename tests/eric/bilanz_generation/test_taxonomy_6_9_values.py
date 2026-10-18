"""Tests für die FactPlan-Werte der Taxonomie 6.9."""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from simpleob.domain.company import Company
from simpleob.domain.fiscal_year import FiscalYear
from simpleob.eric.bilanz_generation.gaap_ci_6_9_values import (
    GaapCi69Values,
)
from simpleob.eric.bilanz_generation.taxonomy_6_9_values import (
    Taxonomy69ValueBuilder,
)
from simpleob.taxonomy.gcd_company_data import GcdCompanyData
from simpleob.taxonomy.gcd_company_identifiers import (
    GcdCompanyIdentifiers,
)
from simpleob.taxonomy.gcd_report_profile import GcdReportProfile


def _company_data() -> GcdCompanyData:
    return GcdCompanyData(
        company=Company(
            company_id=uuid4(),
            name="Beispiel UG",
        ),
        tax_number="5123045678901",
        legal_form="UG (haftungsbeschränkt)",
        street="Musterstraße",
        house_number="12",
        postal_code="52351",
        city="Düren",
        country="Deutschland",
        business="Softwareentwicklung",
    )


def _identifiers() -> GcdCompanyIdentifiers:
    return GcdCompanyIdentifiers(
        tax_number_13="5123045678901",
        tax_id="12345678901",
        tax_economic_id="DE123456789",
        bf4="1234",
    )


def _fiscal_year() -> FiscalYear:
    return FiscalYear(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )


def _gaap_ci_values() -> GaapCi69Values:
    return GaapCi69Values(
        net_income=Decimal("4500.00"),
        earnings_after_taxes=Decimal("4600.00"),
        operating_total_cost=Decimal("5000.00"),
        gross_trading_profit=Decimal("6000.00"),
    )


def test_builds_standard_report_profile_values() -> None:
    values = Taxonomy69ValueBuilder.build(
        company_data=_company_data(),
        identifiers=_identifiers(),
        fiscal_year=_fiscal_year(),
        report_profile=GcdReportProfile.standard(),
        gaap_ci_values=_gaap_ci_values(),
    )

    assert values[
        (
            "genInfo.report.id.reportStatus",
            (
                "genInfo.report.id.reportStatus."
                "reportStatus.E"
            ),
        )
    ] == "endgültig"

    assert values[
        (
            "genInfo.report.id.accountingStandard",
            (
                "genInfo.report.id.accountingStandard."
                "accountingStandard.HGBM"
            ),
        )
    ] == "deutsches Handelsrecht"

    assert values[
        (
            "genInfo.report.id.incomeStatementFormat",
            (
                "genInfo.report.id.incomeStatementFormat."
                "incomeStatementFormat.GKV"
            ),
        )
    ] == "Gesamtkostenverfahren"


def test_builds_company_and_identifier_values() -> None:
    values = Taxonomy69ValueBuilder.build(
        company_data=_company_data(),
        identifiers=_identifiers(),
        fiscal_year=_fiscal_year(),
        report_profile=GcdReportProfile.standard(),
        gaap_ci_values=_gaap_ci_values(),
    )

    assert values[
        ("genInfo.company.id.name",)
    ] == "Beispiel UG"

    assert values[
        ("genInfo.company.id.location.street",)
    ] == "Musterstraße"

    assert values[
        ("genInfo.company.id.location.country",)
    ] == "Deutschland"

    assert values[
        (
            "genInfo.company.id.idNo",
            (
                "genInfo.company.id.idNo."
                "type.companyId.ST13"
            ),
        )
    ] == "5123045678901"

    assert values[
        (
            "genInfo.company.id.legalStatus",
            (
                "genInfo.company.id.legalStatus."
                "legalStatus.UG"
            ),
        )
    ] == "UG (haftungsbeschränkt)"


def test_builds_fiscal_year_values() -> None:
    values = Taxonomy69ValueBuilder.build(
        company_data=_company_data(),
        identifiers=_identifiers(),
        fiscal_year=_fiscal_year(),
        report_profile=GcdReportProfile.standard(),
        gaap_ci_values=_gaap_ci_values(),
    )

    assert values[
        ("genInfo.report.period.reportPeriodBegin",)
    ] == "2026-01-01"

    assert values[
        ("genInfo.report.period.reportPeriodEnd",)
    ] == "2026-12-31"

    assert values[
        ("genInfo.report.period.fiscalYearBegin",)
    ] == "2026-01-01"

    assert values[
        ("genInfo.report.period.fiscalYearEnd",)
    ] == "2026-12-31"

    assert values[
        ("genInfo.report.period.balSheetClosingDate",)
    ] == "2026-12-31"


def test_builds_report_elements_and_gaap_ci_values() -> None:
    values = Taxonomy69ValueBuilder.build(
        company_data=_company_data(),
        identifiers=_identifiers(),
        fiscal_year=_fiscal_year(),
        report_profile=GcdReportProfile.standard(),
        gaap_ci_values=_gaap_ci_values(),
    )

    assert values[
        (
            "genInfo.report.id.reportElement",
            (
                "genInfo.report.id.reportElement."
                "reportElements.B"
            ),
        )
    ] == "Bilanz"

    assert values[
        (
            "genInfo.report.id.reportElement",
            (
                "genInfo.report.id.reportElement."
                "reportElements.GuV"
            ),
        )
    ] == "GuV"

    assert values[
        ("is.netIncome",)
    ] == Decimal("4500.00")

    assert values[
        ("is.netIncome.eat",)
    ] == Decimal("4600.00")

    assert values[
        ("is.netIncome.regular.operatingTC",)
    ] == Decimal("5000.00")

    assert values[
        (
            (
                "is.netIncome.regular.operatingTC."
                "grossTradingProfit"
            ),
        )
    ] == Decimal("6000.00")


def test_standard_report_profile_omits_stu() -> None:
    values = Taxonomy69ValueBuilder.build(
        company_data=_company_data(),
        identifiers=_identifiers(),
        fiscal_year=_fiscal_year(),
        report_profile=GcdReportProfile.standard(),
        gaap_ci_values=_gaap_ci_values(),
    )

    assert (
        "genInfo.report.id.reportElement",
        (
            "genInfo.report.id.reportElement."
            "reportElements.STU"
        ),
    ) not in values


def test_report_profile_with_stu_builds_stu_value() -> None:
    report_profile = (
        GcdReportProfile.standard()
        .with_report_element(
            "genInfo.report.id.reportElement."
            "reportElements.STU"
        )
    )

    values = Taxonomy69ValueBuilder.build(
        company_data=_company_data(),
        identifiers=_identifiers(),
        fiscal_year=_fiscal_year(),
        report_profile=report_profile,
        gaap_ci_values=_gaap_ci_values(),
    )

    assert values[
        (
            "genInfo.report.id.reportElement",
            (
                "genInfo.report.id.reportElement."
                "reportElements.STU"
            ),
        )
    ] == "Steuerliche Überleitungsrechnung"


def test_report_profile_with_ev_builds_ev_value() -> None:
    report_profile = (
        GcdReportProfile.standard()
        .with_report_element(
            "genInfo.report.id.reportElement."
            "reportElements.EV"
        )
    )

    values = Taxonomy69ValueBuilder.build(
        company_data=_company_data(),
        identifiers=_identifiers(),
        fiscal_year=_fiscal_year(),
        report_profile=report_profile,
        gaap_ci_values=_gaap_ci_values(),
    )

    assert values[
        (
            "genInfo.report.id.reportElement",
            (
                "genInfo.report.id.reportElement."
                "reportElements.EV"
            ),
        )
    ] == "Ergebnisverwendung"


def test_optional_identifiers_are_omitted() -> None:
    identifiers = GcdCompanyIdentifiers(
        tax_number_13="5123045678901",
    )

    values = Taxonomy69ValueBuilder.build(
        company_data=_company_data(),
        identifiers=identifiers,
        fiscal_year=_fiscal_year(),
        report_profile=GcdReportProfile.standard(),
        gaap_ci_values=_gaap_ci_values(),
    )

    id_no_parent = "genInfo.company.id.idNo"

    assert (
        id_no_parent,
        (
            "genInfo.company.id.idNo."
            "type.companyId.STID"
        ),
    ) not in values

    assert (
        id_no_parent,
        (
            "genInfo.company.id.idNo."
            "type.companyId.STWID"
        ),
    ) not in values

    assert (
        id_no_parent,
        (
            "genInfo.company.id.idNo."
            "type.companyId.BF4"
        ),
    ) not in values

    assert (
        "genInfo.company.id.location.country.isoCode",
    ) not in values


def test_mismatching_tax_numbers_are_rejected() -> None:
    identifiers = GcdCompanyIdentifiers(
        tax_number_13="5999999999999",
    )

    with pytest.raises(
        ValueError,
        match="company tax numbers do not match",
    ):
        Taxonomy69ValueBuilder.build(
            company_data=_company_data(),
            identifiers=identifiers,
            fiscal_year=_fiscal_year(),
            report_profile=GcdReportProfile.standard(),
            gaap_ci_values=_gaap_ci_values(),
        )

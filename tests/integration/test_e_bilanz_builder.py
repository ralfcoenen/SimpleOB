"""Integrationstest für die vollständige E-Bilanz-Erzeugung."""

from datetime import date
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest

from openbilanz.domain.company import Company
from openbilanz.domain.e_bilanz_account_detail import (
    EBilanzAccountDetail,
)
from openbilanz.domain.fiscal_year import FiscalYear
from openbilanz.hgb.balance_sheet_structure import (
    create_hgb_balance_sheet_structure,
)
from openbilanz.hgb.income_statement_structure import (
    create_hgb_income_statement_structure,
)
from openbilanz.reporting.fixed_asset_schedule import (
    FixedAssetSchedule,
    FixedAssetScheduleRow,
)
from openbilanz.taxonomy.arelle_adapter import ArelleAdapter
from openbilanz.taxonomy.e_bilanz_builder import EBilanzBuilder
from openbilanz.taxonomy.entry_point import TaxonomyEntryPoint
from openbilanz.taxonomy.gcd_company_data import GcdCompanyData
from openbilanz.taxonomy.gcd_company_identifiers import (
    GcdCompanyIdentifiers,
)
from openbilanz.taxonomy.gcd_domestic_branch_of_foreign_company import (
    GcdDomesticBranchOfForeignCompanyType,
)
from openbilanz.taxonomy.gcd_entity_with_taxable_purpose_business import (
    GcdEntityWithTaxablePurposeBusinessType,
)
from openbilanz.taxonomy.gcd_shareholder import (
    GcdShareDivideKey,
    GcdShareholder,
    GcdShareholderGroup,
    GcdShareholderLegalStatus,
)
from openbilanz.taxonomy.resolver import TaxonomyResolver
from openbilanz.taxonomy.taxonomy import TaxonomyVersion

TAXONOMY_ROOT = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "taxonomy"
)

TEST_ENTITY_SCHEME = (
    "http://www.bundesfinanzministerium.de"
)


def _positions_by_code(*roots):
    result = {}

    def walk(position):
        result[position.code] = position

        for child in position.children:
            walk(child)

    for root in roots:
        walk(root)

    return result


@pytest.mark.integration
def test_builds_complete_e_bilanz_and_validates_with_arelle(
    tmp_path: Path,
) -> None:
    """GCD und HGB-Abschluss werden zu valider E-Bilanz-XBRL."""

    version_root = TAXONOMY_ROOT / "6.10"

    if not version_root.is_dir():
        pytest.skip(
            "Taxonomy 6.10 is not installed locally"
        )

    gcd_namespace = (
        "http://www.xbrl.de/taxonomies/"
        "de-gcd-2026-04-01"
    )

    gaap_namespace = (
        "http://www.xbrl.de/taxonomies/"
        "de-gaap-ci-2026-04-01"
    )

    resolver = TaxonomyResolver(
        root=TAXONOMY_ROOT
    )

    gcd_entry_point_path = resolver.gcd_entry_point(
        TaxonomyVersion.V6_10
    )

    gaap_entry_point_path = (
        resolver.gaap_ci_fiscal_entry_point(
            TaxonomyVersion.V6_10
        )
    )

    gcd_base_entry_point = TaxonomyEntryPoint.from_file(
        gcd_entry_point_path
    )

    gaap_base_entry_point = TaxonomyEntryPoint.from_file(
        gaap_entry_point_path
    )

    gcd_entry_point = TaxonomyEntryPoint(
        path=gcd_base_entry_point.path,
        namespace=gcd_base_entry_point.namespace,
        schema_imports=gcd_base_entry_point.schema_imports,
        linkbase_references=(
            gcd_base_entry_point.linkbase_references
        ),
        schema_ref=gcd_entry_point_path.as_uri(),
    )

    gaap_entry_point = TaxonomyEntryPoint(
        path=gaap_base_entry_point.path,
        namespace=gaap_base_entry_point.namespace,
        schema_imports=gaap_base_entry_point.schema_imports,
        linkbase_references=(
            gaap_base_entry_point.linkbase_references
        ),
        schema_ref=gaap_entry_point_path.as_uri(),
    )

    adapter = ArelleAdapter()

    try:
        gcd_model = adapter.model(
            gcd_entry_point_path
        )

        gaap_model = adapter.model(
            gaap_entry_point_path
        )

        assets, liabilities = (
            create_hgb_balance_sheet_structure()
        )

        income_statement = (
            create_hgb_income_statement_structure()
        )

        positions = _positions_by_code(
            assets,
            liabilities,
            income_statement,
        )

        company = Company(
            company_id=uuid4(),
            name="Muster UG (haftungsbeschränkt)",
        )

        company_data = GcdCompanyData(
            company=company,
            tax_number="1234567890123",
            legal_form="UG (haftungsbeschränkt)",
            street="Musterstraße",
            house_number="12a",
            postal_code="12345",
            city="Musterstadt",
            country="DE",
            business="Softwareentwicklung",
        )

        fiscal_year = FiscalYear(
            start_date=date(2027, 1, 1),
            end_date=date(2027, 12, 31),
        )

        identifiers = GcdCompanyIdentifiers(
            tax_number_13="1234567890123",
            tax_id="12345678901",
            tax_economic_id="DE123456789",
            bf4="1234",
        )

        shareholder = GcdShareholder(
            name="Mustermann",
            first_name="Max",
            shareholder_id="1",
            tax_number="1234567890123",
            tax_id="12345678901",
            wid="WID-1",
            group=GcdShareholderGroup.LIMITED,
            legal_status=(
                GcdShareholderLegalStatus.NATURAL_PERSON
            ),
            share_divide_key=GcdShareDivideKey(
                numerator="100",
                denominator="100",
            ),
            current_number=1,
            special_balance_required=False,
            extension_required=False,
            economic_id="BEWI-1",
            id_not_assigned="NO-ID",
        )

        account_detail = EBilanzAccountDetail(
            position=positions["HGB.266.AKTIVA.B.IV"],
            account_number="1200",
            account_description="Bank",
            balance=Decimal("10000.00"),
        )

        builder = EBilanzBuilder(
            gcd_model=gcd_model,
            gaap_ci_model=gaap_model,
            gcd_entry_point=gcd_entry_point,
            gaap_ci_entry_point=gaap_entry_point,
            gcd_namespace=gcd_namespace,
            gaap_ci_namespace=gaap_namespace,
            assets=assets,
            liabilities=liabilities,
            income_statement=income_statement,
        )

        fixed_asset_schedule = FixedAssetSchedule(
            rows=(
                FixedAssetScheduleRow(
                    position_code="HGB.266.AKTIVA.A.II.3",
                    opening_cost=Decimal("12000.00"),
                    additions=Decimal("0.00"),
                    disposals=Decimal("0.00"),
                    current_depreciation=Decimal("2400.00"),
                    accumulated_depreciation=Decimal("4800.00"),
                    closing_book_value=Decimal("7200.00"),
                ),
            )
        )

        document = builder.build(
            company_data=company_data,
            fiscal_year=fiscal_year,
            amounts={
                positions["HGB.266.AKTIVA.B.IV"]:
                    Decimal("10000.00"),
                positions["HGB.266.PASSIVA.A.I"]:
                    Decimal("1000.00"),
                positions["HGB.266.PASSIVA.C.4"]:
                    Decimal("9000.00"),
                positions["HGB.275.GKV.1"]:
                    Decimal("5000.00"),
                positions["HGB.275.GKV.8"]:
                    Decimal("2000.00"),

                # Reiner Strukturknoten:
                positions["HGB.275.GKV"]:
                    Decimal("3000.00"),
            },
            entity_identifier="DE123456789",
            entity_scheme=TEST_ENTITY_SCHEME,
            account_details=(
                account_detail,
            ),
            fixed_asset_schedule=fixed_asset_schedule,
            identifiers=identifiers,
            shareholders=(
                shareholder,
            ),
            domestic_branch_types=(
                GcdDomesticBranchOfForeignCompanyType.HGB,
            ),
            taxable_purpose_business_types=(
                GcdEntityWithTaxablePurposeBusinessType.NORMAL,
            ),
        )

        xml = document.xml

        assert "de-gcd" in xml
        assert "de-gaap-ci" in xml

        assert (
            "genInfo.report.id.reportElement.reportElements.B"
            in xml
        )
        assert (
            "genInfo.report.id.reportElement.reportElements.GuV"
            in xml
        )
        assert (
            "genInfo.report.id.reportElement.reportElements.BAL"
            in xml
        )

        assert (
            "detailedInformation.accountBalances"
            in xml
        )
        assert (
            "detailedInformation."
            "accountbalances.positionName"
            in xml
        )
        assert (
            "de-gaap-ci:bs.ass.currAss.cashEquiv"
            in xml
        )
        assert (
            "detailedInformation."
            "accountbalances.accountNumber"
            in xml
        )
        assert ">1200<" in xml

        assert (
            "detailedInformation."
            "accountbalances.accountDescription"
            in xml
        )
        assert ">Bank<" in xml

        assert (
            "detailedInformation."
            "accountbalances.amount"
            in xml
        )
        assert ">10000.00<" in xml

        assert "bs.ass.currAss.cashEquiv" in xml
        assert "bs.eqLiab.equity.subscribed" in xml
        assert "bs.eqLiab.liab.trade" in xml

        assert (
            "is.netIncome.regular.operatingTC."
            "grossTradingProfit.totalOutput.netSales"
            in xml
        )

        assert (
            "is.netIncome.regular.operatingTC.otherCost"
            in xml
        )

        assert "grossCost.beginning_short" in xml
        assert ">12000.00<" in xml

        assert "accDepr.DeprPeriod_short" in xml
        assert ">2400.00<" in xml

        assert (
            'dimension="de-gaap-ci:dim_taxTrans"'
            in xml
        )
        assert ">de-gaap-ci:dim_comBal<" in xml

        assert (
            'dimension="de-gaap-ci:'
            'dim_changes.nt.ass.gross_short"'
            in xml
        )
        assert (
            ">de-gaap-ci:"
            "bs.ass.fixAss.tan.otherEquipm<"
            in xml
        )

        instance_path = (
            tmp_path
            / "openbilanz-complete-e-bilanz-610.xbrl"
        )

        instance_path.write_text(
            xml,
            encoding="utf-8",
        )

        result = adapter.validate(
            instance_path
        )

    finally:
        adapter.close()

    assert result.is_valid
    assert result.errors == ()

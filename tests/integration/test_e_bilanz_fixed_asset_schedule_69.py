"""Integrationstest des Anlagenspiegels mit Taxonomie 6.9."""

from datetime import date
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest

from openbilanz.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
from openbilanz.domain.company import Company
from openbilanz.domain.fiscal_year import FiscalYear
from openbilanz.hgb.balance_sheet_structure import (
    create_hgb_balance_sheet_structure,
)
from openbilanz.hgb.income_statement_structure import (
    create_hgb_income_statement_structure,
)
from openbilanz.services.fixed_asset_schedule_service import (
    FixedAssetSchedulePosition,
)
from openbilanz.taxonomy.arelle_adapter import ArelleAdapter
from openbilanz.taxonomy.e_bilanz_builder import EBilanzBuilder
from openbilanz.taxonomy.entry_point import TaxonomyEntryPoint
from openbilanz.taxonomy.gcd_company_data import GcdCompanyData
from openbilanz.taxonomy.resolver import TaxonomyResolver
from openbilanz.taxonomy.taxonomy import TaxonomyVersion


TAXONOMY_ROOT = Path(
    "data/taxonomy"
).resolve()

TEST_ENTITY_SCHEME = (
    "http://www.bundesfinanzministerium.de"
)


def _positions_by_code(
    *roots: FinancialStatementPosition,
) -> dict[str, FinancialStatementPosition]:
    """Liefert alle HGB-Positionen nach ihrem Code."""

    result: dict[
        str,
        FinancialStatementPosition,
    ] = {}

    def walk(
        position: FinancialStatementPosition,
    ) -> None:
        result[position.code] = position

        for child in position.children:
            walk(child)

    for root in roots:
        walk(root)

    return result


@pytest.mark.integration
def test_e_bilanz_69_builds_and_validates_fixed_asset_schedule(
    tmp_path: Path,
) -> None:
    """Anlagenspiegel und GCD-Mussfeld werden mit Arelle validiert."""

    version_root = TAXONOMY_ROOT / "6.9"

    if not version_root.is_dir():
        pytest.skip(
            "Taxonomy 6.9 is not installed locally"
        )

    gcd_namespace = (
        "http://www.xbrl.de/taxonomies/"
        "de-gcd-2025-04-01"
    )

    gaap_namespace = (
        "http://www.xbrl.de/taxonomies/"
        "de-gaap-ci-2025-04-01"
    )

    resolver = TaxonomyResolver(
        root=TAXONOMY_ROOT
    )

    gcd_entry_point_path = resolver.gcd_entry_point(
        TaxonomyVersion.V6_9
    )

    gaap_entry_point_path = (
        resolver.gaap_ci_fiscal_entry_point(
            TaxonomyVersion.V6_9
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
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )

        fixed_asset_schedule = (
            FixedAssetSchedulePosition(
                position_code=(
                    "HGB.266.AKTIVA.A.II.2"
                ),
                acquisition_cost_beginning=(
                    Decimal("8000.00")
                ),
                additions=Decimal("2000.00"),
                disposals=Decimal("0.00"),
                acquisition_cost_ending=(
                    Decimal("10000.00")
                ),
                accumulated_depreciation_beginning=(
                    Decimal("2000.00")
                ),
                depreciation_current_year=(
                    Decimal("1000.00")
                ),
                depreciation_disposals=(
                    Decimal("0.00")
                ),
                accumulated_depreciation_ending=(
                    Decimal("3000.00")
                ),
                carrying_amount_ending=(
                    Decimal("7000.00")
                ),
            ),
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

        document = builder.build(
            company_data=company_data,
            fiscal_year=fiscal_year,
            amounts={
                positions[
                    "HGB.266.AKTIVA.A.II.2"
                ]: Decimal("7000.00"),
                positions[
                    "HGB.266.PASSIVA.A.I"
                ]: Decimal("7000.00"),
            },
            entity_identifier="DE123456789",
            entity_scheme=TEST_ENTITY_SCHEME,
            fixed_asset_schedule=(
                fixed_asset_schedule
            ),
        )

        xml = document.xml

        assert "xbrldi:explicitMember" in xml

        assert (
            'dimension="de-gaap-ci:dim_taxTrans"'
            in xml
        )
        assert (
            ">de-gaap-ci:dim_comBal<"
            in xml
        )

        assert (
            'dimension="de-gaap-ci:'
            'dim_changes.nt.ass.gross"'
            in xml
        )
        assert (
            ">de-gaap-ci:"
            "bs.ass.fixAss.tan.machinery<"
            in xml
        )

        assert "grossCost.beginning" in xml
        assert "gross.addition" in xml
        assert "gross.release" in xml
        assert "accDepr.beginning" in xml

        assert (
            "accDepr.DeprPeriod.regular"
            in xml
        )
        assert "accDepr.release" in xml

        assert (
            "<de-gcd:"
            "genInfo.report.id."
            "incomeStatementendswithBalProfit"
            ' contextRef="ctx-duration-2026">'
            "false"
            "</de-gcd:"
            "genInfo.report.id."
            "incomeStatementendswithBalProfit>"
            in xml
        )

        instance_path = (
            tmp_path
            / "simpleob-fixed-asset-schedule-69.xbrl"
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

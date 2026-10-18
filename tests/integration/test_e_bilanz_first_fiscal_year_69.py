"""Integrationstest für das erste Geschäftsjahr mit Taxonomie 6.9."""

import xml.etree.ElementTree as ET
from datetime import date
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest

from simpleob.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
from simpleob.domain.company import Company
from simpleob.domain.fiscal_year import FiscalYear
from simpleob.hgb.balance_sheet_structure import (
    create_hgb_balance_sheet_structure,
)
from simpleob.hgb.income_statement_structure import (
    create_hgb_income_statement_structure,
)
from simpleob.taxonomy.arelle_adapter import ArelleAdapter
from simpleob.taxonomy.e_bilanz_builder import EBilanzBuilder
from simpleob.taxonomy.entry_point import TaxonomyEntryPoint
from simpleob.taxonomy.gcd_company_data import GcdCompanyData
from simpleob.taxonomy.resolver import TaxonomyResolver
from simpleob.taxonomy.taxonomy import TaxonomyVersion

TAXONOMY_ROOT = Path(
    "data/taxonomy"
).resolve()

TEST_ENTITY_SCHEME = (
    "http://www.bundesfinanzministerium.de"
)

XSI_NAMESPACE = (
    "http://www.w3.org/2001/XMLSchema-instance"
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
def test_e_bilanz_69_first_fiscal_year_uses_nil_previous_year_dates(
    tmp_path: Path,
) -> None:
    """Im ersten Geschäftsjahr werden Vorjahresdaten als NIL ausgegeben."""

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
            previous_fiscal_year=None,
            amounts={
                positions[
                    "HGB.266.AKTIVA.B.IV"
                ]: Decimal("1000.00"),
                positions[
                    "HGB.266.PASSIVA.A.I"
                ]: Decimal("1000.00"),
            },
            entity_identifier="DE123456789",
            entity_scheme=TEST_ENTITY_SCHEME,
        )

        xml = document.xml

        root = ET.fromstring(xml)

        current_year_values = {
            "genInfo.report.period.fiscalYearBegin":
                "2026-01-01",
            "genInfo.report.period.fiscalYearEnd":
                "2026-12-31",
            "genInfo.report.period.balSheetClosingDate":
                "2026-12-31",
        }

        for concept_name, expected_value in (
            current_year_values.items()
        ):
            element = root.find(
                f".//{{{gcd_namespace}}}"
                f"{concept_name}"
            )

            assert element is not None
            assert element.text == expected_value
            assert (
                element.get(
                    f"{{{XSI_NAMESPACE}}}nil"
                )
                is None
            )

        previous_year_concepts = (
            "genInfo.report.period.fiscalPreviousYearBegin",
            "genInfo.report.period.fiscalPreviousYearEnd",
            (
                "genInfo.report.period."
                "balSheetClosingDatePreviousYear"
            ),
        )

        for concept_name in previous_year_concepts:
            element = root.find(
                f".//{{{gcd_namespace}}}"
                f"{concept_name}"
            )

            assert element is not None
            assert (
                element.get(
                    f"{{{XSI_NAMESPACE}}}nil"
                )
                == "true"
            )
            assert element.get("unitRef") is None
            assert element.text is None

        instance_path = (
            tmp_path
            / "simpleob-first-fiscal-year-69.xbrl"
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

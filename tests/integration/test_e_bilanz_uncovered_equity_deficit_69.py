"""Integrationstest des HGB-Fehlbetragsausweises in Taxonomie 6.9."""

import os
from datetime import date
from decimal import Decimal
from pathlib import Path
from uuid import uuid4
from xml.etree import ElementTree as ET

import pytest

from simpleob.accounting.balance_sheet import BalanceSheet
from simpleob.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
from simpleob.accounting.income_statement import IncomeStatement
from simpleob.domain.accounting_account_roles import (
    AccountingAccountRoles,
)
from simpleob.domain.company import Company
from simpleob.domain.company_master_data import CompanyMasterData
from simpleob.domain.fiscal_year import FiscalYear
from simpleob.domain.vat_accounts import VatAccounts
from simpleob.hgb.balance_sheet_structure import (
    create_hgb_balance_sheet_structure,
)
from simpleob.hgb.income_statement_structure import (
    create_hgb_income_statement_structure,
)
from simpleob.services.e_bilanz_service import EBilanzService
from simpleob.taxonomy.arelle_adapter import ArelleAdapter
from simpleob.taxonomy.entry_point import TaxonomyEntryPoint
from simpleob.taxonomy.gcd_company_data_mapper import (
    GcdCompanyDataMapper,
)
from simpleob.taxonomy.resolver import TaxonomyResolver
from simpleob.taxonomy.taxonomy import TaxonomyVersion

_DEFAULT_TAXONOMY_ROOT = Path("data/taxonomy").resolve()
_USER_TAXONOMY_ROOT = (
    Path.home()
    / "Library/Application Support/SimpleOB/taxonomy"
)
TAXONOMY_ROOT = Path(
    os.environ.get(
        "SIMPLEOB_TAXONOMY_ROOT",
        str(
            _DEFAULT_TAXONOMY_ROOT
            if (_DEFAULT_TAXONOMY_ROOT / "6.9").is_dir()
            else _USER_TAXONOMY_ROOT
        ),
    )
)


def _positions_by_code(*roots) -> dict[str, FinancialStatementPosition]:
    positions: dict[str, FinancialStatementPosition] = {}

    def walk(position: FinancialStatementPosition) -> None:
        positions[position.code] = position
        for child in position.children:
            walk(child)

    for root in roots:
        walk(root)
    return positions


@pytest.mark.integration
@pytest.mark.parametrize(
    ("economic_equity", "deficit"),
    (
        (Decimal("-5000.00"), Decimal("5000.00")),
        (Decimal("0.00"), Decimal("0.00")),
        (Decimal("1000.00"), Decimal("0.00")),
    ),
)
def test_negative_equity_deficit_xbrl_and_arelle_validation(
    tmp_path: Path,
    economic_equity: Decimal,
    deficit: Decimal,
) -> None:
    """Bilanzfacts und BVV verwenden die getrennten Roh-/Ausweiswerte."""

    if not (TAXONOMY_ROOT / "6.9").is_dir():
        pytest.skip("Taxonomie 6.9 ist lokal nicht installiert")

    assets, liabilities = create_hgb_balance_sheet_structure()
    income_statement_root = create_hgb_income_statement_structure()
    positions = _positions_by_code(
        assets,
        liabilities,
        income_statement_root,
    )
    amounts = {
        assets: Decimal("2000.00"),
        positions["HGB.266.AKTIVA.B.IV"]: Decimal("2000.00"),
        liabilities: Decimal("2000.00"),
        positions["HGB.266.PASSIVA.A"]: economic_equity,
        positions["HGB.266.PASSIVA.A.I"]: Decimal("1000.00"),
        positions["HGB.266.PASSIVA.A.IV"]: economic_equity - Decimal("1000.00"),
        positions["HGB.266.PASSIVA.C"]: Decimal("2000.00") - economic_equity,
        positions["HGB.266.PASSIVA.C.4"]: Decimal("2000.00") - economic_equity,
    }
    balance_sheet = BalanceSheet(
        assets=assets,
        liabilities=liabilities,
        amounts=amounts,
    )
    income_statement = IncomeStatement(
        income_statement=income_statement_root,
        amounts={},
    )
    company = Company(
        company_id=uuid4(),
        name="E-Bilanz-Integrationstest UG",
    )
    master_data = CompanyMasterData(
        company=company,
        legal_form="UG (haftungsbeschränkt)",
        tax_number="123/4567/8901",
        federal_state="NW",
        tax_id="12345678901",
        tax_economic_id="DE123456789",
        bf4="1234",
        street="Musterstraße",
        house_number="1",
        postal_code="50667",
        city="Köln",
        country="DE",
        business="Softwareentwicklung",
    )
    fiscal_year = FiscalYear(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )
    validation_root = tmp_path / "taxonomy"
    validation_root.mkdir()
    (validation_root / "6.9").symlink_to(
        TAXONOMY_ROOT / "6.9",
        target_is_directory=True,
    )
    resolver = TaxonomyResolver(root=validation_root)
    adapter = ArelleAdapter()
    service = EBilanzService(
        resolver=resolver,
        adapter=adapter,
        company_data_mapper=GcdCompanyDataMapper(),
        assets=assets,
        liabilities=liabilities,
        income_statement=income_statement_root,
    )

    try:
        document = service.build(
            master_data=master_data,
            fiscal_year=fiscal_year,
            amounts=amounts,
            income_statement=income_statement,
            balance_sheet=balance_sheet,
            vat_accounts=VatAccounts(
                input_tax_7="1571",
                input_tax_19="1576",
                output_tax_7="1771",
                output_tax_19="1776",
            ),
            account_roles=AccountingAccountRoles(
                cash_accounts=frozenset(),
                bank_accounts=frozenset(),
                general_rate_sales_accounts=frozenset(),
            ),
            entity_identifier="DE123456789",
            entity_scheme=(
                "http://www.bundesfinanzministerium.de"
            ),
            previous_hgb_equity=Decimal("0.00"),
        )
        root = ET.fromstring(document.xml)
        gaap_namespace = (
            "http://www.xbrl.de/taxonomies/"
            "de-gaap-ci-2025-04-01"
        )

        def facts(concept_name: str):
            return root.findall(f"{{{gaap_namespace}}}{concept_name}")

        expected = {
            "bs.ass": str(Decimal("2000.00") + deficit),
            "bs.eqLiab": str(Decimal("2000.00") + deficit),
            "BVV.profitLoss.assetsCurrentYear": str(economic_equity),
        }
        if deficit:
            expected.update(
                {
                    "bs.ass.deficitNotCoveredByCapital": str(deficit),
                    "bs.eqLiab.equity.deficitNotCoveredByCapital": str(deficit),
                    "bs.eqLiab.equity": "0.00",
                }
            )
        elif economic_equity:
            expected["bs.eqLiab.equity"] = str(economic_equity)
        for concept_name, value in expected.items():
            matching = facts(concept_name)
            assert len(matching) == 1, concept_name
            assert matching[0].text == value, concept_name
            expected_context = (
                "ctx-duration-2026"
                if concept_name.startswith("BVV.")
                else "ctx-instant-2026"
            )
            assert matching[0].attrib["contextRef"] == expected_context

        for concept_name in (
            "bs.ass.deficitNotCoveredByCapital",
            "bs.eqLiab.equity.deficitNotCoveredByCapital",
        ):
            matching = facts(concept_name)
            assert len(matching) <= 1
            if deficit:
                assert len(matching) == 1
                assert matching[0].attrib.get(
                    "{http://www.w3.org/2001/XMLSchema-instance}nil"
                ) != "true"
            elif matching:
                assert matching[0].attrib.get(
                    "{http://www.w3.org/2001/XMLSchema-instance}nil"
                ) == "true"
        assert balance_sheet.amounts == amounts
        assert not balance_sheet.uncovered_equity_deficit_applied

        gcd_path = resolver.gcd_entry_point(
            TaxonomyVersion.V6_9
        )
        gaap_path = resolver.gaap_ci_fiscal_entry_point(
            TaxonomyVersion.V6_9
        )
        gcd_entry = TaxonomyEntryPoint.from_file(gcd_path)
        gaap_entry = TaxonomyEntryPoint.from_file(gaap_path)
        validation_xml = document.xml.replace(
            gcd_entry.schema_ref_uri,
            gcd_path.as_uri(),
        ).replace(
            gaap_entry.schema_ref_uri,
            gaap_path.as_uri(),
        )
        instance_path = tmp_path / "uncovered-equity-deficit.xbrl"
        instance_path.write_text(validation_xml, encoding="utf-8")
        validation = adapter.validate(instance_path)
        assert validation.is_valid, validation.errors

    finally:
        adapter.close()

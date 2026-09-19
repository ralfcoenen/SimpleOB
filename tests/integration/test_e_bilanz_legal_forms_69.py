"""Integrationstest der unterstützten Rechtsformen für Taxonomie 6.9."""

from datetime import date
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest

from openbilanz.accounting.balance_sheet import BalanceSheet
from openbilanz.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
from openbilanz.accounting.income_statement import IncomeStatement
from openbilanz.domain.accounting_account_roles import (
    AccountingAccountRoles,
)
from openbilanz.domain.company import Company
from openbilanz.domain.company_master_data import (
    CompanyMasterData,
)
from openbilanz.domain.e_bilanz_account_detail import (
    EBilanzAccountDetail,
)
from openbilanz.domain.fiscal_year import FiscalYear
from openbilanz.domain.vat_accounts import VatAccounts
from openbilanz.hgb.balance_sheet_structure import (
    create_hgb_balance_sheet_structure,
)
from openbilanz.hgb.income_statement_structure import (
    create_hgb_income_statement_structure,
)
from openbilanz.services.e_bilanz_service import EBilanzService
from openbilanz.taxonomy.arelle_adapter import ArelleAdapter
from openbilanz.taxonomy.gcd_company_data_mapper import (
    GcdCompanyDataMapper,
)
from openbilanz.taxonomy.resolver import TaxonomyResolver

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
@pytest.mark.parametrize(
    ("company_name", "legal_form"),
    (
        (
            "Muster UG (haftungsbeschränkt)",
            "UG (haftungsbeschränkt)",
        ),
        (
            "Muster GmbH",
            "GmbH",
        ),
    ),
)
def test_e_bilanz_69_validates_supported_legal_forms(
    company_name: str,
    legal_form: str,
) -> None:
    """UG und GmbH werden mit Taxonomie 6.9 valide erzeugt."""

    version_root = TAXONOMY_ROOT / "6.9"

    if not version_root.is_dir():
        pytest.skip(
            "Taxonomy 6.9 is not installed locally"
        )

    assets, liabilities = (
        create_hgb_balance_sheet_structure()
    )

    income_statement_root = (
        create_hgb_income_statement_structure()
    )

    positions = _positions_by_code(
        assets,
        liabilities,
        income_statement_root,
    )

    company = Company(
        company_id=uuid4(),
        name=company_name,
    )

    master_data = CompanyMasterData(
        company=company,
        legal_form=legal_form,
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

    cash_position = positions[
        "HGB.266.AKTIVA.B.IV"
    ]

    equity_position = positions[
        "HGB.266.PASSIVA.A"
    ]

    capital_position = positions[
        "HGB.266.PASSIVA.A.I"
    ]

    amounts: dict[
        FinancialStatementPosition,
        Decimal,
    ] = {
        assets: Decimal("10000.00"),
        cash_position: Decimal("10000.00"),
        liabilities: Decimal("10000.00"),
        equity_position: Decimal("10000.00"),
        capital_position: Decimal("10000.00"),
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

    vat_accounts = VatAccounts(
        input_tax_7="1571",
        input_tax_19="1576",
        output_tax_7="1771",
        output_tax_19="1776",
    )

    account_roles = AccountingAccountRoles(
        cash_accounts=frozenset(),
        bank_accounts=frozenset({"1200"}),
        general_rate_sales_accounts=frozenset(),
    )

    account_details = (
        EBilanzAccountDetail(
            position=cash_position,
            account_number="1200",
            account_description="Bank",
            balance=Decimal("10000.00"),
        ),
        EBilanzAccountDetail(
            position=capital_position,
            account_number="0800",
            account_description="Gezeichnetes Kapital",
            balance=Decimal("10000.00"),
        ),
    )

    resolver = TaxonomyResolver(
        root=TAXONOMY_ROOT
    )

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
            vat_accounts=vat_accounts,
            account_roles=account_roles,
            entity_identifier="DE123456789",
            entity_scheme=TEST_ENTITY_SCHEME,
            account_details=account_details,
            previous_hgb_equity=Decimal("10000.00"),
        )

        result = service.validate(
            document,
            fiscal_year=fiscal_year,
        )

    finally:
        adapter.close()

    assert result.is_valid
    assert result.errors == ()

    assert "1200" in document.xml
    assert "Bank" in document.xml
    assert "0800" in document.xml
    assert "Gezeichnetes Kapital" in document.xml

    if legal_form == "UG (haftungsbeschränkt)":
        assert (
            "genInfo.company.id.legalStatus."
            "legalStatus.UG"
            in document.xml
        )
        assert (
            "genInfo.company.id.legalStatus."
            "legalStatus.GMBH"
            not in document.xml
        )

    else:
        assert (
            "genInfo.company.id.legalStatus."
            "legalStatus.GMBH"
            in document.xml
        )
        assert (
            "genInfo.company.id.legalStatus."
            "legalStatus.UG"
            not in document.xml
        )

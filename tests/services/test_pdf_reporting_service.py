from decimal import Decimal

from openbilanz.accounting.balance_sheet import BalanceSheet
from openbilanz.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
from openbilanz.services.pdf_reporting_service import (
    PdfReportingService,
)


def test_exports_balance_sheet_as_pdf(tmp_path) -> None:
    bank = FinancialStatementPosition(
        code="HGB.266.AKTIVA.B.IV",
        name="Guthaben bei Kreditinstituten",
    )
    assets = FinancialStatementPosition(
        code="HGB.266.AKTIVA",
        name="Aktiva",
        children=(bank,),
    )

    equity = FinancialStatementPosition(
        code="HGB.266.PASSIVA.A",
        name="Eigenkapital",
    )
    liabilities = FinancialStatementPosition(
        code="HGB.266.PASSIVA",
        name="Passiva",
        children=(equity,),
    )

    balance_sheet = BalanceSheet(
        assets=assets,
        liabilities=liabilities,
        amounts={
            assets: Decimal("1000.00"),
            bank: Decimal("1000.00"),
            liabilities: Decimal("1000.00"),
            equity: Decimal("1000.00"),
        },
    )

    target = tmp_path / "bilanz.pdf"

    exported_path = PdfReportingService().export_balance_sheet(
        balance_sheet=balance_sheet,
        company_name="Beispiel UG",
        fiscal_year_name="01.01.2026 – 31.12.2026",
        target=target,
    )

    assert exported_path == target
    assert target.exists()
    assert target.stat().st_size > 0
    assert target.read_bytes().startswith(b"%PDF-")
    
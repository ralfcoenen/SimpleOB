from decimal import Decimal

from openbilanz.accounting.balance_sheet import BalanceSheet
from openbilanz.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
from openbilanz.domain.bvv_evaluation import BvvEvaluation
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


def test_exports_bvv_as_pdf(tmp_path) -> None:
    evaluation = BvvEvaluation(
        current_hgb_equity=Decimal("10000.00"),
        previous_hgb_equity=Decimal("0.00"),
        current_depreciation_difference=Decimal("0.00"),
        previous_depreciation_difference=Decimal("0.00"),
        current_book_value_difference=Decimal("0.00"),
        previous_book_value_difference=Decimal("0.00"),
        current_tax_equity=Decimal("10000.00"),
        previous_tax_equity=Decimal("0.00"),
        contribution=Decimal("10000.00"),
        withdrawal_distribution=Decimal("0.00"),
        profit_loss=Decimal("0.00"),
    )

    target = tmp_path / "bvv.pdf"

    exported_path = PdfReportingService().export_bvv(
        evaluation=evaluation,
        company_name="Beispiel UG",
        fiscal_year_name="01.01.2026 – 31.12.2026",
        target=target,
    )

    assert exported_path == target
    assert target.exists()
    assert target.stat().st_size > 0
    assert target.read_bytes().startswith(b"%PDF-")

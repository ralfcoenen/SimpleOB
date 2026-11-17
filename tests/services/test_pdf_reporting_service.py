from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from simpleob.accounting.balance_sheet import BalanceSheet
from simpleob.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
from simpleob.accounting.income_statement import IncomeStatement
from simpleob.domain.bvv_evaluation import BvvEvaluation
from simpleob.domain.profit_appropriation_annual_data import (
    ProfitAppropriationAnnualData,
)
from simpleob.hgb.balance_sheet_structure import (
    create_hgb_balance_sheet_structure,
)
from simpleob.services.e_bilanz_preparation_service import (
    EBilanzPreparationResult,
)
from simpleob.services.pdf_reporting_service import (
    PdfReportingService,
)
from simpleob.services.uncovered_equity_deficit_presentation_service import (
    UncoveredEquityDeficitPresentationService,
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


def test_income_statement_pdf_keeps_net_income_and_adds_appropriation() -> None:
    root = FinancialStatementPosition(
        code="HGB.GUV",
        name="GuV",
    )
    income_statement = IncomeStatement(
        income_statement=root,
        amounts={},
    )
    data = ProfitAppropriationAnnualData(
        statutory_reserve_addition=Decimal("1500.00"),
        other_revenue_reserves_addition=Decimal("0.00"),
        statutory_reserve_release=Decimal("0.00"),
        other_revenue_reserves_release=Decimal("0.00"),
        distribution=Decimal("0.00"),
        profit_loss_carryforward=Decimal("0.00"),
    )
    service = PdfReportingService()
    target = Path("GuV.pdf")

    with patch.object(service, "_build_pdf", return_value=target) as build_pdf:
        service.export_income_statement(
            income_statement=income_statement,
            net_income=Decimal("10000.00"),
            company_name="Test UG",
            fiscal_year_name="2026",
            target=target,
            appropriation_data=data,
            previous_carryforward=Decimal("-4000.00"),
        )

    rows = build_pdf.call_args.kwargs["rows"]
    assert rows[1] == ["Jahresüberschuss", "10.000,00"]
    assert ["Ergebnisverwendung", ""] in rows
    assert ["Bilanzgewinn/Bilanzverlust", "4.500,00"] in rows


def _find_position(
    root: FinancialStatementPosition,
    code: str,
) -> FinancialStatementPosition:
    if root.code == code:
        return root
    for child in root.children:
        try:
            return _find_position(child, code)
        except AssertionError:
            continue
    raise AssertionError(f"Position {code} not found")


def _e_bilanz_preparation(equity_amount: Decimal) -> EBilanzPreparationResult:
    assets, liabilities = create_hgb_balance_sheet_structure()
    bank = _find_position(assets, "HGB.266.AKTIVA.B.IV")
    equity = _find_position(liabilities, "HGB.266.PASSIVA.A")
    capital = _find_position(liabilities, "HGB.266.PASSIVA.A.I")
    carryforward = _find_position(liabilities, "HGB.266.PASSIVA.A.IV")
    payables = _find_position(liabilities, "HGB.266.PASSIVA.C.4")
    balance_sheet = BalanceSheet(
        assets=assets,
        liabilities=liabilities,
        amounts={
            assets: Decimal("2000.00"),
            bank: Decimal("2000.00"),
            liabilities: Decimal("2000.00"),
            equity: equity_amount,
            capital: Decimal("1000.00"),
            carryforward: equity_amount - Decimal("1000.00"),
            payables: Decimal("2000.00") - equity_amount,
        },
    )
    income_statement_root = FinancialStatementPosition(
        code="HGB.GUV",
        name="Gewinn- und Verlustrechnung",
    )
    income_statement = IncomeStatement(
        income_statement=income_statement_root,
        amounts={},
    )
    return EBilanzPreparationResult(
        income_statement=income_statement,
        balance_sheet=balance_sheet,
        net_income=Decimal("0.00"),
        amounts={},
        balance_sheet_amounts=dict(balance_sheet.amounts),
        income_statement_amounts={},
    )


def _export_e_bilanz_and_capture_balance_rows(
    *,
    preparation: EBilanzPreparationResult,
    target: Path,
) -> tuple[list[list[str]], BalanceSheet]:
    service = PdfReportingService()
    rows_by_call: list[list[list[str]]] = []
    balance_sheets: list[BalanceSheet] = []
    append_rows = service._append_balance_sheet_rows

    def capture_rows(
        *,
        rows: list[list[str]],
        position: FinancialStatementPosition,
        balance_sheet: BalanceSheet,
        side: str,
        depth: int = 0,
    ) -> None:
        if not rows_by_call:
            rows_by_call.append(rows)
            balance_sheets.append(balance_sheet)
        append_rows(
            rows=rows,
            position=position,
            balance_sheet=balance_sheet,
            side=side,
            depth=depth,
        )

    with patch.object(
        service,
        "_append_balance_sheet_rows",
        side_effect=capture_rows,
    ):
        exported_path = service.export_e_bilanz(
            preparation=preparation,
            company_name="Beispiel UG",
            fiscal_year_name="2026",
            target=target,
        )

    assert exported_path.exists()
    return rows_by_call[0], balance_sheets[0]


def test_e_bilanz_pdf_applies_uncovered_equity_deficit(tmp_path) -> None:
    preparation = _e_bilanz_preparation(Decimal("-5000.00"))

    rows, displayed_balance_sheet = (
        _export_e_bilanz_and_capture_balance_rows(
            preparation=preparation,
            target=tmp_path / "e-bilanz-negativ.pdf",
        )
    )

    assert [
        "  Nicht durch Eigenkapital gedeckter Fehlbetrag",
        "5.000,00",
        "",
    ] in rows
    assert ["  Eigenkapital", "", "0,00"] in rows
    assert ["    Gezeichnetes Kapital", "", "1.000,00"] in rows
    assert ["    Gewinnvortrag/Verlustvortrag", "", "-6.000,00"] in rows
    assert [
        "    Ausgleich des nicht durch Eigenkapital gedeckten Fehlbetrags",
        "",
        "5.000,00",
    ] in rows
    assert rows[-1] == ["Summe", "7.000,00", "7.000,00"]
    assert displayed_balance_sheet.is_balanced()
    assert displayed_balance_sheet.amount_for(
        preparation.balance_sheet.assets
    ) == Decimal("7000.00")
    assert preparation.balance_sheet.amount_for(
        preparation.balance_sheet.assets
    ) == Decimal("2000.00")


def test_e_bilanz_pdf_keeps_positive_equity_presentation(tmp_path) -> None:
    preparation = _e_bilanz_preparation(Decimal("1000.00"))

    rows, displayed_balance_sheet = (
        _export_e_bilanz_and_capture_balance_rows(
            preparation=preparation,
            target=tmp_path / "e-bilanz-positiv.pdf",
        )
    )

    assert not any(
        "Nicht durch Eigenkapital gedeckter Fehlbetrag" in row[0]
        for row in rows
    )
    assert ["  Eigenkapital", "", "1.000,00"] in rows
    assert rows[-1] == ["Summe", "2.000,00", "2.000,00"]
    assert displayed_balance_sheet is preparation.balance_sheet


def test_e_bilanz_pdf_does_not_create_deficit_for_zero_equity(tmp_path) -> None:
    preparation = _e_bilanz_preparation(Decimal("0.00"))

    rows, displayed_balance_sheet = (
        _export_e_bilanz_and_capture_balance_rows(
            preparation=preparation,
            target=tmp_path / "e-bilanz-null.pdf",
        )
    )

    assert not any(
        "Nicht durch Eigenkapital gedeckter Fehlbetrag" in row[0]
        for row in rows
    )
    assert ["  Eigenkapital", "", "0,00"] in rows
    assert rows[-1] == ["Summe", "2.000,00", "2.000,00"]
    assert displayed_balance_sheet is preparation.balance_sheet


def test_e_bilanz_pdf_does_not_apply_existing_presentation_twice(
    tmp_path,
) -> None:
    preparation = _e_bilanz_preparation(Decimal("-5000.00"))
    presented = UncoveredEquityDeficitPresentationService.apply(
        preparation.balance_sheet
    )
    preparation = replace(preparation, balance_sheet=presented)

    rows, displayed_balance_sheet = (
        _export_e_bilanz_and_capture_balance_rows(
            preparation=preparation,
            target=tmp_path / "e-bilanz-bereits-umgegliedert.pdf",
        )
    )

    assert rows[-1] == ["Summe", "7.000,00", "7.000,00"]
    assert sum(
        1
        for row in rows
        if "Nicht durch Eigenkapital gedeckter Fehlbetrag" in row[0]
    ) == 1
    assert displayed_balance_sheet is presented

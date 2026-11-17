from decimal import Decimal
from unittest.mock import Mock

from PySide6.QtWidgets import QApplication

from simpleob.accounting.balance_sheet import BalanceSheet
from simpleob.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
from simpleob.hgb.balance_sheet_structure import (
    create_hgb_balance_sheet_structure,
)
from simpleob.services.pdf_reporting_service import PdfReportingService
from simpleob.services.uncovered_equity_deficit_presentation_service import (
    UncoveredEquityDeficitPresentationService,
)
from simpleob.ui_qt.balance_sheet_frame import BalanceSheetFrame

_APP = QApplication.instance() or QApplication([])


def _find(
    root: FinancialStatementPosition,
    code: str,
) -> FinancialStatementPosition:
    if root.code == code:
        return root
    for child in root.children:
        try:
            return _find(child, code)
        except AssertionError:
            continue
    raise AssertionError(f"Position {code} not found")


def _display_balance_sheet() -> BalanceSheet:
    assets, liabilities = create_hgb_balance_sheet_structure()
    cash = _find(assets, "HGB.266.AKTIVA.B.IV")
    equity = _find(liabilities, "HGB.266.PASSIVA.A")
    capital = _find(liabilities, "HGB.266.PASSIVA.A.I")
    carryforward = _find(liabilities, "HGB.266.PASSIVA.A.IV")
    payables = _find(liabilities, "HGB.266.PASSIVA.C.4")
    raw = BalanceSheet(
        assets=assets,
        liabilities=liabilities,
        amounts={
            assets: Decimal("2000.00"),
            cash: Decimal("2000.00"),
            liabilities: Decimal("2000.00"),
            equity: Decimal("-5000.00"),
            capital: Decimal("1000.00"),
            carryforward: Decimal("-6000.00"),
            payables: Decimal("7000.00"),
        },
    )
    return UncoveredEquityDeficitPresentationService.apply(raw)


def test_zero_equity_parent_children_render_in_gui_and_pdf(tmp_path) -> None:
    balance_sheet = _display_balance_sheet()
    frame = BalanceSheetFrame()
    frame.update_balance_sheet(balance_sheet)

    equity_item = next(
        item
        for item in _tree_items(frame._liabilities_tree)
        if item.text(0) == "Eigenkapital"
    )
    assert equity_item.text(1) == "0,00"
    assert {
        equity_item.child(index).text(0)
        for index in range(equity_item.childCount())
    } >= {
        "Gezeichnetes Kapital",
        "Gewinnvortrag/Verlustvortrag",
        "Ausgleich des nicht durch Eigenkapital gedeckten Fehlbetrags",
    }

    service = PdfReportingService()
    service._build_pdf = Mock(return_value=tmp_path / "bilanz.pdf")
    service.export_balance_sheet(
        balance_sheet=balance_sheet,
        company_name="Test",
        fiscal_year_name="2026",
        target=tmp_path / "bilanz.pdf",
    )
    rows = service._build_pdf.call_args.kwargs["rows"]

    assert [
        "  Eigenkapital",
        "",
        "0,00",
    ] in rows
    assert [
        "    Gewinnvortrag/Verlustvortrag",
        "",
        "-6.000,00",
    ] in rows
    assert [
        "  Nicht durch Eigenkapital gedeckter Fehlbetrag",
        "5.000,00",
        "",
    ] in rows
    assert rows[-1] == ["Summe", "7.000,00", "7.000,00"]

    frame.close()


def test_empty_subtrees_remain_hidden() -> None:
    assets = FinancialStatementPosition("assets", "Aktiva", children=(
        FinancialStatementPosition("empty", "Leer"),
    ))
    liabilities = FinancialStatementPosition("liabilities", "Passiva")
    sheet = BalanceSheet(
        assets=assets,
        liabilities=liabilities,
        amounts={assets: Decimal("0.00"), liabilities: Decimal("0.00")},
    )
    frame = BalanceSheetFrame()

    frame.update_balance_sheet(sheet)

    assert frame._assets_tree.topLevelItemCount() == 0
    frame.close()


def _tree_items(tree):
    for row in range(tree.topLevelItemCount()):
        item = tree.topLevelItem(row)
        yield item
        for child_index in range(item.childCount()):
            child = item.child(child_index)
            yield child
            for grandchild_index in range(child.childCount()):
                yield child.child(grandchild_index)

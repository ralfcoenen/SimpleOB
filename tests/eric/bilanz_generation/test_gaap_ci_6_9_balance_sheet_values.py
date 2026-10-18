"""Tests für die GAAP-CI-Bilanzwerte der Taxonomie 6.9."""

from decimal import Decimal

import pytest

from simpleob.accounting.balance_sheet import BalanceSheet
from simpleob.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
from simpleob.eric.bilanz_generation.gaap_ci_6_9_balance_sheet_values import (
    GaapCi69BalanceSheetValueBuilder,
)
from simpleob.hgb.balance_sheet_structure import (
    create_hgb_balance_sheet_structure,
)
from simpleob.hgb.income_statement_structure import (
    create_hgb_income_statement_structure,
)


def _walk(
    position: FinancialStatementPosition,
) -> tuple[FinancialStatementPosition, ...]:
    result = [position]

    for child in position.children:
        result.extend(_walk(child))

    return tuple(result)


def _position_for(
    root: FinancialStatementPosition,
    code: str,
) -> FinancialStatementPosition:
    for position in _walk(root):
        if position.code == code:
            return position

    raise AssertionError(
        f"position not found: {code}"
    )


def _balance_sheet() -> tuple[
    BalanceSheet,
    FinancialStatementPosition,
]:
    assets, liabilities = create_hgb_balance_sheet_structure()
    income_statement = create_hgb_income_statement_structure()

    cash = _position_for(
        assets,
        "HGB.266.AKTIVA.B.IV",
    )

    subscribed_capital = _position_for(
        liabilities,
        "HGB.266.PASSIVA.A.I",
    )

    net_income = _position_for(
        liabilities,
        "HGB.266.PASSIVA.A.V",
    )

    balance_sheet = BalanceSheet(
        assets=assets,
        liabilities=liabilities,
        amounts={
            assets: Decimal("25000.00"),
            cash: Decimal("25000.00"),
            liabilities: Decimal("25000.00"),
            subscribed_capital: Decimal("20000.00"),
            net_income: Decimal("5000.00"),
        },
    )

    return balance_sheet, income_statement


def test_builds_gaap_ci_values_from_hgb_balance_sheet() -> None:
    balance_sheet, income_statement = _balance_sheet()

    values = GaapCi69BalanceSheetValueBuilder.build(
        balance_sheet=balance_sheet,
        income_statement=income_statement,
    )

    assert values[
        ("bs.ass",)
    ] == Decimal("25000.00")

    assert values[
        ("bs.ass.currAss.cashEquiv",)
    ] == Decimal("25000.00")

    assert values[
        ("bs.eqLiab",)
    ] == Decimal("25000.00")

    assert values[
        ("bs.eqLiab.equity.subscribed",)
    ] == Decimal("20000.00")

    assert values[
        ("bs.eqLiab.equity.netIncome",)
    ] == Decimal("5000.00")


def test_zero_amounts_are_omitted() -> None:
    balance_sheet, income_statement = _balance_sheet()

    other_receivables = _position_for(
        balance_sheet.assets,
        "HGB.266.AKTIVA.B.II.4",
    )

    balance_sheet = BalanceSheet(
        assets=balance_sheet.assets,
        liabilities=balance_sheet.liabilities,
        amounts={
            **balance_sheet.amounts,
            other_receivables: Decimal("0.00"),
        },
    )

    values = GaapCi69BalanceSheetValueBuilder.build(
        balance_sheet=balance_sheet,
        income_statement=income_statement,
    )

    assert (
        "bs.ass.currAss.receiv.other",
    ) not in values


def test_unmapped_positions_are_omitted() -> None:
    balance_sheet, income_statement = _balance_sheet()

    unmapped_position = FinancialStatementPosition(
        code="TEST.UNMAPPED",
        name="Nicht gemappt",
    )

    balance_sheet = BalanceSheet(
        assets=balance_sheet.assets,
        liabilities=balance_sheet.liabilities,
        amounts={
            **balance_sheet.amounts,
            unmapped_position: Decimal("123.45"),
        },
    )

    values = GaapCi69BalanceSheetValueBuilder.build(
        balance_sheet=balance_sheet,
        income_statement=income_statement,
    )

    assert (
        "TEST.UNMAPPED",
    ) not in values


def test_rejects_invalid_balance_sheet() -> None:
    _, income_statement = _balance_sheet()

    with pytest.raises(
        TypeError,
        match="balance_sheet must be a BalanceSheet",
    ):
        GaapCi69BalanceSheetValueBuilder.build(
            balance_sheet=object(),
            income_statement=income_statement,
        )


def test_rejects_invalid_income_statement() -> None:
    balance_sheet, _ = _balance_sheet()

    with pytest.raises(
        TypeError,
        match=(
            "income_statement must be a "
            "FinancialStatementPosition"
        ),
    ):
        GaapCi69BalanceSheetValueBuilder.build(
            balance_sheet=balance_sheet,
            income_statement=object(),
        )

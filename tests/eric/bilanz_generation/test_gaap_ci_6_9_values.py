"""Tests für die ERiC-relevanten GAAP-CI-Werte der Taxonomie 6.9."""

from decimal import Decimal

import pytest

from openbilanz.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
from openbilanz.accounting.income_statement import IncomeStatement
from openbilanz.eric.bilanz_generation.gaap_ci_6_9_values import (
    GaapCi69ValueCalculator,
)
from openbilanz.hgb.income_statement_structure import (
    create_hgb_income_statement_structure,
)


def _positions_by_code(
    position: FinancialStatementPosition,
) -> dict[str, FinancialStatementPosition]:
    result = {
        position.code: position,
    }

    for child in position.children:
        result.update(
            _positions_by_code(child)
        )

    return result


def _income_statement() -> IncomeStatement:
    root = create_hgb_income_statement_structure()
    positions = _positions_by_code(root)

    amounts = {
        positions["HGB.275.GKV.1"]: Decimal("100000.00"),
        positions["HGB.275.GKV.2"]: Decimal("2000.00"),
        positions["HGB.275.GKV.3"]: Decimal("3000.00"),
        positions["HGB.275.GKV.4"]: Decimal("5000.00"),
        positions["HGB.275.GKV.5"]: Decimal("30000.00"),
        positions["HGB.275.GKV.6"]: Decimal("25000.00"),
        positions["HGB.275.GKV.7"]: Decimal("10000.00"),
        positions["HGB.275.GKV.8"]: Decimal("15000.00"),
        positions["HGB.275.GKV.16"]: Decimal("1000.00"),
    }

    return IncomeStatement(
        income_statement=root,
        amounts=amounts,
    )


def test_calculates_gross_trading_profit() -> None:
    values = GaapCi69ValueCalculator.calculate(
        income_statement=_income_statement(),
        net_income=Decimal("15000.00"),
    )

    assert values.gross_trading_profit == Decimal("75000.00")


def test_calculates_operating_total_cost() -> None:
    values = GaapCi69ValueCalculator.calculate(
        income_statement=_income_statement(),
        net_income=Decimal("15000.00"),
    )

    assert values.operating_total_cost == Decimal("30000.00")


def test_uses_existing_net_income() -> None:
    values = GaapCi69ValueCalculator.calculate(
        income_statement=_income_statement(),
        net_income=Decimal("15000.00"),
    )

    assert values.net_income == Decimal("15000.00")


def test_calculates_earnings_after_taxes() -> None:
    values = GaapCi69ValueCalculator.calculate(
        income_statement=_income_statement(),
        net_income=Decimal("15000.00"),
    )

    assert values.earnings_after_taxes == Decimal("16000.00")


def test_supports_negative_inventory_change() -> None:
    income_statement = _income_statement()
    positions = _positions_by_code(
        income_statement.income_statement
    )

    income_statement.amounts[
        positions["HGB.275.GKV.2"]
    ] = Decimal("-2000.00")

    values = GaapCi69ValueCalculator.calculate(
        income_statement=income_statement,
        net_income=Decimal("15000.00"),
    )

    assert values.gross_trading_profit == Decimal("71000.00")


def test_requires_decimal_net_income() -> None:
    with pytest.raises(
        TypeError,
        match="net_income must be a Decimal",
    ):
        GaapCi69ValueCalculator.calculate(
            income_statement=_income_statement(),
            net_income=15000,  # type: ignore[arg-type]
        )


def test_requires_income_statement() -> None:
    with pytest.raises(
        TypeError,
        match="income_statement must be an IncomeStatement",
    ):
        GaapCi69ValueCalculator.calculate(
            income_statement=None,  # type: ignore[arg-type]
            net_income=Decimal("15000.00"),
        )

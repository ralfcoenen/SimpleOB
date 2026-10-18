"""Berechnung der für ERiC benötigten GAAP-CI-Werte der Taxonomie 6.9."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from simpleob.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
from simpleob.accounting.income_statement import IncomeStatement
from simpleob.domain.money import ZERO


@dataclass(frozen=True, slots=True)
class GaapCi69Values:
    """Für das SimpleOB-Standardprofil benötigte GAAP-CI-Summenwerte."""

    net_income: Decimal
    earnings_after_taxes: Decimal
    operating_total_cost: Decimal
    gross_trading_profit: Decimal


class GaapCi69ValueCalculator:
    """Berechnet die vier ERiC-relevanten GuV-Summenwerte."""

    @classmethod
    def calculate(
        cls,
        *,
        income_statement: IncomeStatement,
        net_income: Decimal,
    ) -> GaapCi69Values:
        if not isinstance(income_statement, IncomeStatement):
            raise TypeError(
                "income_statement must be an IncomeStatement"
            )

        if not isinstance(net_income, Decimal):
            raise TypeError("net_income must be a Decimal")

        amounts_by_code = cls._amounts_by_code(
            income_statement=income_statement,
        )

        gross_trading_profit = (
            amounts_by_code["HGB.275.GKV.1"]
            + amounts_by_code["HGB.275.GKV.2"]
            + amounts_by_code["HGB.275.GKV.3"]
            - amounts_by_code["HGB.275.GKV.5"]
        )

        operating_total_cost = (
            gross_trading_profit
            + amounts_by_code["HGB.275.GKV.4"]
            - amounts_by_code["HGB.275.GKV.6"]
            - amounts_by_code["HGB.275.GKV.7"]
            - amounts_by_code["HGB.275.GKV.8"]
        )

        earnings_after_taxes = (
            net_income
            + amounts_by_code["HGB.275.GKV.16"]
        )

        return GaapCi69Values(
            net_income=net_income,
            earnings_after_taxes=earnings_after_taxes,
            operating_total_cost=operating_total_cost,
            gross_trading_profit=gross_trading_profit,
        )

    @classmethod
    def _amounts_by_code(
        cls,
        *,
        income_statement: IncomeStatement,
    ) -> dict[str, Decimal]:
        positions_by_code = cls._positions_by_code(
            position=income_statement.income_statement,
        )

        required_codes = (
            "HGB.275.GKV.1",
            "HGB.275.GKV.2",
            "HGB.275.GKV.3",
            "HGB.275.GKV.4",
            "HGB.275.GKV.5",
            "HGB.275.GKV.6",
            "HGB.275.GKV.7",
            "HGB.275.GKV.8",
            "HGB.275.GKV.16",
        )

        missing_codes = tuple(
            code
            for code in required_codes
            if code not in positions_by_code
        )

        if missing_codes:
            raise ValueError(
                "required HGB income statement positions are missing: "
                + ", ".join(missing_codes)
            )

        return {
            code: income_statement.amounts.get(
                positions_by_code[code],
                ZERO,
            )
            for code in required_codes
        }

    @classmethod
    def _positions_by_code(
        cls,
        *,
        position: FinancialStatementPosition,
    ) -> dict[str, FinancialStatementPosition]:
        result = {
            position.code: position,
        }

        for child in position.children:
            result.update(
                cls._positions_by_code(
                    position=child,
                )
            )

        return result

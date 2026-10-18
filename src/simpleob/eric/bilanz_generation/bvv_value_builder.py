"""FactPlan-Werte für den steuerlichen Betriebsvermögensvergleich."""

from decimal import Decimal

from simpleob.eric.bilanz_generation.fact_plan_resolver import (
    FactPlanPath,
    FactPlanValue,
)

ZERO = Decimal("0.00")


class BvvValueBuilder:
    """Erzeugt die BVV-Werte für einen HGBM-Abschluss."""

    @staticmethod
    def build(
        *,
        current_hgb_equity: Decimal,
        previous_hgb_equity: Decimal,
        current_book_value_difference: Decimal,
        previous_book_value_difference: Decimal = ZERO,
        contribution: Decimal = ZERO,
        withdrawal_distribution: Decimal = ZERO,
    ) -> dict[FactPlanPath, FactPlanValue]:
        """Erzeugt die sieben Werte des Betriebsvermögensvergleichs."""

        current_tax_equity = (
            current_hgb_equity
            + previous_book_value_difference
            + current_book_value_difference
        )

        previous_tax_equity = (
            previous_hgb_equity
            + previous_book_value_difference
        )

        profit_loss = (
            current_tax_equity
            - previous_tax_equity
            - contribution
            + withdrawal_distribution
        )

        return {
            ("BVV.profitLoss",): profit_loss,
            (
                "BVV.profitLoss.assetsCurrentYear",
            ): current_tax_equity,
            (
                "BVV.profitLoss.assetsPreviousYear",
            ): previous_tax_equity,
            (
                "BVV.profitLoss.assetsPreviousYear.assets",
            ): previous_tax_equity,
            (
                "BVV.profitLoss.assetsPreviousYear.capAdjustments",
            ): ZERO,
            (
                "BVV.profitLoss.withdrawalDistrib",
            ): withdrawal_distribution,
            (
                "BVV.profitLoss.contribution",
            ): contribution,
        }

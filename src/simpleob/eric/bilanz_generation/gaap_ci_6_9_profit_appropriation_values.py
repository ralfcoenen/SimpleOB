"""GAAP-CI-Werte der Ergebnisverwendung für Taxonomie 6.9."""

from decimal import Decimal

from simpleob.domain.money import ZERO
from simpleob.domain.profit_appropriation_annual_data import (
    ProfitAppropriationAnnualData,
)
from simpleob.eric.bilanz_generation.fact_plan_resolver import (
    FactPlanPath,
    FactPlanValue,
)


class GaapCi69ProfitAppropriationValueBuilder:
    """Erzeugt FactPlan-Werte für die Ergebnisverwendung."""

    @staticmethod
    def build(
        *,
        net_income: Decimal,
        previous_profit_loss_carryforward: Decimal,
        data: ProfitAppropriationAnnualData,
    ) -> dict[FactPlanPath, FactPlanValue]:
        """Erzeugt die GAAP-CI-Werte der Ergebnisverwendung."""

        if not isinstance(net_income, Decimal):
            raise TypeError("net_income must be a Decimal")

        if not isinstance(
            previous_profit_loss_carryforward,
            Decimal,
        ):
            raise TypeError(
                "previous_profit_loss_carryforward must be a Decimal"
            )

        if not isinstance(
            data,
            ProfitAppropriationAnnualData,
        ):
            raise TypeError(
                "data must be a ProfitAppropriationAnnualData"
            )

        values: dict[FactPlanPath, FactPlanValue] = {}

        gain_loss = (
            net_income
            + previous_profit_loss_carryforward
            + data.statutory_reserve_release
            + data.other_revenue_reserves_release
            - data.statutory_reserve_addition
            - data.other_revenue_reserves_addition
            - data.distribution
            - data.profit_loss_carryforward
        )

        values[("incomeUse.gainLoss",)] = gain_loss

        GaapCi69ProfitAppropriationValueBuilder._add_value(
            values=values,
            concept_name="incomeUse.gainLoss.netIncome",
            amount=net_income,
        )

        if previous_profit_loss_carryforward > ZERO:
            values[
                (
                    "incomeUse.gainLoss."
                    "retainedEarningsPrevYear",
                )
            ] = previous_profit_loss_carryforward
        elif previous_profit_loss_carryforward < ZERO:
            values[
                (
                    "incomeUse.gainLoss."
                    "accumLossPrevYear",
                )
            ] = abs(previous_profit_loss_carryforward)

        release_revenue_reserves = (
            data.statutory_reserve_release
            + data.other_revenue_reserves_release
        )

        GaapCi69ProfitAppropriationValueBuilder._add_value(
            values=values,
            concept_name=(
                "incomeUse.gainLoss.releaseRevenReserves"
            ),
            amount=release_revenue_reserves,
        )
        GaapCi69ProfitAppropriationValueBuilder._add_value(
            values=values,
            concept_name=(
                "incomeUse.gainLoss."
                "releaseRevenReserves.legalRes"
            ),
            amount=data.statutory_reserve_release,
        )
        GaapCi69ProfitAppropriationValueBuilder._add_value(
            values=values,
            concept_name="incomeUse.gainLoss.releaseOtherRes",
            amount=data.other_revenue_reserves_release,
        )

        addition_revenue_reserves = (
            data.statutory_reserve_addition
            + data.other_revenue_reserves_addition
        )

        GaapCi69ProfitAppropriationValueBuilder._add_value(
            values=values,
            concept_name=(
                "incomeUse.gainLoss.additionRevenReserves"
            ),
            amount=addition_revenue_reserves,
        )
        GaapCi69ProfitAppropriationValueBuilder._add_value(
            values=values,
            concept_name=(
                "incomeUse.gainLoss."
                "additionRevenReserves.legalRes"
            ),
            amount=data.statutory_reserve_addition,
        )
        GaapCi69ProfitAppropriationValueBuilder._add_value(
            values=values,
            concept_name="incomeUse.gainLoss.additionOtherRes",
            amount=data.other_revenue_reserves_addition,
        )

        GaapCi69ProfitAppropriationValueBuilder._add_value(
            values=values,
            concept_name="incomeUse.gainLoss.dividensPlanned",
            amount=data.distribution,
        )

        if data.profit_loss_carryforward > ZERO:
            values[
                (
                    "incomeUse.gainLoss."
                    "additionRetainedEarnings",
                )
            ] = data.profit_loss_carryforward
        elif data.profit_loss_carryforward < ZERO:
            values[
                (
                    "incomeUse.gainLoss.additionCummLoss",
                )
            ] = abs(data.profit_loss_carryforward)

        return values

    @staticmethod
    def _add_value(
        *,
        values: dict[FactPlanPath, FactPlanValue],
        concept_name: str,
        amount: Decimal,
    ) -> None:
        if amount == ZERO:
            return

        values[(concept_name,)] = amount

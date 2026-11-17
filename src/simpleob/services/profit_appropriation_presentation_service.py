"""Bereitet eine Bilanz für die gewählte Ergebnisverwendung auf."""

from decimal import Decimal

from simpleob.accounting.balance_sheet import BalanceSheet
from simpleob.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
from simpleob.domain.accounting_control_accounts import (
    AccountingControlAccounts,
)
from simpleob.domain.chart_of_accounts_template import (
    ChartOfAccountsTemplate,
)
from simpleob.domain.money import ZERO
from simpleob.domain.profit_appropriation_annual_data import (
    ProfitAppropriationAnnualData,
)


class ProfitAppropriationPresentationService:
    """Stellt ausdrücklich erfasste Ergebnisverwendung in der Bilanz dar."""

    _STATUTORY_RESERVE = "HGB.266.PASSIVA.A.III.1"
    _OTHER_RESERVES = "HGB.266.PASSIVA.A.III.4"
    _CARRYFORWARD = "HGB.266.PASSIVA.A.IV"
    _RESULT = "HGB.266.PASSIVA.A.V"

    @classmethod
    def remaining_balance_profit_loss(
        cls,
        *,
        net_income: Decimal,
        previous_carryforward: Decimal,
        data: ProfitAppropriationAnnualData,
    ) -> Decimal:
        """Ermittelt den nach den erfassten Verwendungen verbleibenden Betrag."""

        return (
            net_income
            + previous_carryforward
            + data.statutory_reserve_release
            + data.other_revenue_reserves_release
            - data.statutory_reserve_addition
            - data.other_revenue_reserves_addition
            - data.distribution
            - data.profit_loss_carryforward
        )

    @classmethod
    def apply(
        cls,
        *,
        balance_sheet: BalanceSheet,
        data: ProfitAppropriationAnnualData,
        net_income: Decimal,
        previous_carryforward: Decimal,
        chart_of_accounts: ChartOfAccountsTemplate,
        control_accounts: AccountingControlAccounts,
    ) -> BalanceSheet:
        """Ersetzt Ergebnispositionen und passt Reserven/Verbindlichkeit an."""

        if not isinstance(data, ProfitAppropriationAnnualData):
            raise TypeError("data muss ProfitAppropriationAnnualData sein")

        _check_account_position(
            chart_of_accounts,
            control_accounts.statutory_reserve_account,
            cls._STATUTORY_RESERVE,
        )
        _check_account_position(
            chart_of_accounts,
            control_accounts.other_revenue_reserves_account,
            cls._OTHER_RESERVES,
        )
        _check_account_position(
            chart_of_accounts,
            control_accounts.profit_loss_carryforward_account,
            cls._CARRYFORWARD,
        )

        assets = _clone_position(balance_sheet.assets)
        liabilities = _clone_position(balance_sheet.liabilities)
        amounts_by_code = {
            position.code: amount
            for position, amount in balance_sheet.amounts.items()
        }
        positions = {
            position.code: position
            for root in (assets, liabilities)
            for position in _walk(root)
        }
        for code in (
            cls._STATUTORY_RESERVE,
            cls._OTHER_RESERVES,
            cls._CARRYFORWARD,
            cls._RESULT,
        ):
            if code not in positions:
                raise ValueError(
                    f"Die HGB-Bilanzposition {code} fehlt. "
                    "Variante B kann nicht sicher dargestellt werden."
                )

        amounts = {
            position: amounts_by_code.get(code, ZERO)
            for code, position in positions.items()
        }
        amounts[positions[cls._STATUTORY_RESERVE]] = (
            amounts_by_code.get(cls._STATUTORY_RESERVE, ZERO)
            + data.statutory_reserve_addition
            - data.statutory_reserve_release
        )
        amounts[positions[cls._OTHER_RESERVES]] = (
            amounts_by_code.get(cls._OTHER_RESERVES, ZERO)
            + data.other_revenue_reserves_addition
            - data.other_revenue_reserves_release
        )
        amounts[positions[cls._CARRYFORWARD]] = (
            data.profit_loss_carryforward
        )
        amounts[positions[cls._RESULT]] = cls.remaining_balance_profit_loss(
            net_income=net_income,
            previous_carryforward=previous_carryforward,
            data=data,
        )

        if data.distribution:
            liability_code = _distribution_liability_position(
                chart_of_accounts,
                control_accounts.distribution_liability_account,
            )
            liability_position = positions.get(liability_code)
            if liability_position is None:
                raise ValueError(
                    "Die HGB-Position des konfigurierten "
                    "Ausschüttungsverbindlichkeitskontos fehlt. "
                    "Variante B kann nicht sicher dargestellt werden."
                )
            amounts[liability_position] = (
                amounts.get(liability_position, ZERO) + data.distribution
            )

        _aggregate(assets, amounts)
        _aggregate(liabilities, amounts)
        result = BalanceSheet(
            assets=assets,
            liabilities=liabilities,
            amounts=amounts,
        )
        if not result.is_balanced():
            raise ValueError(
                "Variante B würde die Bilanzsumme verändern oder "
                "die Aktiva und Passiva nicht ausgleichen. Prüfen Sie "
                "die erfassten Beträge und Kontenzuordnungen."
            )
        return result


def _walk(
    position: FinancialStatementPosition,
):
    yield position
    for child in position.children:
        yield from _walk(child)


def _clone_position(
    position: FinancialStatementPosition,
) -> FinancialStatementPosition:
    name = position.name
    if position.code == ProfitAppropriationPresentationService._CARRYFORWARD:
        name = "Gewinn-/Verlustvortrag nach Verwendung"
    elif position.code == ProfitAppropriationPresentationService._RESULT:
        name = "Bilanzgewinn/Bilanzverlust"
    return FinancialStatementPosition(
        code=position.code,
        name=name,
        children=tuple(_clone_position(child) for child in position.children),
        category=position.category,
    )


def _aggregate(
    position: FinancialStatementPosition,
    amounts: dict[FinancialStatementPosition, Decimal],
) -> Decimal:
    if not position.children:
        return amounts.get(position, ZERO)
    total = sum(
        (_aggregate(child, amounts) for child in position.children),
        ZERO,
    )
    amounts[position] = total
    return total


def _check_account_position(
    chart: ChartOfAccountsTemplate,
    account_number: str,
    expected_code: str,
) -> None:
    rule = next(
        (
            item for item in chart.account_mapping_rules
            if item.account_number == account_number
        ),
        None,
    )
    if rule is None or not any(
        target is not None and target.code == expected_code
        for target in (rule.debit_position, rule.credit_position)
    ):
        raise ValueError(
            f"Das für die Ergebnisverwendung konfigurierte Konto "
            f"{account_number} ist nicht der HGB-Position {expected_code} "
            "zugeordnet. Variante B kann nicht sicher dargestellt werden."
        )


def _distribution_liability_position(
    chart: ChartOfAccountsTemplate,
    account_number: str,
) -> str:
    rule = next(
        (
            item for item in chart.account_mapping_rules
            if item.account_number == account_number
        ),
        None,
    )
    position = rule.credit_position if rule is not None else None
    if (
        position is None
        or not position.code.startswith("HGB.266.PASSIVA.")
        or position.code.split(".")[3] not in {"B", "C", "D", "E"}
    ):
        raise ValueError(
            "Die HGB-Zuordnung des Ausschüttungsverbindlichkeitskontos "
            f"{account_number} ist keine eindeutige "
            "Passiv-Verbindlichkeit. Variante B kann nicht sicher "
            "dargestellt werden."
        )
    return position.code

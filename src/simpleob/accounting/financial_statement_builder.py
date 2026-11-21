from decimal import Decimal

from simpleob.accounting.account_balance import AccountBalance
from simpleob.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
from simpleob.accounting.mapper import AccountMapper
from simpleob.domain.money import ZERO
from simpleob.services.closing_result import ClosingResult


class FinancialStatementBuilder:
    def __init__(self, mapper: AccountMapper) -> None:
        self._mapper = mapper

    @property
    def account_mapper(self) -> AccountMapper:
        """Liefert den für diesen Builder konfigurierten Kontenmapper."""

        return self._mapper


    def build(
        self,
        balances: tuple[AccountBalance, ...],
        root_positions: tuple[FinancialStatementPosition, ...] = (),
        closing_result: ClosingResult | None = None,
        result_position: FinancialStatementPosition | None = None,
    ) -> dict[FinancialStatementPosition, Decimal]:
        amounts: dict[FinancialStatementPosition, Decimal] = {}

        if balances:
            self.ensure_person_account_balances_supported(balances)

        for balance in balances:
            if balance.balance == ZERO:
                continue
            position, amount = self._mapper.map_balance(
                balance
            )

            amounts[position] = (
                amounts.get(position, ZERO)
                + amount
            )

        if closing_result is not None:
            if result_position is None:
                raise ValueError(
                    "result_position muss angegeben werden, "
                    "wenn closing_result gesetzt ist."
                )

            amounts[result_position] = closing_result.net_income

        for root_position in root_positions:
            self._aggregate_position(root_position, amounts)

        return amounts

    def ensure_person_account_balances_supported(
        self,
        balances: tuple[AccountBalance, ...],
    ) -> None:
        """Validiert Personenkontenklassifikationen und deren HGB-Zuordnung."""
        self._mapper.ensure_person_account_balances_supported(balances)

    def _aggregate_position(
        self,
        position: FinancialStatementPosition,
        amounts: dict[FinancialStatementPosition, Decimal],
    ) -> Decimal:
        if not position.children:
            return amounts.get(position, ZERO)

        total = sum(
            (
                self._aggregate_position(child, amounts)
                for child in position.children
            ),
            start=ZERO,
        )

        amounts[position] = total
        return total

from decimal import Decimal

from openbilanz.accounting.account_balance import AccountBalance
from openbilanz.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
from openbilanz.accounting.mapper import AccountMapper
from openbilanz.domain.money import ZERO


class FinancialStatementBuilder:
    def __init__(self, mapper: AccountMapper) -> None:
        self._mapper = mapper

    def build(
        self,
        balances: tuple[AccountBalance, ...],
        root_positions: tuple[FinancialStatementPosition, ...] = (),
    ) -> dict[FinancialStatementPosition, Decimal]:
        amounts: dict[FinancialStatementPosition, Decimal] = {}

        for balance in balances:
            position = self._mapper.position_for(balance)

            if balance.debit_balance > ZERO:
                amount = balance.debit_balance
            else:
                amount = balance.credit_balance

            amounts[position] = amounts.get(position, ZERO) + amount

        for root_position in root_positions:
            self._aggregate_position(root_position, amounts)

        return amounts
    
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
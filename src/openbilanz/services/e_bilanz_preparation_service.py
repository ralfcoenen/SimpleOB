"""Aufbereitung der HGB-Abschlusswerte für die E-Bilanz."""

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal

from openbilanz.accounting.balance_sheet import BalanceSheet
from openbilanz.accounting.financial_statement_builder import (
    FinancialStatementBuilder,
)
from openbilanz.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
from openbilanz.accounting.income_statement import IncomeStatement
from openbilanz.accounting.ledger import Ledger
from openbilanz.domain.account_type import AccountType
from openbilanz.domain.money import ZERO
from openbilanz.services.closing_result import ClosingResult
from openbilanz.services.closing_service import ClosingService

@dataclass(frozen=True, slots=True)
class EBilanzPreparationResult:
    """Enthält die aufbereiteten HGB-Werte für die E-Bilanz."""

    income_statement: IncomeStatement
    balance_sheet: BalanceSheet

    amounts: dict[
        FinancialStatementPosition,
        Decimal,
    ]

    balance_sheet_amounts: dict[
        FinancialStatementPosition,
        Decimal,
    ]

    income_statement_amounts: dict[
        FinancialStatementPosition,
        Decimal,
    ]


class EBilanzPreparationService:
    """Bereitet GuV und Schlussbilanz für die E-Bilanz auf."""

    def __init__(
        self,
        *,
        statement_builder: FinancialStatementBuilder,
        closing_service: ClosingService,
        account_types: Mapping[str, AccountType],
        assets: FinancialStatementPosition,
        liabilities: FinancialStatementPosition,
        income_summary_account_number: str,
    ) -> None:
        self._statement_builder = statement_builder
        self._closing_service = closing_service
        self._account_types = account_types
        self._assets = assets
        self._liabilities = liabilities
        self._income_summary_account_number = (
            income_summary_account_number
        )

    def prepare(
        self,
        *,
        income_statement: IncomeStatement,
        closed_ledger: Ledger,
    ) -> EBilanzPreparationResult:
        """Verbindet GuV vor Abschluss mit Bilanz nach Abschluss."""

        balance_sheet_account_types = (
            AccountType.ASSET,
            AccountType.LIABILITY,
            AccountType.EQUITY,
        )

        balance_sheet_balances = tuple(
            balance
            for balance in closed_ledger.balances()
            if (
                self._account_types.get(
                    balance.account_number
                )
                in balance_sheet_account_types
                and (
                    balance.debit_balance > ZERO
                    or balance.credit_balance > ZERO
                )
                and (
                    balance.account_number
                    != self._income_summary_account_number
                )
            )
        )

        net_income = self._closing_service.calculate_net_income(
            income_statement=income_statement,
        )

        closing_result = ClosingResult(
            net_income=net_income,
        )

        equity = next(
            position
            for position in self._liabilities.children
            if position.code == "HGB.266.PASSIVA.A"
        )

        result_position = next(
            position
            for position in equity.children
            if position.code == "HGB.266.PASSIVA.A.V"
        )

        balance_sheet_amounts = (
            self._statement_builder.build(
                balances=balance_sheet_balances,
                root_positions=(
                    self._assets,
                    self._liabilities,
                ),
                closing_result=closing_result,
                result_position=result_position,
            )
        )

        balance_sheet = BalanceSheet(
            assets=self._assets,
            liabilities=self._liabilities,
            amounts=balance_sheet_amounts,
        )

        income_statement_amounts = dict(
            income_statement.amounts
        )

        amounts = {
            **income_statement_amounts,
            **balance_sheet_amounts,
        }

        return EBilanzPreparationResult(
            income_statement=income_statement,
            balance_sheet=balance_sheet,
            amounts=amounts,
            balance_sheet_amounts=balance_sheet_amounts,
            income_statement_amounts=(
                income_statement_amounts
            ),
        )

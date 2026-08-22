"""Gemeinsame Erzeugung von Bilanz und GuV."""

from dataclasses import dataclass
from decimal import Decimal

from openbilanz.accounting.account_balance import AccountBalance
from openbilanz.accounting.balance_sheet import BalanceSheet
from openbilanz.accounting.financial_statement_context import (
    FinancialStatementContext,
)
from openbilanz.accounting.income_statement import IncomeStatement
from openbilanz.accounting.ledger import Ledger
from openbilanz.domain.account_type import AccountType
from openbilanz.domain.money import ZERO
from openbilanz.services.closing_result import ClosingResult
from openbilanz.services.closing_service import ClosingService


@dataclass(frozen=True, slots=True)
class FinancialStatementResult:
    """Gemeinsames Ergebnis der laufenden Abschlussauswertung."""

    balance_sheet: BalanceSheet
    income_statement: IncomeStatement
    net_income: Decimal
    closing_result: ClosingResult
    closing_balances: tuple[AccountBalance, ...]
    mapping_error: str | None = None


class FinancialStatementService:
    """Erzeugt Bilanz, GuV und Jahresergebnis."""

    def __init__(
        self,
        *,
        closing_service: ClosingService,
    ) -> None:
        self._closing_service = closing_service

    def build(
        self,
        *,
        ledger: Ledger,
        pre_closing_ledger: Ledger,
        is_closed: bool,
        context: FinancialStatementContext,
    ) -> FinancialStatementResult:
        """Erzeugt die laufenden Abschlussauswertungen."""

        balance_sheet_account_types = (
            AccountType.ASSET,
            AccountType.LIABILITY,
            AccountType.EQUITY,
        )

        income_statement_account_types = (
            AccountType.REVENUE,
            AccountType.EXPENSE,
        )

        balance_sheet_balances = tuple(
            balance
            for balance in ledger.balances()
            if (
                context.account_types.get(
                    balance.account_number
                )
                in balance_sheet_account_types
                and (
                    balance.debit_balance > ZERO
                    or balance.credit_balance > ZERO
                )
            )
        )

        income_statement_ledger = (
            pre_closing_ledger
            if is_closed
            else ledger
        )

        income_statement_balances = tuple(
            balance
            for balance in income_statement_ledger.balances()
            if (
                context.account_types.get(
                    balance.account_number
                )
                in income_statement_account_types
                and (
                    balance.debit_balance > ZERO
                    or balance.credit_balance > ZERO
                )
            )
        )

        closing_balances = (
            balance_sheet_balances
            + income_statement_balances
        )

        income_statement_amounts = (
            context.statement_builder.build(
                balances=income_statement_balances,
                root_positions=(
                    context.income_statement,
                ),
            )
        )

        income_statement = IncomeStatement(
            income_statement=context.income_statement,
            amounts=income_statement_amounts,
        )

        net_income = (
            self._closing_service.calculate_net_income(
                income_statement=income_statement,
            )
        )

        closing_result = ClosingResult(
            net_income=net_income,
        )

        result_position = self._find_position(
            context.liabilities,
            "HGB.266.PASSIVA.A.V",
        )

        if result_position is None:
            raise ValueError(
                "Die HGB-Position für den "
                "Jahresüberschuss/Jahresfehlbetrag "
                "wurde nicht gefunden."
            )

        try:
            balance_sheet_amounts = (
                context.statement_builder.build(
                    balances=balance_sheet_balances,
                    root_positions=(
                        context.assets,
                        context.liabilities,
                    ),
                    closing_result=closing_result,
                    result_position=result_position,
                )
            )
        except ValueError as exc:
            message = str(exc)

            if (
                "no debit position defined for account" not in message
                and "no credit position defined for account" not in message
            ):
                raise

            return FinancialStatementResult(
                balance_sheet=None,
                income_statement=income_statement,
                net_income=net_income,
                closing_result=closing_result,
                closing_balances=closing_balances,
                mapping_error=message,
            )

        balance_sheet = BalanceSheet(
            assets=context.assets,
            liabilities=context.liabilities,
            amounts=balance_sheet_amounts,
        )

        return FinancialStatementResult(
            balance_sheet=balance_sheet,
            income_statement=income_statement,
            net_income=net_income,
            closing_result=closing_result,
            closing_balances=closing_balances,
        )

    @classmethod
    def _find_position(
        cls,
        root,
        code: str,
    ):
        if root.code == code:
            return root

        for child in root.children:
            result = cls._find_position(
                child,
                code,
            )

            if result is not None:
                return result

        return None

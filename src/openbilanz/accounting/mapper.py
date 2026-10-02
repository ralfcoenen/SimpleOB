from decimal import Decimal

from openbilanz.accounting.account_balance import AccountBalance
from openbilanz.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
from openbilanz.domain.account_type import AccountType
from openbilanz.domain.chart_of_accounts_template import (
    ChartOfAccountsTemplate,
)
from openbilanz.domain.money import ZERO


class AccountMapper:
    def __init__(
        self,
        chart_of_accounts: ChartOfAccountsTemplate,
    ) -> None:
        self._chart_of_accounts = chart_of_accounts

    def map_balance(
        self,
        balance: AccountBalance,
    ) -> tuple[FinancialStatementPosition, Decimal]:
        """Liefert Abschlussposition und vorzeichenbehafteten Betrag."""

        for rule in self._chart_of_accounts.account_mapping_rules:
            if rule.account_number != balance.account_number:
                continue

            account = self._chart_of_accounts.get(
                balance.account_number
            )
            if balance.debit_balance > ZERO:
                if rule.debit_position is not None:
                    return (
                        rule.debit_position,
                        balance.debit_balance,
                    )

                if (
                    account.account_type
                    in (
                        AccountType.REVENUE,
                        AccountType.EQUITY,
                    )
                    and rule.credit_position is not None
                ):
                    return (
                        rule.credit_position,
                        -balance.debit_balance,
                    )

                raise ValueError(
                    "no debit position defined for account "
                    f"{balance.account_number}"
                )

            if balance.credit_balance > ZERO:
                if rule.credit_position is not None:
                    return (
                        rule.credit_position,
                        balance.credit_balance,
                    )

                if (
                    account.account_type is AccountType.EXPENSE
                    and rule.debit_position is not None
                ):
                    return (
                        rule.debit_position,
                        -balance.credit_balance,
                    )

                raise ValueError(
                    "no credit position defined for account "
                    f"{balance.account_number}"
                )

        raise ValueError(
            f"no mapping rule found for account {balance.account_number}"
        )

    def position_for(
        self,
        balance: AccountBalance,
    ) -> FinancialStatementPosition:
        position, _ = self.map_balance(
            balance
        )

        return position

from openbilanz.accounting.account_balance import AccountBalance
from openbilanz.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
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

    def position_for(
        self,
        balance: AccountBalance,
    ) -> FinancialStatementPosition:
        for rule in self._chart_of_accounts.account_mapping_rules:
            if rule.account_number == balance.account_number:
                if balance.debit_balance > ZERO:
                    if rule.debit_position is None:
                        raise ValueError(
                            "no debit position defined for account "
                            f"{balance.account_number}"
                        )

                    return rule.debit_position
                
                if balance.credit_balance > ZERO:
                    if rule.credit_position is None:
                        raise ValueError(
                            "no credit position defined for account "
                            f"{balance.account_number}"
                        )

                    return rule.credit_position

        raise ValueError(
            f"no mapping rule found for account {balance.account_number}"
        )


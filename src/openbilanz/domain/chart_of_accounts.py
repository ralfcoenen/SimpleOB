from dataclasses import dataclass

from openbilanz.domain.account import Account
from openbilanz.domain.chart_of_accounts_template import ChartOfAccountsTemplate


@dataclass(frozen=True, slots=True)
class ChartOfAccounts:
    accounts: tuple[Account, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.accounts, tuple):
            raise TypeError("accounts must be a tuple")

        if not all(isinstance(account, Account) for account in self.accounts):
            raise TypeError("all accounts must be Account instances")

    @classmethod
    def from_template(
        cls,
        template: ChartOfAccountsTemplate,
        ) -> "ChartOfAccounts":
        return cls(
            accounts=tuple(
                Account(template=template_account)
                for template_account in template.accounts
            )
        )
        
    def account(self, account_number: str) -> Account:
        for account in self.accounts:
            if account.number == account_number:
                return account

        raise KeyError(account_number)
    
    def __len__(self) -> int:
        return len(self.accounts)
    
    
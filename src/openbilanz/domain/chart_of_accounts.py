from dataclasses import dataclass
from typing import Iterable

from openbilanz.domain.account import Account


@dataclass(frozen=True, slots=True)
class ChartOfAccounts:
    accounts: tuple[Account, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.accounts, tuple):
            raise TypeError("accounts must be a tuple")

        if not all(isinstance(account, Account) for account in self.accounts):
            raise TypeError("all accounts must be Account instances")

    def __len__(self) -> int:
        return len(self.accounts)
    
    
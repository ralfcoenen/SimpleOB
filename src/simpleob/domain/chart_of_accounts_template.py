from collections.abc import Iterator
from dataclasses import dataclass

from simpleob.domain.account_mapping_rule import AccountMappingRule
from simpleob.domain.errors import UnknownAccountError
from simpleob.domain.template_account import TemplateAccount


@dataclass(frozen=True, slots=True)
class ChartOfAccountsTemplate:
    name: str
    accounts: tuple[TemplateAccount, ...]
    account_mapping_rules: tuple[AccountMappingRule, ...] = ()

    def __post_init__(self) -> None:
        self._validate_name()
        self._validate_accounts()
        self._validate_account_mapping_rules()
        
    def _validate_account_mapping_rules(self) -> None:
        account_numbers = {
            account.account_number
            for account in self.accounts
        }

        for rule in self.account_mapping_rules:
            if rule.account_number not in account_numbers:
                raise ValueError(
                    f"unknown account number: {rule.account_number}"
                )

    def __len__(self) -> int:
        return len(self.accounts)

    def __iter__(self) -> Iterator[TemplateAccount]:
        return iter(self.accounts)

    def __contains__(self, account_number: object) -> bool:
        if not isinstance(account_number, str):
            return False

        return self.contains(account_number)

    def contains(self, account_number: str) -> bool:
        return any(
            account.account_number == account_number for account in self.accounts
        )

    def get(self, account_number: str) -> TemplateAccount:
        for account in self.accounts:
            if account.account_number == account_number:
                return account

        raise UnknownAccountError(account_number)

    def _validate_name(self) -> None:
        if not isinstance(self.name, str):
            raise TypeError("name must be a string")

        if not self.name.strip():
            raise ValueError("name must not be blank")

        if self.name != self.name.strip():
            raise ValueError("name must not contain surrounding whitespace")

    def _validate_accounts(self) -> None:
        if not isinstance(self.accounts, tuple):
            raise TypeError("accounts must be a tuple")

        if not all(isinstance(account, TemplateAccount) for account in self.accounts):
            raise TypeError("accounts must contain only TemplateAccount objects")

        account_numbers = [account.account_number for account in self.accounts]

        if len(account_numbers) != len(set(account_numbers)):
            raise ValueError("duplicate account numbers are not allowed")

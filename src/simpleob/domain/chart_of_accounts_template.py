from collections.abc import Iterator
from dataclasses import dataclass

from simpleob.domain.account_mapping_rule import AccountMappingRule
from simpleob.domain.errors import UnknownAccountError
from simpleob.domain.template_account import TemplateAccount
from simpleob.domain.person_account_role import PersonAccountRole


@dataclass(frozen=True, slots=True)
class ChartOfAccountsTemplate:
    name: str
    accounts: tuple[TemplateAccount, ...]
    account_mapping_rules: tuple[AccountMappingRule, ...] = ()
    person_account_roles: tuple[tuple[str, PersonAccountRole], ...] = ()

    def __post_init__(self) -> None:
        self._validate_name()
        self._validate_accounts()
        self._validate_account_mapping_rules()
        self._validate_person_account_roles()

    def _validate_person_account_roles(self) -> None:
        if not isinstance(self.person_account_roles, tuple):
            raise TypeError("person_account_roles must be a tuple")
        account_numbers = {account.account_number for account in self.accounts}
        mapped_numbers: set[str] = set()
        for entry in self.person_account_roles:
            if (
                not isinstance(entry, tuple)
                or len(entry) != 2
                or not isinstance(entry[0], str)
                or not isinstance(entry[1], PersonAccountRole)
            ):
                raise TypeError("person_account_roles entries must be (number, role) tuples")
            account_number, _role = entry
            if account_number not in account_numbers:
                raise ValueError(f"unknown person account number: {account_number}")
            if account_number in mapped_numbers:
                raise ValueError(f"duplicate person account number: {account_number}")
            mapped_numbers.add(account_number)

    @property
    def person_account_numbers(self) -> frozenset[str]:
        return frozenset(number for number, _role in self.person_account_roles)

    def is_person_account(self, account_number: str) -> bool:
        return account_number in self.person_account_numbers

    def person_account_role(self, account_number: str) -> PersonAccountRole | None:
        return next(
            (role for number, role in self.person_account_roles if number == account_number),
            None,
        )
        
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

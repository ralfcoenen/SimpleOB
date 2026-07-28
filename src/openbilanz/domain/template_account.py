from dataclasses import dataclass

from openbilanz.domain.account_type import AccountType


@dataclass(frozen=True, slots=True)
class TemplateAccount:
    account_number: str
    name: str
    account_type: AccountType

    def __post_init__(self) -> None:
        if not isinstance(self.account_number, str):
            raise TypeError("account_number must be a string")

        if not self.account_number.strip():
            raise ValueError("account_number must not be blank")

        if self.account_number != self.account_number.strip():
            raise ValueError("account_number must not have surrounding whitespace")

        if not self.account_number.isdigit():
            raise ValueError("account_number must contain digits only")

        if not isinstance(self.name, str):
            raise TypeError("name must be a string")

        if not self.name.strip():
            raise ValueError("name must not be blank")

        if self.name != self.name.strip():
            raise ValueError("name must not have surrounding whitespace")

        if not isinstance(self.account_type, AccountType):
            raise TypeError("account_type must be an AccountType")

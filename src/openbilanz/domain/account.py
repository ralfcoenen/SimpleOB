from dataclasses import dataclass
from enum import Enum, auto


class AccountType(Enum):
    ASSET = auto()
    LIABILITY = auto()
    EXPENSE = auto()
    REVENUE = auto()


@dataclass(frozen=True, slots=True)
class Account:
    number: str
    name: str
    account_type: AccountType

    def __post_init__(self) -> None:
        if not isinstance(self.number, str):
            raise TypeError("account number must be a string")

        if not self.number.strip():
            raise ValueError("account number must not be empty")

        if not isinstance(self.name, str):
            raise TypeError("account name must be a string")

        if not self.name.strip():
            raise ValueError("account name must not be empty")

        if not isinstance(self.account_type, AccountType):
            raise TypeError("account_type must be an AccountType")

    def __str__(self) -> str:
        return f"{self.number} – {self.name}"

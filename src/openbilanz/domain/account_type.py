from enum import Enum, auto


class AccountType(Enum):
    ASSET = auto()
    LIABILITY = auto()
    EXPENSE = auto()
    REVENUE = auto()

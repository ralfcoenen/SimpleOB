"""Position einer Eröffnungsbilanz."""

from dataclasses import dataclass
from decimal import Decimal

from openbilanz.domain.account import Account
from openbilanz.domain.account_type import AccountType
from openbilanz.domain.money import to_decimal


@dataclass(frozen=True, slots=True)
class OpeningBalanceItem:
    """Eine Position der Eröffnungsbilanz."""

    account: Account
    amount: Decimal

    def __post_init__(self) -> None:
        if not isinstance(self.account, Account):
            raise TypeError("account muss ein Account sein.")

        normalized_amount = to_decimal(self.amount)

        if normalized_amount < Decimal("0.00"):
            raise ValueError(
                "Der Anfangsbestand darf nicht negativ sein."
            )
            
        if self.account.account_type not in (
            AccountType.ASSET,
            AccountType.LIABILITY,
            AccountType.EQUITY,
        ):
            raise ValueError(
                "Für eine Eröffnungsbilanz sind nur Bestandskonten zulässig."
            )

        object.__setattr__(
            self,
            "amount",
            normalized_amount,
        )

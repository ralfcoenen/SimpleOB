"""Position einer Eröffnungsbilanz."""

from dataclasses import dataclass
from decimal import Decimal

from simpleob.domain.account import Account
from simpleob.domain.account_type import AccountType
from simpleob.domain.entry_side import EntrySide
from simpleob.domain.money import to_decimal


@dataclass(frozen=True, slots=True)
class OpeningBalanceItem:
    """Ein Soll- oder Habensaldo eines Bestandskontos."""

    account: Account
    amount: Decimal
    side: EntrySide

    def __post_init__(self) -> None:
        if not isinstance(self.account, Account):
            raise TypeError("account muss ein Account sein.")

        normalized_amount = to_decimal(self.amount)
        side = EntrySide.from_value(self.side)

        if normalized_amount < Decimal("0.00"):
            raise ValueError(
                "Der Anfangssaldo darf nicht negativ sein; "
                "die Richtung wird über Soll oder Haben angegeben."
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
        object.__setattr__(self, "side", side)

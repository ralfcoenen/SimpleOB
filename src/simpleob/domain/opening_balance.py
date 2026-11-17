"""Eröffnungsbilanz."""

from dataclasses import dataclass
from decimal import Decimal

from simpleob.domain.entry_side import EntrySide
from simpleob.domain.money import ZERO
from simpleob.domain.opening_balance_item import (
    OpeningBalanceItem,
)


@dataclass(frozen=True, slots=True)
class OpeningBalance:
    """Eine vollständige Eröffnungsbilanz."""

    items: tuple[OpeningBalanceItem, ...]

    def __post_init__(self) -> None:
        account_numbers = [item.account.number for item in self.items]
        if len(account_numbers) != len(set(account_numbers)):
            raise ValueError(
                "Jedes Konto darf in der Eröffnungsbilanz nur "
                "einen Nettosaldo haben."
            )

    @property
    def is_balanced(self) -> bool:
        return self.total_debits == self.total_credits

    @property
    def total_debits(self) -> Decimal:
        return sum(
            (
                item.amount
                for item in self.items
                if item.side is EntrySide.DEBIT
            ),
            start=ZERO,
        )

    @property
    def total_credits(self) -> Decimal:
        return sum(
            (
                item.amount
                for item in self.items
                if item.side is EntrySide.CREDIT
            ),
            start=ZERO,
        )


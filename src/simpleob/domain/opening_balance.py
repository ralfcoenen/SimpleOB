"""Eröffnungsbilanz."""

from dataclasses import dataclass
from decimal import Decimal

from simpleob.domain.account_type import AccountType
from simpleob.domain.money import ZERO
from simpleob.domain.opening_balance_item import (
    OpeningBalanceItem,
)


@dataclass(frozen=True, slots=True)
class OpeningBalance:
    """Eine vollständige Eröffnungsbilanz."""

    items: tuple[OpeningBalanceItem, ...]

    @property
    def is_balanced(self) -> bool:
        return (
            self.total_assets
            == self.total_liabilities_and_equity
        )
        
    @property
    def total_assets(self) -> Decimal:
        return sum(
            (
                item.amount
                for item in self.items
                if item.account.account_type is AccountType.ASSET
            ),
            start=ZERO,
        )
    
    @property
    def total_liabilities_and_equity(self) -> Decimal:
        return sum(
            (
                item.amount
                for item in self.items
                if item.account.account_type
                in (
                    AccountType.LIABILITY,
                    AccountType.EQUITY,
                )
            ),
            start=ZERO,
        )


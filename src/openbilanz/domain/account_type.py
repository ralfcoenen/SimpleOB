"""Betriebswirtschaftliche Kontentypen."""

from enum import Enum, auto


class AccountType(Enum):
    """Grundlegende betriebswirtschaftliche Kategorien eines Kontos."""

    ASSET = auto()
    LIABILITY = auto()
    EQUITY = auto()
    REVENUE = auto()
    EXPENSE = auto()
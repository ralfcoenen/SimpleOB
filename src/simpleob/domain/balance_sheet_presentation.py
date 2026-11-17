"""Darstellungsvariante der Bilanz für ein Geschäftsjahr."""

from enum import Enum


class BalanceSheetPresentation(str, Enum):
    """Bilanz vor oder unter Berücksichtigung der Ergebnisverwendung."""

    BEFORE_APPROPRIATION = "A"
    AFTER_APPROPRIATION = "B"

"""Herkunft von Abschreibungen auf Anlagegüter."""

from enum import Enum


class DepreciationSource(Enum):
    """Herkunft einer Abschreibung."""

    CALCULATED = "CALCULATED"
    IMPORTED = "IMPORTED"

"""Arten von Abschreibungen auf Anlagegüter."""

from enum import Enum


class DepreciationKind(Enum):
    """Fachliche Art einer Abschreibung."""

    LINEAR = "LINEAR"
    DEGRESSIVE = "DEGRESSIVE"
    SPECIAL = "SPECIAL"
    OTHER = "OTHER"

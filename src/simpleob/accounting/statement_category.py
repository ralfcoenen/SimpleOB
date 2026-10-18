"""Fachliche Kategorien von Abschlusspositionen."""

from enum import Enum


class StatementCategory(Enum):
    """Fachliche Bedeutung einer Abschlussposition."""

    ASSET = "asset"
    LIABILITY = "liability"
    INCOME = "income"
    EXPENSE = "expense"
    RESULT = "result"
    NEUTRAL = "neutral"
    

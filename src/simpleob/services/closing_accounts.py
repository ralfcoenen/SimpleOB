"""Konten für den Jahresabschluss."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ClosingAccounts:
    """Konten, die für den Jahresabschluss verwendet werden."""

    income_summary_account: str
    profit_account: str
    loss_account: str

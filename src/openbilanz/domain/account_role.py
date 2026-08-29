from enum import StrEnum


class AccountRole(StrEnum):
    """Fachliche Rolle eines mandantenspezifischen Kontos."""

    RECEIVABLE = "RECEIVABLE"
    PAYABLE = "PAYABLE"
    BANK = "BANK"
    CASH = "CASH"

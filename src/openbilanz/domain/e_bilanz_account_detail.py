"""Kontennachweis für die E-Bilanz."""

from dataclasses import dataclass
from decimal import Decimal

from openbilanz.accounting.financial_statement_position import (
    FinancialStatementPosition,
)


@dataclass(frozen=True, slots=True)
class EBilanzAccountDetail:
    """Ein unverdichteter Kontennachweis der E-Bilanz."""

    position: FinancialStatementPosition
    account_number: str
    account_description: str
    balance: Decimal

    def __post_init__(self) -> None:
        if not isinstance(
            self.position,
            FinancialStatementPosition,
        ):
            raise TypeError(
                "position muss eine FinancialStatementPosition sein."
            )

        if not isinstance(self.account_number, str):
            raise TypeError(
                "account_number muss eine Zeichenkette sein."
            )

        if not self.account_number.strip():
            raise ValueError(
                "account_number darf nicht leer sein."
            )

        if not isinstance(self.account_description, str):
            raise TypeError(
                "account_description muss eine Zeichenkette sein."
            )

        if not self.account_description.strip():
            raise ValueError(
                "account_description darf nicht leer sein."
            )

        if not isinstance(self.balance, Decimal):
            raise TypeError(
                "balance muss ein Decimal sein."
            )

        object.__setattr__(
            self,
            "account_number",
            self.account_number.strip(),
        )
        object.__setattr__(
            self,
            "account_description",
            self.account_description.strip(),
        )

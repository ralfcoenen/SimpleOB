"""Buchungsvorschläge zur Umsetzung einer Ergebnisverwendung."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from openbilanz.domain.money import to_decimal
from openbilanz.domain.profit_appropriation_posting_type import (
    ProfitAppropriationPostingType,
)


@dataclass(frozen=True, slots=True)
class ProfitAppropriationPostingProposal:
    """Noch nicht gebuchte Umsetzung eines Ergebnisverwendungsbeschlusses."""

    posting_type: ProfitAppropriationPostingType
    booking_date: date
    amount: Decimal
    debit_account_number: str
    credit_account_number: str

    def __post_init__(self) -> None:
        if not isinstance(
            self.posting_type,
            ProfitAppropriationPostingType,
        ):
            raise TypeError(
                "posting_type must be a ProfitAppropriationPostingType"
            )

        if not isinstance(self.booking_date, date):
            raise TypeError("booking_date must be a date")

        amount = to_decimal(self.amount)

        if amount <= Decimal("0.00"):
            raise ValueError(
                "amount must be greater than 0.00"
            )

        debit_account_number = self._normalize_account_number(
            self.debit_account_number,
            field_name="debit_account_number",
        )
        credit_account_number = self._normalize_account_number(
            self.credit_account_number,
            field_name="credit_account_number",
        )

        if debit_account_number == credit_account_number:
            raise ValueError(
                "debit_account_number and credit_account_number "
                "must be different"
            )

        object.__setattr__(
            self,
            "amount",
            amount,
        )
        object.__setattr__(
            self,
            "debit_account_number",
            debit_account_number,
        )
        object.__setattr__(
            self,
            "credit_account_number",
            credit_account_number,
        )

    @staticmethod
    def _normalize_account_number(
        value: str,
        *,
        field_name: str,
    ) -> str:
        if not isinstance(value, str):
            raise TypeError(
                f"{field_name} must be a string"
            )

        normalized = value.strip()

        if not normalized:
            raise ValueError(
                f"{field_name} must not be blank"
            )

        return normalized

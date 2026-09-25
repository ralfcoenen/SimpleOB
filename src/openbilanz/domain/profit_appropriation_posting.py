"""Bestätigte Buchungen zur Umsetzung einer Ergebnisverwendung."""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

from openbilanz.domain.money import to_decimal
from openbilanz.domain.profit_appropriation_posting_type import (
    ProfitAppropriationPostingType,
)


@dataclass(frozen=True, slots=True)
class ProfitAppropriationPosting:
    """Eine bestätigte und gebuchte Umsetzung einer Ergebnisverwendung."""

    source_fiscal_year_end: date
    posting_date: date
    amount: Decimal
    booking_id: UUID
    posting_type: ProfitAppropriationPostingType
    posting_id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        if not isinstance(
            self.source_fiscal_year_end,
            date,
        ):
            raise TypeError(
                "source_fiscal_year_end must be a date"
            )

        if not isinstance(
            self.posting_date,
            date,
        ):
            raise TypeError(
                "posting_date must be a date"
            )

        amount = to_decimal(self.amount)

        if amount <= Decimal("0.00"):
            raise ValueError(
                "amount must be greater than 0.00"
            )

        if not isinstance(
            self.booking_id,
            UUID,
        ):
            raise TypeError(
                "booking_id must be a UUID"
            )

        if not isinstance(
            self.posting_type,
            ProfitAppropriationPostingType,
        ):
            raise TypeError(
                "posting_type must be a "
                "ProfitAppropriationPostingType"
            )

        if not isinstance(
            self.posting_id,
            UUID,
        ):
            raise TypeError(
                "posting_id must be a UUID"
            )

        object.__setattr__(
            self,
            "amount",
            amount,
        )

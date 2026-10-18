"""Steuerlich abweichende Abschreibungen von Anlagegütern."""

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from simpleob.domain.money import to_decimal


@dataclass(frozen=True, slots=True)
class TaxDepreciationAdjustment:
    """Steuerliche AfA-Abweichung zu einer bestätigten Abschreibung."""

    depreciation_id: UUID
    commercial_amount: Decimal
    tax_amount: Decimal

    def __post_init__(self) -> None:
        if not isinstance(
            self.depreciation_id,
            UUID,
        ):
            raise TypeError(
                "depreciation_id must be a UUID"
            )

        commercial_amount = to_decimal(
            self.commercial_amount
        )
        tax_amount = to_decimal(
            self.tax_amount
        )

        if commercial_amount <= Decimal("0.00"):
            raise ValueError(
                "commercial_amount must be greater than 0.00"
            )

        if tax_amount < Decimal("0.00"):
            raise ValueError(
                "tax_amount must not be negative"
            )

        if tax_amount == commercial_amount:
            raise ValueError(
                "tax_amount must differ from commercial_amount"
            )

        object.__setattr__(
            self,
            "commercial_amount",
            commercial_amount,
        )
        object.__setattr__(
            self,
            "tax_amount",
            tax_amount,
        )

    @property
    def difference(self) -> Decimal:
        """Steuerliche AfA abzüglich handelsrechtlicher AfA."""

        return self.tax_amount - self.commercial_amount

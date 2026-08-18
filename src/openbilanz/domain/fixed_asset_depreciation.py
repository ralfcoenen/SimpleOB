"""Bestätigte Abschreibungen von Anlagegütern."""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

from openbilanz.domain.depreciation_kind import DepreciationKind
from openbilanz.domain.depreciation_source import DepreciationSource
from openbilanz.domain.money import to_decimal


@dataclass(frozen=True, slots=True)
class FixedAssetDepreciation:
    """Eine bestätigte und gebuchte Abschreibung eines Anlageguts."""

    fixed_asset_id: UUID
    fiscal_year_end: date
    depreciation_date: date
    amount: Decimal
    booking_id: UUID
    kind: DepreciationKind
    source: DepreciationSource
    depreciation_id: UUID = field(
        default_factory=uuid4
    )

    def __post_init__(self) -> None:
        if not isinstance(
            self.fixed_asset_id,
            UUID,
        ):
            raise TypeError(
                "fixed_asset_id must be a UUID"
            )

        if not isinstance(
            self.fiscal_year_end,
            date,
        ):
            raise TypeError(
                "fiscal_year_end must be a date"
            )

        if not isinstance(
            self.depreciation_date,
            date,
        ):
            raise TypeError(
                "depreciation_date must be a date"
            )

        amount = to_decimal(
            self.amount
        )

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
            self.kind,
            DepreciationKind,
        ):
            raise TypeError(
                "kind must be a DepreciationKind"
            )

        if not isinstance(
            self.source,
            DepreciationSource,
        ):
            raise TypeError(
                "source must be a DepreciationSource"
            )

        if (
            self.source
            is DepreciationSource.CALCULATED
            and self.kind
            is not DepreciationKind.LINEAR
        ):
            raise ValueError(
                "Calculated depreciation must be linear."
            )

        if not isinstance(
            self.depreciation_id,
            UUID,
        ):
            raise TypeError(
                "depreciation_id must be a UUID"
            )

        object.__setattr__(
            self,
            "amount",
            amount,
        )
    
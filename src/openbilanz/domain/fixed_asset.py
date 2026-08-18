"""Anlagegüter der kleinen Anlagenbuchhaltung."""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

from openbilanz.domain.fixed_asset_status import (
    FixedAssetStatus,
)
from openbilanz.domain.money import to_decimal


@dataclass(frozen=True, slots=True)
class FixedAsset:
    """Ein einzelnes Anlagegut."""

    company_id: UUID
    asset_code: str
    description: str
    position_code: str
    asset_account_number: str
    depreciation_expense_account_number: str
    acquisition_date: date
    acquisition_cost: Decimal
    depreciation_start_date: date
    useful_life_months: int
    fixed_asset_id: UUID = field(
        default_factory=uuid4
    )
    status: FixedAssetStatus = FixedAssetStatus.ACTIVE
    disposal_date: date | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.company_id, UUID):
            raise TypeError(
                "company_id must be a UUID"
            )

        if not isinstance(self.fixed_asset_id, UUID):
            raise TypeError(
                "fixed_asset_id must be a UUID"
            )

        asset_code = self._normalize_text(
            self.asset_code,
            field_name="asset_code",
        )
        description = self._normalize_text(
            self.description,
            field_name="description",
        )
        position_code = self._normalize_text(
            self.position_code,
            field_name="position_code",
        )
        
        asset_account_number = self._normalize_text(
            self.asset_account_number,
            field_name="asset_account_number",
        )

        depreciation_expense_account_number = (
            self._normalize_text(
                self.depreciation_expense_account_number,
                field_name=(
                    "depreciation_expense_account_number"
                ),
            )
        )

        if not position_code.startswith(
            "HGB.266.AKTIVA.A"
        ):
            raise ValueError(
                "position_code must reference "
                "fixed assets"
            )
        
        

        if not isinstance(
            self.acquisition_date,
            date,
        ):
            raise TypeError(
                "acquisition_date must be a date"
            )

        acquisition_cost = to_decimal(
            self.acquisition_cost
        )

        if acquisition_cost <= Decimal("0.00"):
            raise ValueError(
                "acquisition_cost must be greater "
                "than 0.00"
            )

        if not isinstance(
            self.depreciation_start_date,
            date,
        ):
            raise TypeError(
                "depreciation_start_date must be a date"
            )

        if (
            self.depreciation_start_date
            < self.acquisition_date
        ):
            raise ValueError(
                "depreciation_start_date must not be "
                "before acquisition_date"
            )

        if not isinstance(
            self.useful_life_months,
            int,
        ):
            raise TypeError(
                "useful_life_months must be an int"
            )

        if self.useful_life_months <= 0:
            raise ValueError(
                "useful_life_months must be greater "
                "than zero"
            )

        if not isinstance(
            self.status,
            FixedAssetStatus,
        ):
            raise TypeError(
                "status must be a FixedAssetStatus"
            )

        if (
            self.disposal_date is not None
            and not isinstance(
                self.disposal_date,
                date,
            )
        ):
            raise TypeError(
                "disposal_date must be a date or None"
            )

        if (
            self.disposal_date is not None
            and self.disposal_date
            < self.acquisition_date
        ):
            raise ValueError(
                "disposal_date must not be before "
                "acquisition_date"
            )

        if (
            self.status is FixedAssetStatus.ACTIVE
            and self.disposal_date is not None
        ):
            raise ValueError(
                "an active fixed asset must not have "
                "a disposal_date"
            )

        if (
            self.status is FixedAssetStatus.DISPOSED
            and self.disposal_date is None
        ):
            raise ValueError(
                "a disposed fixed asset requires "
                "a disposal_date"
            )

        object.__setattr__(
            self,
            "asset_code",
            asset_code,
        )
        object.__setattr__(
            self,
            "description",
            description,
        )
        object.__setattr__(
            self,
            "position_code",
            position_code,
        )
        object.__setattr__(
            self,
            "asset_account_number",
            asset_account_number,
        )
        object.__setattr__(
            self,
            "depreciation_expense_account_number",
            depreciation_expense_account_number,
        )
        object.__setattr__(
            self,
            "acquisition_cost",
            acquisition_cost,
        )

    @staticmethod
    def _normalize_text(
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

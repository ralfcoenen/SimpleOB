"""Vorschläge für lineare Anlagenabschreibungen."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from openbilanz.domain.money import to_decimal


@dataclass(frozen=True, slots=True)
class DepreciationProposal:
    """Noch nicht gebuchte lineare Abschreibung."""

    fixed_asset_id: UUID
    depreciation_date: date
    amount: Decimal
    expense_account_number: str
    asset_account_number: str

    def __post_init__(self) -> None:
        if not isinstance(
            self.fixed_asset_id,
            UUID,
        ):
            raise TypeError(
                "fixed_asset_id must be a UUID"
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

        expense_account_number = (
            self._normalize_account_number(
                self.expense_account_number,
                field_name="expense_account_number",
            )
        )

        asset_account_number = (
            self._normalize_account_number(
                self.asset_account_number,
                field_name="asset_account_number",
            )
        )

        object.__setattr__(
            self,
            "amount",
            amount,
        )
        object.__setattr__(
            self,
            "expense_account_number",
            expense_account_number,
        )
        object.__setattr__(
            self,
            "asset_account_number",
            asset_account_number,
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

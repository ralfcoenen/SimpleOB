"""Berechnung linearer Anlagenabschreibungen."""

from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from openbilanz.domain.depreciation_proposal import (
    DepreciationProposal,
)
from openbilanz.domain.fiscal_year import FiscalYear
from openbilanz.domain.fixed_asset import FixedAsset
from openbilanz.domain.money import to_decimal

_CENT = Decimal("0.01")
_MEMORY_VALUE = Decimal("1.00")


class DepreciationService:
    """Ermittelt Vorschläge für lineare Anlagenabschreibungen."""

    def build_proposal(
        self,
        *,
        fixed_asset: FixedAsset,
        fiscal_year: FiscalYear,
        previous_depreciation: Decimal,
        expense_account_number: str,
        asset_account_number: str,
    ) -> DepreciationProposal | None:
        """Ermittelt die lineare Abschreibung eines Geschäftsjahres."""

        if not isinstance(
            fixed_asset,
            FixedAsset,
        ):
            raise TypeError(
                "fixed_asset must be a FixedAsset"
            )

        if not isinstance(
            fiscal_year,
            FiscalYear,
        ):
            raise TypeError(
                "fiscal_year must be a FiscalYear"
            )

        previous_depreciation = to_decimal(
            previous_depreciation
        )

        if previous_depreciation < Decimal("0.00"):
            raise ValueError(
                "previous_depreciation must not be negative"
            )

        depreciable_remaining = (
            fixed_asset.acquisition_cost
            - previous_depreciation
            - _MEMORY_VALUE
        )

        if depreciable_remaining <= Decimal("0.00"):
            return None

        if fixed_asset.acquisition_date > fiscal_year.end_date:
            return None

        annual_depreciation = (
            fixed_asset.acquisition_cost
            * Decimal("12")
            / Decimal(fixed_asset.useful_life_months)
        )

        months = self._depreciation_months(
            fixed_asset=fixed_asset,
            fiscal_year=fiscal_year,
        )

        if months <= 0:
            return None

        amount = (
            annual_depreciation
            * Decimal(months)
            / Decimal("12")
        ).quantize(
            _CENT,
            rounding=ROUND_HALF_UP,
        )

        amount = min(
            amount,
            depreciable_remaining,
        )

        amount = amount.quantize(
            _CENT,
            rounding=ROUND_HALF_UP,
        )

        if amount <= Decimal("0.00"):
            return None

        return DepreciationProposal(
            fixed_asset_id=fixed_asset.fixed_asset_id,
            depreciation_date=fiscal_year.end_date,
            amount=amount,
            expense_account_number=expense_account_number,
            asset_account_number=asset_account_number,
        )
    def build_proposal_until(
        self,
        *,
        fixed_asset: FixedAsset,
        fiscal_year: FiscalYear,
        previous_depreciation: Decimal,
        expense_account_number: str,
        asset_account_number: str,
        depreciation_date: date,
        current_fiscal_year_depreciation: Decimal = Decimal("0.00"),
    ) -> DepreciationProposal | None:
        """Ermittelt die lineare AfA bis zu einem Stichtag."""

        if not isinstance(
            depreciation_date,
            date,
        ):
            raise TypeError(
                "depreciation_date must be a date"
            )

        if (
            depreciation_date < fiscal_year.start_date
            or depreciation_date > fiscal_year.end_date
        ):
            raise ValueError(
                "depreciation_date must be within "
                "the fiscal year"
            )

        if not isinstance(
            fixed_asset,
            FixedAsset,
        ):
            raise TypeError(
                "fixed_asset must be a FixedAsset"
            )

        previous_depreciation = to_decimal(
            previous_depreciation
        )

        if previous_depreciation < Decimal("0.00"):
            raise ValueError(
                "previous_depreciation must not be negative"
            )

        current_fiscal_year_depreciation = to_decimal(
            current_fiscal_year_depreciation
        )

        if current_fiscal_year_depreciation < Decimal("0.00"):
            raise ValueError(
                "current_fiscal_year_depreciation "
                "must not be negative"
            )

        depreciable_remaining = (
            fixed_asset.acquisition_cost
            - previous_depreciation
            - _MEMORY_VALUE
        )

        if depreciable_remaining <= Decimal("0.00"):
            return None

        if fixed_asset.acquisition_date > depreciation_date:
            return None

        annual_depreciation = (
            fixed_asset.acquisition_cost
            * Decimal("12")
            / Decimal(fixed_asset.useful_life_months)
        )

        start_date = max(
            fixed_asset.depreciation_start_date,
            fiscal_year.start_date,
        )

        if start_date > depreciation_date:
            return None

        months = (
            (depreciation_date.year - start_date.year) * 12
            + depreciation_date.month
            - start_date.month
            + 1
        )

        target_amount = (
            annual_depreciation
            * Decimal(months)
            / Decimal("12")
        ).quantize(
            _CENT,
            rounding=ROUND_HALF_UP,
        )

        amount = (
            target_amount
            - current_fiscal_year_depreciation
        )

        if amount <= Decimal("0.00"):
            return None

        amount = min(
            amount,
            depreciable_remaining,
        ).quantize(
            _CENT,
            rounding=ROUND_HALF_UP,
        )

        if amount <= Decimal("0.00"):
            return None

        return DepreciationProposal(
            fixed_asset_id=fixed_asset.fixed_asset_id,
            depreciation_date=depreciation_date,
            amount=amount,
            expense_account_number=expense_account_number,
            asset_account_number=asset_account_number,
        )

    @staticmethod
    def _depreciation_months(
        *,
        fixed_asset: FixedAsset,
        fiscal_year: FiscalYear,
    ) -> int:
        """Ermittelt die AfA-Monate innerhalb des Geschäftsjahres."""

        start_date = max(
            fixed_asset.depreciation_start_date,
            fiscal_year.start_date,
        )

        if start_date > fiscal_year.end_date:
            return 0

        return (
            (
                fiscal_year.end_date.year
                - start_date.year
            )
            * 12
            + fiscal_year.end_date.month
            - start_date.month
            + 1
        )

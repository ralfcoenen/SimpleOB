"""Ermittlung des Buchwerts eines Anlageguts."""

from datetime import date
from decimal import Decimal

from openbilanz.database.fixed_asset_depreciation_repository import (
    FixedAssetDepreciationRepository,
)
from openbilanz.domain.fixed_asset import FixedAsset
from openbilanz.domain.money import to_decimal


class FixedAssetBookValueService:
    """Ermittelt Buchwerte aus tatsächlich gebuchten Abschreibungen."""

    def __init__(
        self,
        *,
        depreciation_repository: FixedAssetDepreciationRepository,
    ) -> None:
        self._depreciation_repository = (
            depreciation_repository
        )

    def depreciation_until(
        self,
        *,
        fixed_asset: FixedAsset,
        reference_date: date,
    ) -> Decimal:
        """Summiert gebuchte AfA bis einschließlich Stichtag."""

        if not isinstance(
            fixed_asset,
            FixedAsset,
        ):
            raise TypeError(
                "fixed_asset must be a FixedAsset"
            )

        if not isinstance(
            reference_date,
            date,
        ):
            raise TypeError(
                "reference_date must be a date"
            )

        depreciations = (
            self._depreciation_repository.list_for_fixed_asset(
                fixed_asset.fixed_asset_id
            )
        )

        total = sum(
            (
                depreciation.amount
                for depreciation in depreciations
                if depreciation.depreciation_date
                <= reference_date
            ),
            Decimal("0.00"),
        )

        return to_decimal(total)

    def book_value_at(
        self,
        *,
        fixed_asset: FixedAsset,
        reference_date: date,
    ) -> Decimal:
        """Ermittelt den Buchwert aus den gebuchten Abschreibungen."""

        depreciation = self.depreciation_until(
            fixed_asset=fixed_asset,
            reference_date=reference_date,
        )

        book_value = (
            fixed_asset.acquisition_cost
            - depreciation
        )

        if book_value < Decimal("0.00"):
            raise ValueError(
                "Die gebuchten Abschreibungen übersteigen "
                "die Anschaffungskosten."
            )

        return to_decimal(
            book_value
        )

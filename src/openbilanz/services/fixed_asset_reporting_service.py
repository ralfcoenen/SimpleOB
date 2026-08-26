"""Erstellung von Anlagenberichten."""

from datetime import date
from uuid import UUID

from openbilanz.database.fixed_asset_depreciation_repository import (
    FixedAssetDepreciationRepository,
)
from openbilanz.database.fixed_asset_movement_repository import (
    FixedAssetMovementRepository,
)
from openbilanz.database.fixed_asset_repository import (
    FixedAssetRepository,
)
from openbilanz.domain.fixed_asset_movement_type import (
    FixedAssetMovementType,
)
from openbilanz.domain.money import ZERO, to_decimal
from openbilanz.reporting.fixed_asset_report import (
    FixedAssetReport,
    FixedAssetReportRow,
)


class FixedAssetReportingService:
    """Erzeugt Anlagenberichte aus gebuchten Anlagendaten."""

    def __init__(
        self,
        *,
        fixed_asset_repository: FixedAssetRepository,
        depreciation_repository: FixedAssetDepreciationRepository,
        movement_repository: FixedAssetMovementRepository,
    ) -> None:
        self._fixed_asset_repository = fixed_asset_repository
        self._depreciation_repository = depreciation_repository
        self._movement_repository = movement_repository

    def report_for_company(
        self,
        *,
        company_id: UUID,
        start_date: date,
        end_date: date,
    ) -> FixedAssetReport:
        """Erzeugt den Anlagenbericht für ein Geschäftsjahr."""

        if not isinstance(start_date, date):
            raise TypeError(
                "start_date muss ein Datum sein."
            )

        if not isinstance(end_date, date):
            raise TypeError(
                "end_date muss ein Datum sein."
            )

        if end_date < start_date:
            raise ValueError(
                "Das Enddatum darf nicht vor dem "
                "Startdatum liegen."
            )

        fixed_assets = (
            self._fixed_asset_repository.list_for_company(
                company_id
            )
        )

        rows: list[FixedAssetReportRow] = []

        for fixed_asset in fixed_assets:
            if fixed_asset.acquisition_date > end_date:
                continue

            depreciations = (
                self._depreciation_repository
                .list_for_fixed_asset(
                    fixed_asset.fixed_asset_id
                )
            )

            opening_depreciation = sum(
                (
                    depreciation.amount
                    for depreciation in depreciations
                    if depreciation.depreciation_date
                    < start_date
                ),
                ZERO,
            )

            current_depreciation = sum(
                (
                    depreciation.amount
                    for depreciation in depreciations
                    if (
                        start_date
                        <= depreciation.depreciation_date
                        <= end_date
                    )
                ),
                ZERO,
            )

            accumulated_depreciation = sum(
                (
                    depreciation.amount
                    for depreciation in depreciations
                    if depreciation.depreciation_date
                    <= end_date
                ),
                ZERO,
            )

            movements = (
                self._movement_repository
                .list_for_fixed_asset(
                    fixed_asset.fixed_asset_id
                )
            )

            disposal_movements = tuple(
                movement
                for movement in movements
                if (
                    movement.movement_date <= end_date
                    and movement.movement_type
                    in {
                        FixedAssetMovementType.DISPOSAL,
                        FixedAssetMovementType.LOSS,
                    }
                )
            )

            disposed = bool(disposal_movements)

            closing_book_value = (
                ZERO
                if disposed
                else to_decimal(
                    fixed_asset.acquisition_cost
                    - accumulated_depreciation
                )
            )

            if closing_book_value < ZERO:
                raise ValueError(
                    "Die gebuchten Abschreibungen "
                    "übersteigen die Anschaffungskosten "
                    f"des Anlageguts "
                    f"{fixed_asset.asset_code}."
                )

            disposal_date = (
                disposal_movements[-1].movement_date
                if disposal_movements
                else None
            )

            rows.append(
                FixedAssetReportRow(
                    asset_code=fixed_asset.asset_code,
                    description=fixed_asset.description,
                    asset_account_number=(
                        fixed_asset.asset_account_number
                    ),
                    acquisition_date=(
                        fixed_asset.acquisition_date
                    ),
                    acquisition_cost=to_decimal(
                        fixed_asset.acquisition_cost
                    ),
                    opening_depreciation=to_decimal(
                        opening_depreciation
                    ),
                    current_depreciation=to_decimal(
                        current_depreciation
                    ),
                    accumulated_depreciation=to_decimal(
                        accumulated_depreciation
                    ),
                    closing_book_value=closing_book_value,
                    disposal_date=disposal_date,
                )
            )

        return FixedAssetReport(
            start_date=start_date,
            end_date=end_date,
            rows=tuple(rows),
        )

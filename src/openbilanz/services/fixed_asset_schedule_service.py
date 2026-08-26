"""Erstellung des aggregierten Anlagenspiegels."""

from collections import defaultdict
from datetime import date
from decimal import Decimal
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
from openbilanz.domain.fixed_asset_movement import (
    FixedAssetMovement,
)
from openbilanz.domain.fixed_asset_movement_type import (
    FixedAssetMovementType,
)
from openbilanz.domain.money import ZERO, to_decimal
from openbilanz.reporting.fixed_asset_schedule import (
    FixedAssetSchedule,
    FixedAssetScheduleRow,
)


class FixedAssetScheduleService:
    """Erzeugt den aggregierten Anlagenspiegel."""

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

    def schedule_for_company(
        self,
        *,
        company_id: UUID,
        start_date: date,
        end_date: date,
    ) -> FixedAssetSchedule:
        """Erzeugt den Anlagenspiegel für ein Geschäftsjahr."""

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

        values: dict[str, dict[str, Decimal]] = defaultdict(
            lambda: {
                "opening_cost": ZERO,
                "additions": ZERO,
                "disposals": ZERO,
                "current_depreciation": ZERO,
                "accumulated_depreciation": ZERO,
                "closing_book_value": ZERO,
            }
        )

        fixed_assets = (
            self._fixed_asset_repository.list_for_company(
                company_id
            )
        )

        for fixed_asset in fixed_assets:
            movements = (
                self._movement_repository.list_for_fixed_asset(
                    fixed_asset.fixed_asset_id
                )
            )

            effective_movements = self._effective_movements(
                movements
            )

            acquisition = next(
                (
                    movement
                    for movement in effective_movements
                    if (
                        movement.movement_type
                        is FixedAssetMovementType.ACQUISITION
                    )
                ),
                None,
            )

            if acquisition is None:
                continue

            if acquisition.movement_date > end_date:
                continue

            disposal = next(
                (
                    movement
                    for movement in effective_movements
                    if (
                        movement.movement_type
                        in {
                            FixedAssetMovementType.DISPOSAL,
                            FixedAssetMovementType.LOSS,
                        }
                        and movement.movement_date <= end_date
                    )
                ),
                None,
            )

            depreciations = (
                self._depreciation_repository
                .list_for_fixed_asset(
                    fixed_asset.fixed_asset_id
                )
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
                start=ZERO,
            )

            accumulated_depreciation = sum(
                (
                    depreciation.amount
                    for depreciation in depreciations
                    if depreciation.depreciation_date <= end_date
                ),
                start=ZERO,
            )

            acquisition_cost = to_decimal(
                fixed_asset.acquisition_cost
            )

            position_values = values[
                fixed_asset.position_code
            ]

            if acquisition.movement_date < start_date:
                position_values["opening_cost"] += (
                    acquisition_cost
                )
            else:
                position_values["additions"] += (
                    acquisition_cost
                )

            if (
                disposal is not None
                and start_date
                <= disposal.movement_date
                <= end_date
            ):
                position_values["disposals"] += (
                    acquisition_cost
                )

            position_values[
                "current_depreciation"
            ] += to_decimal(
                current_depreciation
            )

            position_values[
                "accumulated_depreciation"
            ] += to_decimal(
                accumulated_depreciation
            )

            if disposal is None:
                closing_book_value = to_decimal(
                    acquisition_cost
                    - accumulated_depreciation
                )
            else:
                closing_book_value = ZERO

            if closing_book_value < ZERO:
                raise ValueError(
                    "Die gebuchten Abschreibungen "
                    "übersteigen die Anschaffungskosten "
                    f"des Anlageguts "
                    f"{fixed_asset.asset_code}."
                )

            position_values[
                "closing_book_value"
            ] += closing_book_value

        rows = tuple(
            FixedAssetScheduleRow(
                position_code=position_code,
                opening_cost=to_decimal(
                    row_values["opening_cost"]
                ),
                additions=to_decimal(
                    row_values["additions"]
                ),
                disposals=to_decimal(
                    row_values["disposals"]
                ),
                current_depreciation=to_decimal(
                    row_values["current_depreciation"]
                ),
                accumulated_depreciation=to_decimal(
                    row_values[
                        "accumulated_depreciation"
                    ]
                ),
                closing_book_value=to_decimal(
                    row_values["closing_book_value"]
                ),
            )
            for position_code, row_values
            in sorted(values.items())
        )

        return FixedAssetSchedule(
            rows=rows
        )

    @staticmethod
    def _effective_movements(
        movements: tuple[
            FixedAssetMovement,
            ...,
        ],
    ) -> tuple[FixedAssetMovement, ...]:
        """Entfernt Stornos und stornierte Bewegungen."""

        reversed_movement_ids = {
            movement.reversed_movement_id
            for movement in movements
            if (
                movement.movement_type
                is FixedAssetMovementType.REVERSAL
                and movement.reversed_movement_id is not None
            )
        }

        return tuple(
            movement
            for movement in movements
            if (
                movement.movement_type
                is not FixedAssetMovementType.REVERSAL
                and movement.movement_id
                not in reversed_movement_ids
            )
        )

"""Fachliche Jahresauswertung für den Anlagenspiegel."""

from dataclasses import dataclass
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
from openbilanz.domain.fixed_asset_movement_type import (
    FixedAssetMovementType,
)

ZERO = Decimal("0.00")


@dataclass(frozen=True, slots=True)
class FixedAssetSchedulePosition:
    """Jahreswerte einer HGB-Anlagenposition."""

    position_code: str

    acquisition_cost_beginning: Decimal
    additions: Decimal
    disposals: Decimal
    acquisition_cost_ending: Decimal

    accumulated_depreciation_beginning: Decimal
    depreciation_current_year: Decimal
    depreciation_disposals: Decimal
    accumulated_depreciation_ending: Decimal

    carrying_amount_ending: Decimal


class FixedAssetScheduleService:
    """Erstellt den fachlichen Anlagenspiegel eines Geschäftsjahres."""

    def __init__(
        self,
        *,
        fixed_asset_repository: FixedAssetRepository,
        fixed_asset_movement_repository: FixedAssetMovementRepository,
        fixed_asset_depreciation_repository: (
            FixedAssetDepreciationRepository
        ),
    ) -> None:
        self._fixed_asset_repository = (
            fixed_asset_repository
        )
        self._fixed_asset_movement_repository = (
            fixed_asset_movement_repository
        )
        self._fixed_asset_depreciation_repository = (
            fixed_asset_depreciation_repository
        )

    def build(
        self,
        *,
        company_id: UUID,
        fiscal_year_start: date,
        fiscal_year_end: date,
    ) -> tuple[FixedAssetSchedulePosition, ...]:
        """Ermittelt die Werte des Anlagenspiegels."""

        if not isinstance(company_id, UUID):
            raise TypeError(
                "company_id must be a UUID"
            )

        if not isinstance(fiscal_year_start, date):
            raise TypeError(
                "fiscal_year_start must be a date"
            )

        if not isinstance(fiscal_year_end, date):
            raise TypeError(
                "fiscal_year_end must be a date"
            )

        if fiscal_year_end < fiscal_year_start:
            raise ValueError(
                "fiscal_year_end must not be before "
                "fiscal_year_start"
            )

        assets = (
            self._fixed_asset_repository.list_for_company(
                company_id
            )
        )

        positions: dict[
            str,
            FixedAssetSchedulePosition,
        ] = {}

        for fixed_asset in assets:
            if fixed_asset.acquisition_date > fiscal_year_end:
                continue

            movements = (
                self._fixed_asset_movement_repository
                .list_for_fixed_asset(
                    fixed_asset.fixed_asset_id
                )
            )

            depreciations = (
                self._fixed_asset_depreciation_repository
                .list_for_fixed_asset(
                    fixed_asset.fixed_asset_id
                )
            )

            acquisition_cost_beginning = ZERO

            if fixed_asset.acquisition_date < fiscal_year_start:
                acquisition_cost_beginning = (
                    fixed_asset.acquisition_cost
                )

            additions = ZERO

            if (
                fiscal_year_start
                <= fixed_asset.acquisition_date
                <= fiscal_year_end
            ):
                acquisition_confirmed = any(
                    movement.movement_type
                    is FixedAssetMovementType.ACQUISITION
                    and (
                        fiscal_year_start
                        <= movement.movement_date
                        <= fiscal_year_end
                    )
                    for movement in movements
                )

                if not acquisition_confirmed:
                    continue

                additions = fixed_asset.acquisition_cost

            accumulated_depreciation_beginning = sum(
                (
                    depreciation.amount
                    for depreciation in depreciations
                    if depreciation.depreciation_date
                    < fiscal_year_start
                ),
                ZERO,
            )

            depreciation_current_year = sum(
                (
                    depreciation.amount
                    for depreciation in depreciations
                    if (
                        fiscal_year_start
                        <= depreciation.depreciation_date
                        <= fiscal_year_end
                    )
                ),
                ZERO,
            )

            disposal_movement = next(
                (
                    movement
                    for movement in movements
                    if (
                        movement.movement_type
                        is FixedAssetMovementType.DISPOSAL
                        and (
                            fiscal_year_start
                            <= movement.movement_date
                            <= fiscal_year_end
                        )
                    )
                ),
                None,
            )

            disposals = ZERO
            depreciation_disposals = ZERO

            if disposal_movement is not None:
                disposals = fixed_asset.acquisition_cost

                depreciation_disposals = sum(
                    (
                        depreciation.amount
                        for depreciation in depreciations
                        if (
                            depreciation.depreciation_date
                            <= disposal_movement.movement_date
                        )
                    ),
                    ZERO,
                )

            acquisition_cost_ending = (
                acquisition_cost_beginning
                + additions
                - disposals
            )

            accumulated_depreciation_ending = (
                accumulated_depreciation_beginning
                + depreciation_current_year
                - depreciation_disposals
            )

            carrying_amount_ending = (
                acquisition_cost_ending
                - accumulated_depreciation_ending
            )

            current = positions.get(
                fixed_asset.position_code
            )

            if current is None:
                positions[fixed_asset.position_code] = (
                    FixedAssetSchedulePosition(
                        position_code=(
                            fixed_asset.position_code
                        ),
                        acquisition_cost_beginning=(
                            acquisition_cost_beginning
                        ),
                        additions=additions,
                        disposals=disposals,
                        acquisition_cost_ending=(
                            acquisition_cost_ending
                        ),
                        accumulated_depreciation_beginning=(
                            accumulated_depreciation_beginning
                        ),
                        depreciation_current_year=(
                            depreciation_current_year
                        ),
                        depreciation_disposals=(
                            depreciation_disposals
                        ),
                        accumulated_depreciation_ending=(
                            accumulated_depreciation_ending
                        ),
                        carrying_amount_ending=(
                            carrying_amount_ending
                        ),
                    )
                )
                continue

            positions[fixed_asset.position_code] = (
                FixedAssetSchedulePosition(
                    position_code=current.position_code,
                    acquisition_cost_beginning=(
                        current.acquisition_cost_beginning
                        + acquisition_cost_beginning
                    ),
                    additions=(
                        current.additions
                        + additions
                    ),
                    disposals=(
                        current.disposals
                        + disposals
                    ),
                    acquisition_cost_ending=(
                        current.acquisition_cost_ending
                        + acquisition_cost_ending
                    ),
                    accumulated_depreciation_beginning=(
                        current.accumulated_depreciation_beginning
                        + accumulated_depreciation_beginning
                    ),
                    depreciation_current_year=(
                        current.depreciation_current_year
                        + depreciation_current_year
                    ),
                    depreciation_disposals=(
                        current.depreciation_disposals
                        + depreciation_disposals
                    ),
                    accumulated_depreciation_ending=(
                        current.accumulated_depreciation_ending
                        + accumulated_depreciation_ending
                    ),
                    carrying_amount_ending=(
                        current.carrying_amount_ending
                        + carrying_amount_ending
                    ),
                )
            )

        return tuple(
            positions[position_code]
            for position_code in sorted(positions)
        )

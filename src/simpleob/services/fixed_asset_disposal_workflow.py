"""Workflow für die Bestätigung eines Anlagenverkaufs."""

from dataclasses import replace
from uuid import UUID

from sqlalchemy.orm import Session

from simpleob.database.booking_repository import (
    BookingRepository,
)
from simpleob.database.fixed_asset_movement_repository import (
    FixedAssetMovementRepository,
)
from simpleob.database.fixed_asset_repository import (
    FixedAssetRepository,
)
from simpleob.domain.entry_side import EntrySide
from simpleob.domain.fiscal_year import FiscalYear
from simpleob.domain.fixed_asset import FixedAsset
from simpleob.domain.fixed_asset_disposal_calculation import (
    FixedAssetDisposalCalculation,
)
from simpleob.domain.fixed_asset_movement import (
    FixedAssetMovement,
)
from simpleob.domain.fixed_asset_movement_type import (
    FixedAssetMovementType,
)
from simpleob.domain.fixed_asset_status import (
    FixedAssetStatus,
)


class FixedAssetDisposalWorkflow:
    """Persistiert einen bestätigten Anlagenverkauf atomar."""

    def __init__(
        self,
        *,
        session: Session,
        booking_repository: BookingRepository,
        movement_repository: FixedAssetMovementRepository,
        fixed_asset_repository: FixedAssetRepository,
    ) -> None:
        self._session = session
        self._booking_repository = booking_repository
        self._movement_repository = movement_repository
        self._fixed_asset_repository = fixed_asset_repository

    def confirm(
        self,
        *,
        company_id: UUID,
        fiscal_year: FiscalYear,
        fixed_asset: FixedAsset,
        calculation: FixedAssetDisposalCalculation,
    ) -> FixedAssetMovement:
        """Bestätigt und persistiert einen Anlagenverkauf."""

        if fixed_asset.company_id != company_id:
            raise ValueError(
                "Das Anlagegut gehört nicht zum Unternehmen."
            )

        if fixed_asset.status is not FixedAssetStatus.ACTIVE:
            raise ValueError(
                "Das Anlagegut ist nicht aktiv."
            )

        booking = calculation.booking

        if not fiscal_year.contains(booking.booking_date):
            raise ValueError(
                "Das Abgangsdatum liegt außerhalb "
                "des Geschäftsjahres."
            )

        if booking.booking_date < fixed_asset.acquisition_date:
            raise ValueError(
                "Das Abgangsdatum liegt vor dem "
                "Anschaffungsdatum."
            )

        asset_line_positions = tuple(
            position
            for position, line in enumerate(booking.lines)
            if (
                line.account_number
                == fixed_asset.asset_account_number
                and line.side is EntrySide.CREDIT
                and line.amount
                == calculation.carrying_amount
            )
        )

        if len(asset_line_positions) != 1:
            raise ValueError(
                "Die Verkaufsbuchung enthält keine "
                "eindeutige Haben-Buchungszeile für "
                "den Restbuchwert des Anlagekontos."
            )

        asset_line_position = asset_line_positions[0]

        movement = FixedAssetMovement(
            fixed_asset_id=fixed_asset.fixed_asset_id,
            fiscal_year_end=fiscal_year.end_date,
            movement_date=booking.booking_date,
            amount=fixed_asset.acquisition_cost,
            booking_id=booking.booking_id,
            movement_type=FixedAssetMovementType.DISPOSAL,
        )

        disposed_fixed_asset = replace(
            fixed_asset,
            status=FixedAssetStatus.DISPOSED,
            disposal_date=booking.booking_date,
        )

        try:
            self._booking_repository.add(
                company_id=company_id,
                fiscal_year=fiscal_year,
                booking=booking,
                commit=False,
            )

            self._movement_repository.add(
                movement=movement,
                booking_line_position=asset_line_position,
                commit=False,
            )

            self._fixed_asset_repository.update(
                fixed_asset=disposed_fixed_asset,
                commit=False,
            )

            self._session.commit()

        except Exception:
            self._session.rollback()
            raise

        return movement

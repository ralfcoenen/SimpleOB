
"""Workflow für die Bestätigung einer Anlagenabschreibung."""

from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from simpleob.database.booking_repository import BookingRepository
from simpleob.database.company_repository import CompanyRepository
from simpleob.database.fixed_asset_depreciation_repository import (
    FixedAssetDepreciationRepository,
)
from simpleob.database.fixed_asset_movement_repository import (
    FixedAssetMovementRepository,
)
from simpleob.database.fixed_asset_repository import FixedAssetRepository
from simpleob.domain.booking_type import BookingType
from simpleob.domain.depreciation_kind import DepreciationKind
from simpleob.domain.depreciation_proposal import DepreciationProposal
from simpleob.domain.depreciation_source import DepreciationSource
from simpleob.domain.fiscal_year import FiscalYear
from simpleob.domain.fixed_asset_depreciation import (
    FixedAssetDepreciation,
)
from simpleob.domain.fixed_asset_movement_type import (
    FixedAssetMovementType,
)
from simpleob.services.depreciation_booking_service import (
    DepreciationBookingService,
)
from simpleob.services.depreciation_service import DepreciationService


class FixedAssetDepreciationWorkflow:
    """Prüft und persistiert eine bestätigte lineare Abschreibung atomar."""

    def __init__(
        self,
        *,
        session: Session,
        booking_repository: BookingRepository,
        depreciation_repository: FixedAssetDepreciationRepository,
        booking_service: DepreciationBookingService,
        company_repository: CompanyRepository,
        fixed_asset_repository: FixedAssetRepository,
        movement_repository: FixedAssetMovementRepository,
        depreciation_service: DepreciationService,
    ) -> None:
        self._session = session
        self._booking_repository = booking_repository
        self._depreciation_repository = depreciation_repository
        self._booking_service = booking_service
        self._company_repository = company_repository
        self._fixed_asset_repository = fixed_asset_repository
        self._movement_repository = movement_repository
        self._depreciation_service = depreciation_service

    def confirm(
        self,
        *,
        company_id: UUID,
        fiscal_year: FiscalYear,
        proposal: DepreciationProposal,
        asset_code: str,
        asset_description: str,
    ) -> FixedAssetDepreciation:
        """Bestätigt einen nach erneuter Prüfung gültigen AfA-Vorschlag."""

        try:
            self._company_repository.lock_open_fiscal_year(
                company_id,
                fiscal_year,
            )

            fixed_asset = self._fixed_asset_repository.get(
                proposal.fixed_asset_id
            )

            if fixed_asset is None:
                raise ValueError("Das Anlagegut ist nicht vorhanden.")

            if fixed_asset.company_id != company_id:
                raise ValueError(
                    "Das Anlagegut gehört nicht zum ausgewählten Mandanten."
                )

            movements = self._movement_repository.list_for_fixed_asset(
                fixed_asset.fixed_asset_id
            )

            reversed_movement_ids = {
                movement.reversed_movement_id
                for movement in movements
                if (
                    movement.movement_type
                    is FixedAssetMovementType.REVERSAL
                    and movement.reversed_movement_id is not None
                )
            }

            effective_movements = tuple(
                movement
                for movement in movements
                if (
                    movement.movement_type
                    is not FixedAssetMovementType.REVERSAL
                    and movement.movement_id not in reversed_movement_ids
                )
            )

            if not any(
                movement.movement_type
                is FixedAssetMovementType.ACQUISITION
                for movement in effective_movements
            ):
                raise ValueError(
                    "Der Abschreibungsvorschlag ist nicht mehr gültig: "
                    "Es fehlt eine wirksame Anschaffungsbewegung."
                )

            disposal_movement = next(
                (
                    movement
                    for movement in effective_movements
                    if movement.movement_type
                    is FixedAssetMovementType.DISPOSAL
                ),
                None,
            )

            depreciations = (
                self._depreciation_repository.list_for_fixed_asset(
                    fixed_asset.fixed_asset_id
                )
            )

            bookings = self._booking_repository.list_for_fiscal_year(
                company_id=company_id,
                fiscal_year=fiscal_year,
            )

            reversed_booking_ids = {
                booking.reversal_of_booking_id
                for booking in bookings
                if (
                    booking.booking_type is BookingType.REVERSAL
                    and booking.reversal_of_booking_id is not None
                )
            }

            effective_depreciations = tuple(
                depreciation
                for depreciation in depreciations
                if depreciation.booking_id not in reversed_booking_ids
            )

            if any(
                depreciation.fiscal_year_end == fiscal_year.end_date
                for depreciation in effective_depreciations
            ):
                raise ValueError(
                    "Für dieses Anlagegut wurde im Geschäftsjahr "
                    "bereits eine Abschreibung bestätigt."
                )

            previous_depreciation = sum(
                (
                    depreciation.amount
                    for depreciation in effective_depreciations
                ),
                start=Decimal("0.00"),
            )

            current_proposal = self._depreciation_service.build_proposal(
                fixed_asset=fixed_asset,
                fiscal_year=fiscal_year,
                previous_depreciation=previous_depreciation,
                expense_account_number=(
                    fixed_asset.depreciation_expense_account_number
                ),
                asset_account_number=fixed_asset.asset_account_number,
                depreciation_end_date=(
                    disposal_movement.movement_date
                    if disposal_movement is not None
                    else None
                ),
            )

            if current_proposal != proposal:
                raise ValueError(
                    "Der Abschreibungsvorschlag ist nicht mehr aktuell. "
                    "Bitte berechnen Sie die Abschreibung erneut."
                )

            booking = self._booking_service.build_booking(
                proposal=current_proposal,
                asset_code=fixed_asset.asset_code,
                asset_description=fixed_asset.description,
            )

            depreciation = FixedAssetDepreciation(
                fixed_asset_id=current_proposal.fixed_asset_id,
                fiscal_year_end=fiscal_year.end_date,
                depreciation_date=current_proposal.depreciation_date,
                amount=current_proposal.amount,
                booking_id=booking.booking_id,
                kind=DepreciationKind.LINEAR,
                source=DepreciationSource.CALCULATED,
            )

            self._booking_repository.add(
                company_id=company_id,
                fiscal_year=fiscal_year,
                booking=booking,
                commit=False,
            )

            self._depreciation_repository.add(
                depreciation=depreciation,
                booking_line_position=1,
                commit=False,
            )

            self._session.commit()

        except Exception:
            self._session.rollback()
            raise

        return depreciation

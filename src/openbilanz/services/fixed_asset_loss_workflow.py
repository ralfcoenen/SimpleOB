"""Workflow für den Totalverlust eines Anlageguts."""
from dataclasses import replace
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from openbilanz.database.booking_repository import (
    BookingRepository,
)
from openbilanz.database.fixed_asset_depreciation_repository import (
    FixedAssetDepreciationRepository,
)
from openbilanz.database.fixed_asset_movement_repository import (
    FixedAssetMovementRepository,
)
from openbilanz.database.fixed_asset_repository import (
    FixedAssetRepository,
)
from openbilanz.domain.depreciation_proposal import (
    DepreciationProposal,
)
from openbilanz.domain.fiscal_year import FiscalYear
from openbilanz.domain.fixed_asset_movement import (
    FixedAssetMovement,
)
from openbilanz.domain.fixed_asset_movement_type import (
    FixedAssetMovementType,
)
from openbilanz.domain.fixed_asset_status import (
    FixedAssetStatus,
)
from openbilanz.services.depreciation_service import (
    DepreciationService,
)
from openbilanz.services.fixed_asset_book_value_service import (
    FixedAssetBookValueService,
)
from openbilanz.services.fixed_asset_loss_booking_service import (
    FixedAssetLossBookingService,
)


class FixedAssetLossWorkflow:
    """Prüft und verbucht den Totalverlust eines Anlageguts."""

    def __init__(
        self,
        *,
        session: Session,
        fixed_asset_repository: FixedAssetRepository,
        depreciation_repository: (
            FixedAssetDepreciationRepository
        ),
        movement_repository: FixedAssetMovementRepository,
        booking_repository: BookingRepository,
        depreciation_service: DepreciationService,
        book_value_service: FixedAssetBookValueService,
        booking_service: FixedAssetLossBookingService,
    ) -> None:
        self._session = session
        self._fixed_asset_repository = (
            fixed_asset_repository
        )
        self._depreciation_repository = (
            depreciation_repository
        )
        self._movement_repository = (
            movement_repository
        )
        self._booking_repository = (
            booking_repository
        )
        self._depreciation_service = (
            depreciation_service
        )
        self._book_value_service = (
            book_value_service
        )
        self._booking_service = (
            booking_service
        )

    def pending_depreciation(
        self,
        *,
        fixed_asset_id: UUID,
        fiscal_year: FiscalYear,
        loss_date: date,
    ) -> DepreciationProposal | None:
        """Ermittelt eine vor dem Totalverlust noch offene AfA."""

        fixed_asset = (
            self._fixed_asset_repository.get(
                fixed_asset_id
            )
        )

        if fixed_asset is None:
            raise ValueError(
                "Das Anlagegut ist nicht vorhanden."
            )

        depreciations = (
            self._depreciation_repository
            .list_for_fixed_asset(
                fixed_asset.fixed_asset_id
            )
        )

        previous_depreciation = sum(
            (
                depreciation.amount
                for depreciation in depreciations
                if depreciation.depreciation_date
                <= loss_date
            ),
            start=Decimal("0.00"),
        )

        current_fiscal_year_depreciation = sum(
            (
                depreciation.amount
                for depreciation in depreciations
                if (
                    fiscal_year.start_date
                    <= depreciation.depreciation_date
                    <= loss_date
                )
            ),
            start=Decimal("0.00"),
        )

        return self._depreciation_service.build_proposal_until(
            fixed_asset=fixed_asset,
            fiscal_year=fiscal_year,
            previous_depreciation=previous_depreciation,
            expense_account_number=(
                fixed_asset
                .depreciation_expense_account_number
            ),
            asset_account_number=(
                fixed_asset.asset_account_number
            ),
            depreciation_date=loss_date,
            current_fiscal_year_depreciation=(
                current_fiscal_year_depreciation
            ),
        )

    def confirm_loss(
        self,
        *,
        company_id: UUID,
        fiscal_year: FiscalYear,
        fixed_asset_id: UUID,
        loss_date: date,
        loss_expense_account_number: str,
    ) -> FixedAssetMovement:
        """Bucht einen Totalverlust nach erledigter AfA."""

        fixed_asset = (
            self._fixed_asset_repository.get(
                fixed_asset_id
            )
        )

        if fixed_asset is None:
            raise ValueError(
                "Das Anlagegut ist nicht vorhanden."
            )

        if fixed_asset.company_id != company_id:
            raise ValueError(
                "Das Anlagegut gehört nicht zum Unternehmen."
            )

        if fixed_asset.status is not FixedAssetStatus.ACTIVE:
            raise ValueError(
                "Das Anlagegut ist nicht mehr aktiv."
            )

        if not fiscal_year.contains(loss_date):
            raise ValueError(
                "Das Verlustdatum liegt außerhalb "
                "des Geschäftsjahres."
            )

        if loss_date < fixed_asset.acquisition_date:
            raise ValueError(
                "Das Verlustdatum liegt vor der Anschaffung."
            )

        pending_depreciation = self.pending_depreciation(
            fixed_asset_id=fixed_asset_id,
            fiscal_year=fiscal_year,
            loss_date=loss_date,
        )

        if pending_depreciation is not None:
            raise ValueError(
                "Vor dem Anlagenabgang muss die "
                "Abschreibung bis zum Abgangsdatum "
                "bestätigt und gebucht werden."
            )

        book_value = (
            self._book_value_service.book_value_at(
                fixed_asset=fixed_asset,
                reference_date=loss_date,
            )
        )

        if book_value <= 0:
            raise ValueError(
                "Das Anlagegut hat keinen auszubuchenden "
                "Restbuchwert."
            )

        booking = self._booking_service.build_booking(
            loss_date=loss_date,
            book_value=book_value,
            asset_account_number=(
                fixed_asset.asset_account_number
            ),
            loss_expense_account_number=(
                loss_expense_account_number
            ),
        )

        movement = FixedAssetMovement(
            fixed_asset_id=fixed_asset.fixed_asset_id,
            fiscal_year_end=fiscal_year.end_date,
            movement_date=loss_date,
            amount=book_value,
            booking_id=booking.booking_id,
            movement_type=FixedAssetMovementType.LOSS,
        )

        disposed_asset = replace(
            fixed_asset,
            status=FixedAssetStatus.DISPOSED,
            disposal_date=loss_date,
        )

        try:
            self._booking_repository.add(
                company_id=company_id,
                fiscal_year=fiscal_year,
                booking=booking,
                commit=False,
            )

            # Anlagenkonto ist die Habenzeile Position 1.
            self._movement_repository.add(
                movement=movement,
                booking_line_position=1,
                commit=False,
            )

            self._fixed_asset_repository.update(
                fixed_asset=disposed_asset,
                commit=False,
            )

            self._session.commit()

        except Exception:
            self._session.rollback()
            raise

        return movement

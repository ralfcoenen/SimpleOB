"""Workflow für die Bestätigung einer Anlagenabschreibung."""

from uuid import UUID

from sqlalchemy.orm import Session

from openbilanz.database.booking_repository import (
    BookingRepository,
)
from openbilanz.database.fixed_asset_depreciation_repository import (
    FixedAssetDepreciationRepository,
)
from openbilanz.domain.depreciation_kind import (
    DepreciationKind,
)
from openbilanz.domain.depreciation_proposal import (
    DepreciationProposal,
)
from openbilanz.domain.depreciation_source import (
    DepreciationSource,
)
from openbilanz.domain.fiscal_year import FiscalYear
from openbilanz.domain.fixed_asset_depreciation import (
    FixedAssetDepreciation,
)
from openbilanz.services.depreciation_booking_service import (
    DepreciationBookingService,
)


class FixedAssetDepreciationWorkflow:
    """Persistiert eine bestätigte lineare Abschreibung atomar."""

    def __init__(
        self,
        *,
        session: Session,
        booking_repository: BookingRepository,
        depreciation_repository: FixedAssetDepreciationRepository,
        booking_service: DepreciationBookingService,
    ) -> None:
        self._session = session
        self._booking_repository = booking_repository
        self._depreciation_repository = depreciation_repository
        self._booking_service = booking_service

    def confirm(
        self,
        *,
        company_id: UUID,
        fiscal_year: FiscalYear,
        proposal: DepreciationProposal,
    ) -> FixedAssetDepreciation:
        """Bestätigt und persistiert einen linearen AfA-Vorschlag."""

        booking = self._booking_service.build_booking(
            proposal=proposal,
        )

        depreciation = FixedAssetDepreciation(
            fixed_asset_id=proposal.fixed_asset_id,
            fiscal_year_end=fiscal_year.end_date,
            depreciation_date=proposal.depreciation_date,
            amount=proposal.amount,
            booking_id=booking.booking_id,
            kind=DepreciationKind.LINEAR,
            source=DepreciationSource.CALCULATED,
        )

        try:
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

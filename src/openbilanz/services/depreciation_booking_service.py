"""Erzeugung von Abschreibungsbuchungen."""

from openbilanz.domain.booking import Booking
from openbilanz.domain.booking_line import BookingLine
from openbilanz.domain.booking_type import BookingType
from openbilanz.domain.depreciation_proposal import (
    DepreciationProposal,
)
from openbilanz.domain.entry_side import EntrySide


class DepreciationBookingService:
    """Erzeugt Buchungen aus bestätigten AfA-Vorschlägen."""

    def build_booking(
        self,
        *,
        proposal: DepreciationProposal,
    ) -> Booking:
        """Erzeugt die Hauptbuchbuchung für eine lineare AfA."""

        if not isinstance(
            proposal,
            DepreciationProposal,
        ):
            raise TypeError(
                "proposal must be a DepreciationProposal"
            )

        return Booking(
            booking_date=proposal.depreciation_date,
            description="Lineare Abschreibung",
            booking_type=BookingType.REGULAR,
            lines=(
                BookingLine(
                    account_number=(
                        proposal.expense_account_number
                    ),
                    side=EntrySide.DEBIT,
                    amount=proposal.amount,
                ),
                BookingLine(
                    account_number=(
                        proposal.asset_account_number
                    ),
                    side=EntrySide.CREDIT,
                    amount=proposal.amount,
                ),
            ),
        )
    
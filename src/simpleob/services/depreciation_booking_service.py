"""Erzeugung von Abschreibungsbuchungen."""

from simpleob.domain.booking import Booking
from simpleob.domain.booking_line import BookingLine
from simpleob.domain.booking_type import BookingType
from simpleob.domain.depreciation_proposal import (
    DepreciationProposal,
)
from simpleob.domain.entry_side import EntrySide


class DepreciationBookingService:
    """Erzeugt Buchungen aus bestätigten AfA-Vorschlägen."""

    def build_booking(
        self,
        *,
        proposal: DepreciationProposal,
        asset_code: str,
        asset_description: str,
    ) -> Booking:
        """Erzeugt die Hauptbuchbuchung für eine lineare AfA."""

        if not isinstance(
            proposal,
            DepreciationProposal,
        ):
            raise TypeError(
                "proposal must be a DepreciationProposal"
            )

        if not isinstance(asset_code, str):
            raise TypeError(
                "asset_code must be a string"
            )

        if not asset_code.strip():
            raise ValueError(
                "asset_code must not be empty"
            )

        if not isinstance(asset_description, str):
            raise TypeError(
                "asset_description must be a string"
            )

        if not asset_description.strip():
            raise ValueError(
                "asset_description must not be empty"
            )

        asset_code = asset_code.strip()
        asset_description = asset_description.strip()

        return Booking(
            booking_date=proposal.depreciation_date,
            description=(
                "Lineare Abschreibung – "
                f"{asset_code} – "
                f"{asset_description}"
            ),
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

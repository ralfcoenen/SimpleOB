"""Erzeugung von Buchungen zur Umsetzung einer Ergebnisverwendung."""

from openbilanz.domain.booking import Booking
from openbilanz.domain.booking_line import BookingLine
from openbilanz.domain.booking_type import BookingType
from openbilanz.domain.entry_side import EntrySide
from openbilanz.domain.profit_appropriation_posting_proposal import (
    ProfitAppropriationPostingProposal,
)
from openbilanz.domain.profit_appropriation_posting_type import (
    ProfitAppropriationPostingType,
)


class ProfitAppropriationBookingService:
    """Erzeugt Buchungen aus bestätigten Ergebnisverwendungsvorschlägen."""

    def build_booking(
        self,
        *,
        proposal: ProfitAppropriationPostingProposal,
    ) -> Booking:
        """Erzeugt die Hauptbuchbuchung für einen Vorschlag."""

        if not isinstance(
            proposal,
            ProfitAppropriationPostingProposal,
        ):
            raise TypeError(
                "proposal must be a "
                "ProfitAppropriationPostingProposal"
            )

        return Booking(
            booking_date=proposal.booking_date,
            description=self._description(
                proposal.posting_type
            ),
            booking_type=BookingType.REGULAR,
            lines=(
                BookingLine(
                    account_number=(
                        proposal.debit_account_number
                    ),
                    side=EntrySide.DEBIT,
                    amount=proposal.amount,
                ),
                BookingLine(
                    account_number=(
                        proposal.credit_account_number
                    ),
                    side=EntrySide.CREDIT,
                    amount=proposal.amount,
                ),
            ),
        )

    @staticmethod
    def _description(
        posting_type: ProfitAppropriationPostingType,
    ) -> str:
        descriptions = {
            ProfitAppropriationPostingType.STATUTORY_RESERVE_ADDITION: (
                "Ergebnisverwendung – Zuführung gesetzliche Rücklage"
            ),
            ProfitAppropriationPostingType.OTHER_REVENUE_RESERVES_ADDITION: (
                "Ergebnisverwendung – Zuführung andere Gewinnrücklagen"
            ),
            ProfitAppropriationPostingType.STATUTORY_RESERVE_RELEASE: (
                "Ergebnisverwendung – Auflösung gesetzliche Rücklage"
            ),
            ProfitAppropriationPostingType.OTHER_REVENUE_RESERVES_RELEASE: (
                "Ergebnisverwendung – Auflösung andere Gewinnrücklagen"
            ),
            ProfitAppropriationPostingType.DISTRIBUTION: (
                "Ergebnisverwendung – Ausschüttung"
            ),
        }

        return descriptions[posting_type]

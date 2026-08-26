"""Erzeugung von Buchungen für den Totalverlust eines Anlageguts."""

from datetime import date
from decimal import Decimal

from openbilanz.domain.booking import Booking
from openbilanz.domain.booking_line import BookingLine
from openbilanz.domain.booking_type import BookingType
from openbilanz.domain.entry_side import EntrySide
from openbilanz.domain.money import to_decimal


class FixedAssetLossBookingService:
    """Erzeugt die Ausbuchung eines verlorenen Anlageguts."""

    def build_booking(
        self,
        *,
        loss_date: date,
        book_value: Decimal,
        asset_account_number: str,
        loss_expense_account_number: str,
    ) -> Booking:
        """Erzeugt die Buchung des Restbuchwerts als Verlust."""

        if not isinstance(loss_date, date):
            raise TypeError(
                "loss_date must be a date"
            )

        book_value = to_decimal(
            book_value
        )

        if book_value <= Decimal("0.00"):
            raise ValueError(
                "book_value must be greater than 0.00"
            )

        return Booking(
            booking_date=loss_date,
            description="Abgang Anlagegut durch Totalverlust",
            booking_type=BookingType.REGULAR,
            lines=(
                BookingLine(
                    account_number=(
                        loss_expense_account_number
                    ),
                    side=EntrySide.DEBIT,
                    amount=book_value,
                ),
                BookingLine(
                    account_number=(
                        asset_account_number
                    ),
                    side=EntrySide.CREDIT,
                    amount=book_value,
                ),
            ),
        )

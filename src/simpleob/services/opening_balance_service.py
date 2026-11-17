"""Service für Eröffnungsbuchungen."""

from datetime import date

from simpleob.domain.booking import Booking
from simpleob.domain.booking_line import BookingLine
from simpleob.domain.booking_type import BookingType
from simpleob.domain.entry_side import EntrySide
from simpleob.domain.money import ZERO
from simpleob.domain.opening_balance import OpeningBalance


class OpeningBalanceService:
    """Erzeugt Eröffnungsbuchungen aus einer Eröffnungsbilanz."""

    def __init__(
        self,
        *,
        opening_balance_account_number: str,
    ) -> None:
        self._opening_balance_account_number = (
            opening_balance_account_number
        )

    def create_bookings(
        self,
        *,
        opening_balance: OpeningBalance,
        booking_date: date,
    ) -> tuple[Booking, ...]:
        """Erzeugt Eröffnungsbuchungen."""

        if not opening_balance.is_balanced:
            raise ValueError(
                "Die Eröffnungsbilanz muss ausgeglichen sein."
            )

        bookings: list[Booking] = []

        for item in opening_balance.items:
            if item.account.number == self._opening_balance_account_number:
                raise ValueError(
                    "Das Eröffnungsbilanzkonto darf nicht als "
                    "Anfangssaldo erfasst werden."
                )

            if item.amount == ZERO:
                continue

            if item.side is EntrySide.DEBIT:
                debit_account = item.account.number
                credit_account = self._opening_balance_account_number

            else:
                debit_account = self._opening_balance_account_number
                credit_account = item.account.number

            bookings.append(
                Booking(
                    booking_date=booking_date,
                    description="Eröffnungsbuchung",
                    booking_type=BookingType.OPENING,
                    lines=(
                        BookingLine(
                            account_number=debit_account,
                            side=EntrySide.DEBIT,
                            amount=item.amount,
                        ),
                        BookingLine(
                            account_number=credit_account,
                            side=EntrySide.CREDIT,
                            amount=item.amount,
                        ),
                    ),
                )
            )
        return tuple(bookings)

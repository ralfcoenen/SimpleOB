"""Service für Eröffnungsbuchungen."""

from datetime import date

from openbilanz.domain.account_type import AccountType
from openbilanz.domain.booking import Booking
from openbilanz.domain.booking_line import BookingLine
from openbilanz.domain.entry_side import EntrySide
from openbilanz.domain.opening_balance import OpeningBalance
from openbilanz.domain.booking_type import BookingType


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
            if item.account.account_type is AccountType.ASSET:
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

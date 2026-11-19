from simpleob.domain.booking import Booking
from simpleob.domain.booking_type import BookingType
from simpleob.domain.chart_of_accounts import ChartOfAccounts
from simpleob.domain.errors import UnknownAccountError


class BookingValidator:
    """Validiert Buchungen gegen einen Kontenplan."""

    def __init__(self, chart_of_accounts: ChartOfAccounts) -> None:
        self._chart_of_accounts = chart_of_accounts

    def validate(self, booking: Booking) -> None:
        """
        Prüft, ob alle in der Buchung verwendeten Konten
        im Kontenplan vorhanden sind.
        """
        for line in booking.lines:
            try:
                account = self._chart_of_accounts.account(line.account_number)
            except KeyError as error:
                raise UnknownAccountError(
                    f"unknown account: {line.account_number}"
                ) from error

            if (
                booking.booking_type is BookingType.REGULAR
                and account.person_account_role is not None
                and not account.is_active
            ):
                raise ValueError(
                    "Neue reguläre Buchungen auf inaktive Personenkonten "
                    f"sind nicht zulässig: {account.number}."
                )
                

from openbilanz.domain.booking import Booking
from openbilanz.domain.chart_of_accounts import ChartOfAccounts
from openbilanz.domain.errors import UnknownAccountError


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
                self._chart_of_accounts.account(line.account_no)
            except KeyError as error:
                raise UnknownAccountError(
                    f"unknown account: {line.account_no}"
                ) from error
                

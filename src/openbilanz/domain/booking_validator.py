from openbilanz.domain.booking import Booking
from openbilanz.domain.chart_of_accounts import ChartOfAccounts


class BookingValidator:
    """Validiert Buchungen gegen einen Kontenplan."""

    def __init__(self, chart_of_accounts: ChartOfAccounts) -> None:
        self._chart_of_accounts = chart_of_accounts

    def validate(self, booking: Booking) -> None:
        """Akzeptiert zunächst jede Buchung."""
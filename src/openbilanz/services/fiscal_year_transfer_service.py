"""Service für die Überleitung in ein neues Geschäftsjahr."""

from datetime import date
from decimal import Decimal

from openbilanz.accounting.ledger import Ledger
from openbilanz.domain.account_type import AccountType
from openbilanz.domain.booking import Booking
from openbilanz.domain.booking_line import BookingLine
from openbilanz.domain.entry_side import EntrySide


class FiscalYearTransferService:
    """Erzeugt Eröffnungsbuchungen aus den Endsalden der Bestandskonten."""

    def __init__(
        self,
        *,
        opening_balance_account_number: str,
    ) -> None:
        self._opening_balance_account_number = (
            opening_balance_account_number
        )

    def create_opening_bookings(
        self,
        *,
        ledger: Ledger,
        account_types: dict[str, AccountType],
        opening_date: date,
    ) -> tuple[Booking, ...]:
        """Erzeugt Saldovorträge für Bestandskonten."""

        bookings: list[Booking] = []

        balance_sheet_account_types = {
            AccountType.ASSET,
            AccountType.LIABILITY,
            AccountType.EQUITY,
        }

        for balance in ledger.balances():
            account_number = balance.account_number

            if (
                account_number
                == self._opening_balance_account_number
            ):
                continue

            account_type = account_types.get(
                account_number
            )

            if (
                account_type
                not in balance_sheet_account_types
            ):
                continue

            booking = self._create_opening_booking(
                account_number=account_number,
                debit_balance=balance.debit_balance,
                credit_balance=balance.credit_balance,
                opening_date=opening_date,
            )

            if booking is not None:
                bookings.append(
                    booking
                )

        return tuple(bookings)

    def _create_opening_booking(
        self,
        *,
        account_number: str,
        debit_balance: Decimal,
        credit_balance: Decimal,
        opening_date: date,
    ) -> Booking | None:
        """Erzeugt den Saldovortrag eines einzelnen Kontos."""

        if debit_balance > Decimal("0.00"):
            return Booking(
                booking_date=opening_date,
                voucher_no=None,
                description=(
                    f"Saldovortrag Konto {account_number}"
                ),
                lines=(
                    BookingLine(
                        account_number=account_number,
                        side=EntrySide.DEBIT,
                        amount=debit_balance,
                    ),
                    BookingLine(
                        account_number=(
                            self._opening_balance_account_number
                        ),
                        side=EntrySide.CREDIT,
                        amount=debit_balance,
                    ),
                ),
            )

        if credit_balance > Decimal("0.00"):
            return Booking(
                booking_date=opening_date,
                voucher_no=None,
                description=(
                    f"Saldovortrag Konto {account_number}"
                ),
                lines=(
                    BookingLine(
                        account_number=(
                            self._opening_balance_account_number
                        ),
                        side=EntrySide.DEBIT,
                        amount=credit_balance,
                    ),
                    BookingLine(
                        account_number=account_number,
                        side=EntrySide.CREDIT,
                        amount=credit_balance,
                    ),
                ),
            )

        return None

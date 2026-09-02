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
        profit_account_number: str,
        loss_account_number: str,
        profit_loss_carryforward_account_number: str,
    ) -> None:
        self._opening_balance_account_number = (
            opening_balance_account_number
        )
        self._profit_account_number = (
            profit_account_number
        )
        self._loss_account_number = (
            loss_account_number
        )
        self._profit_loss_carryforward_account_number = (
            profit_loss_carryforward_account_number
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
            source_account_number = balance.account_number

            if (
                source_account_number
                == self._opening_balance_account_number
            ):
                continue

            account_type = account_types.get(
                source_account_number
            )

            if (
                account_type
                not in balance_sheet_account_types
            ):
                continue

            target_account_number = (
                self._opening_account_number(
                    source_account_number
                )
            )

            booking = self._create_opening_booking(
                source_account_number=source_account_number,
                target_account_number=target_account_number,
                debit_balance=balance.debit_balance,
                credit_balance=balance.credit_balance,
                opening_date=opening_date,
            )

            if booking is not None:
                bookings.append(
                    booking
                )

        return tuple(bookings)

    def _opening_account_number(
        self,
        source_account_number: str,
    ) -> str:
        """Bestimmt das Konto des Saldovortrags im neuen Geschäftsjahr."""

        if source_account_number in (
            self._profit_account_number,
            self._loss_account_number,
        ):
            return (
                self._profit_loss_carryforward_account_number
            )

        return source_account_number

    def _create_opening_booking(
        self,
        *,
        source_account_number: str,
        target_account_number: str,
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
                    "Saldovortrag Konto "
                    f"{source_account_number}"
                ),
                lines=(
                    BookingLine(
                        account_number=target_account_number,
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
                    "Saldovortrag Konto "
                    f"{source_account_number}"
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
                        account_number=target_account_number,
                        side=EntrySide.CREDIT,
                        amount=credit_balance,
                    ),
                ),
            )

        return None

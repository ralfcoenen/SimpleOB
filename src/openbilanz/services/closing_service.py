"""Services für den Jahresabschluss."""

from datetime import date
from decimal import Decimal

from openbilanz.accounting.income_statement import IncomeStatement
from openbilanz.accounting.ledger import Ledger
from openbilanz.accounting.statement_category import StatementCategory
from openbilanz.domain.account_type import AccountType
from openbilanz.domain.booking import Booking
from openbilanz.domain.booking_line import BookingLine
from openbilanz.domain.booking_type import BookingType
from openbilanz.domain.chart_of_accounts_template import (
    ChartOfAccountsTemplate,
)
from openbilanz.domain.entry_side import EntrySide
from openbilanz.services.closing_accounts import ClosingAccounts
from openbilanz.services.closing_result import ClosingResult


class ClosingService:
    """Führt Abschlussberechnungen und Abschlussbuchungen durch."""

    def __init__(
        self,
        *,
        closing_accounts: ClosingAccounts | None = None,
    ) -> None:
        self._closing_accounts = closing_accounts

    def calculate_net_income(
        self,
        *,
        income: Decimal | None = None,
        expenses: Decimal | None = None,
        income_statement: IncomeStatement | None = None,
    ) -> Decimal:
        """Berechnet Jahresüberschuss oder Jahresfehlbetrag."""

        if income_statement is not None:
            return self._calculate_net_income_from_statement(
                income_statement
            )

        if income is None or expenses is None:
            raise ValueError(
                "income und expenses müssen gemeinsam angegeben werden."
            )

        return income - expenses

    def close(
        self,
        *,
        income_statement: IncomeStatement,
        ledger: Ledger | None = None,
        chart_of_accounts: ChartOfAccountsTemplate | None = None,
        closing_date: date | None = None,
    ) -> ClosingResult:
        """Führt den GuV-Abschluss durch."""

        net_income = self.calculate_net_income(
            income_statement=income_statement,
        )

        bookings: list[Booking] = []

        bookings.extend(
            self._create_account_closing_bookings(
                ledger=ledger,
                chart_of_accounts=chart_of_accounts,
                closing_date=closing_date,
            )
        )

        result_booking = self._create_result_booking(
            net_income=net_income,
            closing_date=closing_date,
        )

        if result_booking is not None:
            bookings.append(result_booking)

        return ClosingResult(
            net_income=net_income,
            bookings=tuple(bookings),
        )

    @classmethod
    def _calculate_net_income_from_statement(
        cls,
        income_statement: IncomeStatement,
    ) -> Decimal:
        """Berechnet das Ergebnis ohne Doppelzählung aggregierter Positionen."""

        income_total, expense_total = cls._statement_totals(
            position=income_statement.income_statement,
            amounts=income_statement.amounts,
        )

        return income_total - expense_total


    @classmethod
    def _statement_totals(
        cls,
        *,
        position,
        amounts,
    ) -> tuple[Decimal, Decimal]:
        """Ermittelt Erlöse und Aufwendungen eines GuV-Teilbaums.

        Sobald eine fachlich kategorisierte Position erreicht wird,
        wird deren bereits aggregierter Betrag verwendet. Untergeordnete
        Positionen werden dann nicht nochmals berücksichtigt.
        """

        amount = amounts.get(
            position,
            Decimal("0.00"),
        )

        if position.category is StatementCategory.INCOME:
            return amount, Decimal("0.00")

        if position.category is StatementCategory.EXPENSE:
            return Decimal("0.00"), amount

        income_total = Decimal("0.00")
        expense_total = Decimal("0.00")

        for child in position.children:
            child_income, child_expenses = cls._statement_totals(
                position=child,
                amounts=amounts,
            )

            income_total += child_income
            expense_total += child_expenses

        return income_total, expense_total
   
    def _create_account_closing_bookings(
        self,
        *,
        ledger: Ledger | None,
        chart_of_accounts: ChartOfAccountsTemplate | None,
        closing_date: date | None,
    ) -> tuple[Booking, ...]:
        """Erzeugt Buchungen zum Abschluss der Erfolgskonten."""

        if (
            ledger is None
            or chart_of_accounts is None
            or closing_date is None
            or self._closing_accounts is None
        ):
            return ()

        account_types = {
            account.account_number: account.account_type
            for account in chart_of_accounts.accounts
        }

        bookings: list[Booking] = []

        for balance in ledger.balances():
            account_type = account_types.get(balance.account_number)

            booking = self._create_account_closing_booking(
                account_number=balance.account_number,
                account_type=account_type,
                debit_balance=balance.debit_balance,
                credit_balance=balance.credit_balance,
                closing_date=closing_date,
            )

            if booking is not None:
                bookings.append(booking)

        return tuple(bookings)

    def _create_account_closing_booking(
        self,
        *,
        account_number: str,
        account_type: AccountType | None,
        debit_balance: Decimal,
        credit_balance: Decimal,
        closing_date: date,
    ) -> Booking | None:
        """Erzeugt die Abschlussbuchung für ein einzelnes Erfolgskonto."""

        if self._closing_accounts is None:
            return None

        if (
            account_type is AccountType.REVENUE
            and credit_balance > Decimal("0.00")
        ):
            return Booking(
                booking_date=closing_date,
                voucher_no=None,
                description=f"Abschluss des Erlöskontos {account_number}",
                booking_type=BookingType.CLOSING,
                lines=(
                    BookingLine(
                        account_number=account_number,
                        side=EntrySide.DEBIT,
                        amount=credit_balance,
                    ),
                    BookingLine(
                        account_number=(
                            self._closing_accounts.income_summary_account
                        ),
                        side=EntrySide.CREDIT,
                        amount=credit_balance,
                    ),
                ),
                            )

        if (
            account_type is AccountType.EXPENSE
            and debit_balance > Decimal("0.00")
        ):
            return Booking(
                booking_date=closing_date,
                voucher_no=None,
                description=f"Abschluss des Aufwandskontos {account_number}",
                booking_type=BookingType.CLOSING,
                lines=(
                    BookingLine(
                        account_number=(
                            self._closing_accounts.income_summary_account
                        ),
                        side=EntrySide.DEBIT,
                        amount=debit_balance,
                    ),
                    BookingLine(
                        account_number=account_number,
                        side=EntrySide.CREDIT,
                        amount=debit_balance,
                    ),
                ),
            )

        return None

    def _create_result_booking(
        self,
        *,
        net_income: Decimal,
        closing_date: date | None,
    ) -> Booking | None:
        """Erzeugt die Abschlussbuchung für Gewinn oder Verlust."""

        if closing_date is None or self._closing_accounts is None:
            return None

        if net_income > Decimal("0.00"):
            return self._create_profit_booking(
                net_income=net_income,
                closing_date=closing_date,
            )

        if net_income < Decimal("0.00"):
            return self._create_loss_booking(
                net_loss=-net_income,
                closing_date=closing_date,
            )

        return None

    def _create_profit_booking(
        self,
        *,
        net_income: Decimal,
        closing_date: date,
    ) -> Booking:
        """Erzeugt die Buchung für einen Jahresüberschuss."""

        assert self._closing_accounts is not None

        return Booking(
            booking_date=closing_date,
            voucher_no=None,
            description="Abschluss des GuV-Kontos",
            booking_type=BookingType.CLOSING,            
            lines=(
                BookingLine(
                    account_number=(
                        self._closing_accounts.income_summary_account
                    ),
                    side=EntrySide.DEBIT,
                    amount=net_income,
                ),
                BookingLine(
                    account_number=self._closing_accounts.profit_account,
                    side=EntrySide.CREDIT,
                    amount=net_income,
                ),
            ),
        )

    def _create_loss_booking(
        self,
        *,
        net_loss: Decimal,
        closing_date: date,
    ) -> Booking:
        """Erzeugt die Buchung für einen Jahresfehlbetrag."""

        assert self._closing_accounts is not None

        return Booking(
            booking_date=closing_date,
            voucher_no=None,
            description="Abschluss des GuV-Kontos",
            booking_type=BookingType.CLOSING,            
            lines=(
                BookingLine(
                    account_number=self._closing_accounts.loss_account,
                    side=EntrySide.DEBIT,
                    amount=net_loss,
                ),
                BookingLine(
                    account_number=(
                        self._closing_accounts.income_summary_account
                    ),
                    side=EntrySide.CREDIT,
                    amount=net_loss,
                ),
            ),
        )

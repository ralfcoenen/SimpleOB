"""Application Service für die Erstellung von Berichten."""

from datetime import date
from decimal import Decimal

from openbilanz.accounting.ledger import Ledger
from openbilanz.domain.booking_type import BookingType
from openbilanz.domain.entry_side import EntrySide
from openbilanz.domain.journal import Journal
from openbilanz.domain.money import ZERO
from openbilanz.reporting.account_activity_report import (
    AccountActivityReport,
    AccountActivityReportLine,
)
from openbilanz.reporting.account_statement import AccountStatement
from openbilanz.reporting.account_statement_line import (
    AccountStatementLine,
)
from openbilanz.reporting.journal_report import (
    JournalReport,
    JournalReportLine,
)
from openbilanz.reporting.trial_balance_report import (
    TrialBalanceReport,
    TrialBalanceReportRow,
)


class ReportingService:
    """Erzeugt unveränderliche Auswertungen aus dem Hauptbuch."""

    def account_statement(
        self,
        *,
        ledger: Ledger,
        account_number: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> AccountStatement:
        """Erzeugt ein Kontoblatt für ein Konto und einen Zeitraum."""

        if not isinstance(
            ledger,
            Ledger,
        ):
            raise TypeError("ledger muss ein Ledger sein.")

        if start_date is not None and not isinstance(
            start_date,
            date,
        ):
            raise TypeError("start_date muss ein Datum oder None sein.")

        if end_date is not None and not isinstance(
            end_date,
            date,
        ):
            raise TypeError("end_date muss ein Datum oder None sein.")

        if start_date is not None and end_date is not None and end_date < start_date:
            raise ValueError("Das Enddatum darf nicht vor dem Startdatum liegen.")

        entries = ledger.entries_for_account(account_number)

        running_balance = ZERO
        lines: list[AccountStatementLine] = []

        for entry in entries:
            if start_date is not None and entry.booking_date < start_date:
                if entry.side is EntrySide.DEBIT:
                    running_balance += entry.amount
                else:
                    running_balance -= entry.amount

                continue

            if end_date is not None and entry.booking_date > end_date:
                continue

            if entry.side is EntrySide.DEBIT:
                running_balance += entry.amount
            else:
                running_balance -= entry.amount

            lines.append(
                AccountStatementLine(
                    entry=entry,
                    running_balance=running_balance,
                )
            )

        return AccountStatement(
            account_number=account_number,
            lines=tuple(lines),
        )

    def trial_balance_report(
        self,
        *,
        ledger: Ledger,
        journal: Journal,
        start_date: date,
        end_date: date,
        opening_balance_account_number: str,
    ) -> TrialBalanceReport:
        """Erzeugt eine Summen- und Saldenliste für einen Zeitraum."""

        if not isinstance(
            ledger,
            Ledger,
        ):
            raise TypeError("ledger muss ein Ledger sein.")

        if not isinstance(
            journal,
            Journal,
        ):
            raise TypeError("journal muss ein Journal sein.")

        if not isinstance(
            start_date,
            date,
        ):
            raise TypeError("start_date muss ein Datum sein.")

        if not isinstance(
            end_date,
            date,
        ):
            raise TypeError("end_date muss ein Datum sein.")

        if end_date < start_date:
            raise ValueError("Das Enddatum darf nicht vor dem Startdatum liegen.")

        opening_account = opening_balance_account_number.strip()

        if not opening_account:
            raise ValueError("Das Eröffnungsbilanzkonto darf nicht leer sein.")

        opening_balances: dict[str, Decimal] = {}
        debit_turnovers: dict[str, Decimal] = {}
        credit_turnovers: dict[str, Decimal] = {}

        account_numbers: set[str] = set()

        for booking in journal:
            # Jahresabschlussbuchungen gehören nicht in
            # die normale Summen- und Saldenliste.
            if booking.booking_type is BookingType.CLOSING:
                continue

            for line in booking.lines:
                account_number = line.account_number

                # Technisches Eröffnungsgegenkonto nicht anzeigen.
                if account_number == opening_account:
                    continue

                if (
                    booking.booking_type is BookingType.OPENING
                    or booking.booking_date < start_date
                ):
                    account_numbers.add(account_number)

                    signed_amount = (
                        line.amount if line.side is EntrySide.DEBIT else -line.amount
                    )

                    opening_balances[account_number] = (
                        opening_balances.get(
                            account_number,
                            ZERO,
                        )
                        + signed_amount
                    )

                    continue

                if booking.booking_date > end_date:
                    continue

                account_numbers.add(account_number)

                if line.side is EntrySide.DEBIT:
                    debit_turnovers[account_number] = (
                        debit_turnovers.get(
                            account_number,
                            ZERO,
                        )
                        + line.amount
                    )
                else:
                    credit_turnovers[account_number] = (
                        credit_turnovers.get(
                            account_number,
                            ZERO,
                        )
                        + line.amount
                    )

        rows: list[TrialBalanceReportRow] = []

        for account_number in sorted(account_numbers):
            opening_balance = opening_balances.get(
                account_number,
                ZERO,
            )

            opening_debit = max(
                opening_balance,
                ZERO,
            )
            opening_credit = max(
                -opening_balance,
                ZERO,
            )

            debit_turnover = debit_turnovers.get(
                account_number,
                ZERO,
            )
            credit_turnover = credit_turnovers.get(
                account_number,
                ZERO,
            )

            closing_balance = opening_balance + debit_turnover - credit_turnover

            closing_debit = max(
                closing_balance,
                ZERO,
            )
            closing_credit = max(
                -closing_balance,
                ZERO,
            )

            rows.append(
                TrialBalanceReportRow(
                    account_number=account_number,
                    opening_debit=opening_debit,
                    opening_credit=opening_credit,
                    debit_turnover=debit_turnover,
                    credit_turnover=credit_turnover,
                    closing_debit=closing_debit,
                    closing_credit=closing_credit,
                )
            )

        return TrialBalanceReport(
            start_date=start_date,
            end_date=end_date,
            rows=tuple(rows),
        )

    def account_activity_report(
        self,
        *,
        journal: Journal,
        account_number: str,
        start_date: date,
        end_date: date,
    ) -> AccountActivityReport:
        """Erzeugt eine gefilterte Kontenauswertung aus dem Journal."""

        if not isinstance(journal, Journal):
            raise TypeError("journal muss ein Journal sein.")

        if not isinstance(start_date, date):
            raise TypeError("start_date muss ein Datum sein.")

        if not isinstance(end_date, date):
            raise TypeError("end_date muss ein Datum sein.")

        if end_date < start_date:
            raise ValueError("Das Enddatum darf nicht vor dem Startdatum liegen.")

        normalized_account_number = account_number.strip()

        if not normalized_account_number:
            raise ValueError("Die Kontonummer darf nicht leer sein.")

        running_balance = ZERO
        lines: list[AccountActivityReportLine] = []

        for booking in journal:
            if booking.booking_type is BookingType.CLOSING:
                continue

            for booking_line in booking.lines:
                if booking_line.account_number != normalized_account_number:
                    continue

                signed_amount = (
                    booking_line.amount
                    if booking_line.side is EntrySide.DEBIT
                    else -booking_line.amount
                )

                if booking.booking_date < start_date:
                    running_balance += signed_amount
                    continue

                if booking.booking_date > end_date:
                    continue

                running_balance += signed_amount

                debit = (
                    booking_line.amount
                    if booking_line.side is EntrySide.DEBIT
                    else ZERO
                )

                credit = (
                    booking_line.amount
                    if booking_line.side is EntrySide.CREDIT
                    else ZERO
                )

                lines.append(
                    AccountActivityReportLine(
                        booking_date=booking.booking_date,
                        voucher_no=booking.voucher_no or "",
                        account_number=normalized_account_number,
                        description=booking.description or "",
                        debit=debit,
                        credit=credit,
                        running_balance=running_balance,
                    )
                )

        return AccountActivityReport(
            account_number=normalized_account_number,
            lines=tuple(lines),
        )

    def journal_report(
        self,
        *,
        journal: Journal,
        start_date: date,
        end_date: date,
    ) -> JournalReport:
        """Erzeugt ein Journal für einen Berichtszeitraum."""

        if not isinstance(journal, Journal):
            raise TypeError("journal muss ein Journal sein.")

        if not isinstance(start_date, date):
            raise TypeError("start_date muss ein Datum sein.")

        if not isinstance(end_date, date):
            raise TypeError("end_date muss ein Datum sein.")

        if end_date < start_date:
            raise ValueError("Das Enddatum darf nicht vor dem Startdatum liegen.")

        lines: list[JournalReportLine] = []

        booking_number = 0

        for booking in journal:
            if booking.booking_type is BookingType.CLOSING:
                continue

            if booking.booking_date < start_date:
                continue

            if booking.booking_date > end_date:
                continue

            booking_number += 1

            for line in booking.lines:
                lines.append(
                    JournalReportLine(
                        booking_id=booking.booking_id,
                        booking_number=booking_number,
                        booking_date=booking.booking_date,
                        voucher_no=booking.voucher_no or "",
                        description=booking.description or "",
                        account_number=line.account_number,
                        side=line.side,
                        amount=line.amount,
                    )
                )

        return JournalReport(
            start_date=start_date,
            end_date=end_date,
            lines=tuple(lines),
        )
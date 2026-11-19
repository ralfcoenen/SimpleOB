"""Application Service für die Erstellung von Berichten."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from simpleob.accounting.ledger import Ledger
from simpleob.domain.booking_type import BookingType
from simpleob.domain.entry_side import EntrySide
from simpleob.domain.fiscal_year import FiscalYear
from simpleob.domain.journal import Journal
from simpleob.domain.money import ZERO
from simpleob.domain.person_account import PersonAccount
from simpleob.reporting.account_activity_report import (
    AccountActivityReport,
    AccountActivityReportLine,
)
from simpleob.reporting.account_statement import AccountStatement
from simpleob.reporting.account_statement_line import (
    AccountStatementLine,
)
from simpleob.reporting.journal_report import (
    JournalReport,
    JournalReportLine,
)
from simpleob.reporting.person_account_report import (
    PersonAccountBalanceRow,
    PersonAccountStatement,
    PersonAccountStatementLine,
    PersonAccountSummary,
)
from simpleob.reporting.trial_balance_report import (
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

            is_legacy_opening_booking = (
                booking.booking_date == start_date
                and any(
                    line.account_number == opening_account
                    for line in booking.lines
                )
            )

            for line in booking.lines:
                account_number = line.account_number

                # Technisches Eröffnungsgegenkonto nicht anzeigen.
                if account_number == opening_account:
                    continue

                if (
                    booking.booking_type is BookingType.OPENING
                    or booking.booking_date < start_date
                    or is_legacy_opening_booking
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
        include_opening_balance: bool = True,
        fiscal_year: FiscalYear | None = None,
    ) -> AccountActivityReport:
        """Erzeugt eine gefilterte Kontenauswertung aus dem Journal."""

        if not isinstance(journal, Journal):
            raise TypeError("journal muss ein Journal sein.")

        if not isinstance(start_date, date):
            raise TypeError("start_date muss ein Datum sein.")

        if not isinstance(end_date, date):
            raise TypeError("end_date muss ein Datum sein.")

        if fiscal_year is not None and not isinstance(fiscal_year, FiscalYear):
            raise TypeError("fiscal_year muss ein FiscalYear oder None sein.")

        if end_date < start_date:
            raise ValueError(
                "Das Enddatum darf nicht vor dem Startdatum liegen."
            )

        normalized_account_number = account_number.strip()

        if not normalized_account_number:
            raise ValueError(
                "Die Kontonummer darf nicht leer sein."
            )

        running_balance = ZERO
        opening_balance = ZERO
        lines: list[AccountActivityReportLine] = []

        ordered_bookings = sorted(
            enumerate(journal),
            key=lambda item: (item[1].booking_date, item[0]),
        )
        for _booking_index, booking in ordered_bookings:
            if booking.booking_type is BookingType.CLOSING:
                continue
            if fiscal_year is not None and not fiscal_year.contains(booking.booking_date):
                continue

            for booking_line in booking.lines:
                if (
                    booking_line.account_number
                    != normalized_account_number
                ):
                    continue

                signed_amount = (
                    booking_line.amount
                    if booking_line.side is EntrySide.DEBIT
                    else -booking_line.amount
                )

                if booking.booking_date < start_date:
                    if include_opening_balance:
                        running_balance += signed_amount
                        opening_balance += signed_amount
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
                        booking_id=booking.booking_id,
                        is_opening=booking.booking_type is BookingType.OPENING,
                    )
                )

        return AccountActivityReport(
            account_number=normalized_account_number,
            lines=tuple(lines),
            opening_balance=opening_balance,
            ending_balance=running_balance,
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

    def person_account_summary(
        self,
        *,
        ledger: Ledger,
        journal: Journal,
        fiscal_year: FiscalYear,
        company_id: UUID,
        person_accounts: tuple[PersonAccount, ...],
        start_date: date,
        end_date: date,
        opening_balance_account_number: str,
    ) -> PersonAccountSummary:
        """Erzeugt eine mandantenspezifische Übersicht der Personenkonten."""

        self._validate_person_account_report_request(
            journal=journal,
            fiscal_year=fiscal_year,
            company_id=company_id,
            person_accounts=person_accounts,
            start_date=start_date,
            end_date=end_date,
        )
        fiscal_year_journal = Journal()
        for booking in journal:
            if fiscal_year.contains(booking.booking_date):
                fiscal_year_journal.add(booking)
        trial_balance = self.trial_balance_report(
            ledger=ledger,
            journal=fiscal_year_journal,
            start_date=start_date,
            end_date=end_date,
            opening_balance_account_number=opening_balance_account_number,
        )
        balances_by_number = {
            row.account_number: row for row in trial_balance.rows
        }
        rows: list[PersonAccountBalanceRow] = []
        for person_account in sorted(
            person_accounts,
            key=lambda item: (item.partner.name.casefold(), item.account.number),
        ):
            account_balance = balances_by_number.get(
                person_account.account.number
            )
            opening_debit = account_balance.opening_debit if account_balance else ZERO
            opening_credit = account_balance.opening_credit if account_balance else ZERO
            opening_balance = opening_debit - opening_credit
            debit_turnover = account_balance.debit_turnover if account_balance else ZERO
            credit_turnover = account_balance.credit_turnover if account_balance else ZERO
            ending_debit_balance = account_balance.closing_debit if account_balance else ZERO
            ending_credit_balance = account_balance.closing_credit if account_balance else ZERO
            ending_balance = ending_debit_balance - ending_credit_balance
            rows.append(
                PersonAccountBalanceRow(
                    account_number=person_account.account.number,
                    partner_id=person_account.partner.partner_id,
                    partner_name=person_account.partner.name,
                    role=person_account.role,
                    opening_balance=opening_balance,
                    debit_turnover=debit_turnover,
                    credit_turnover=credit_turnover,
                    ending_balance=ending_balance,
                    ending_debit_balance=ending_debit_balance,
                    ending_credit_balance=ending_credit_balance,
                )
            )

        return PersonAccountSummary(
            start_date=start_date,
            end_date=end_date,
            rows=tuple(rows),
            opening_debit_total=sum(
                (max(row.opening_balance, ZERO) for row in rows), start=ZERO
            ),
            opening_credit_total=sum(
                (max(-row.opening_balance, ZERO) for row in rows), start=ZERO
            ),
            debit_turnover_total=sum(
                (row.debit_turnover for row in rows), start=ZERO
            ),
            credit_turnover_total=sum(
                (row.credit_turnover for row in rows), start=ZERO
            ),
            ending_debit_total=sum(
                (row.ending_debit_balance for row in rows), start=ZERO
            ),
            ending_credit_total=sum(
                (row.ending_credit_balance for row in rows), start=ZERO
            ),
        )

    def person_account_statement(
        self,
        *,
        journal: Journal,
        fiscal_year: FiscalYear,
        company_id: UUID,
        person_account: PersonAccount,
        start_date: date,
        end_date: date,
        has_opening_source: bool,
    ) -> PersonAccountStatement:
        """Erzeugt ein Kontenblatt ausschließlich für das geöffnete Geschäftsjahr."""

        self._validate_person_account_report_request(
            journal=journal,
            fiscal_year=fiscal_year,
            company_id=company_id,
            person_accounts=(person_account,),
            start_date=start_date,
            end_date=end_date,
        )
        if not isinstance(has_opening_source, bool):
            raise TypeError("has_opening_source muss bool sein.")

        activity = self.account_activity_report(
            journal=journal,
            account_number=person_account.account.number,
            start_date=start_date,
            end_date=end_date,
            include_opening_balance=True,
            fiscal_year=fiscal_year,
        )
        carried_forward_balance = ZERO
        if has_opening_source:
            for booking in journal:
                if (
                    booking.booking_type is not BookingType.OPENING
                    or not fiscal_year.contains(booking.booking_date)
                ):
                    continue
                for line in booking.lines:
                    if line.account_number != person_account.account.number:
                        continue
                    carried_forward_balance += (
                        line.amount
                        if line.side is EntrySide.DEBIT
                        else -line.amount
                    )

        statement_lines = tuple(
            PersonAccountStatementLine(
                booking_date=line.booking_date,
                voucher_no=line.voucher_no,
                description=line.description,
                debit=line.debit,
                credit=line.credit,
                running_balance=line.running_balance,
                booking_id=line.booking_id,
                is_opening=line.is_opening,
            )
            for line in activity.lines
        )

        return PersonAccountStatement(
            fiscal_year_start=fiscal_year.start_date,
            fiscal_year_end=fiscal_year.end_date,
            start_date=start_date,
            end_date=end_date,
            account_number=person_account.account.number,
            account_name=person_account.account.name,
            partner_id=person_account.partner.partner_id,
            partner_name=person_account.partner.name,
            role=person_account.role,
            opening_balance=activity.opening_balance,
            carried_forward_balance=carried_forward_balance,
            lines=statement_lines,
            ending_balance=activity.ending_balance,
        )

    @staticmethod
    def _validate_person_account_report_request(
        *,
        journal: Journal,
        fiscal_year: FiscalYear,
        company_id: UUID,
        person_accounts: tuple[PersonAccount, ...],
        start_date: date,
        end_date: date,
    ) -> None:
        if not isinstance(journal, Journal):
            raise TypeError("journal muss ein Journal sein.")
        if not isinstance(fiscal_year, FiscalYear):
            raise TypeError("fiscal_year muss ein FiscalYear sein.")
        if not isinstance(person_accounts, tuple) or not all(
            isinstance(item, PersonAccount) for item in person_accounts
        ):
            raise TypeError("person_accounts muss ein Tupel von PersonAccount sein.")
        if not isinstance(company_id, UUID):
            raise TypeError("company_id muss eine UUID sein.")
        if not isinstance(start_date, date) or not isinstance(end_date, date):
            raise TypeError("start_date und end_date müssen Daten sein.")
        if start_date < fiscal_year.start_date or end_date > fiscal_year.end_date:
            raise ValueError("Der Auswertungszeitraum muss innerhalb des Geschäftsjahres liegen.")
        if end_date < start_date:
            raise ValueError("Das Enddatum darf nicht vor dem Startdatum liegen.")
        numbers: set[str] = set()
        for item in person_accounts:
            if item.company_id != company_id:
                raise ValueError("Personenkonto gehört zu einem anderen Mandanten.")
            if item.account.person_account_role is not item.role:
                raise ValueError(
                    "Die Personenkontenrolle stimmt nicht mit der geladenen Kontenklassifikation überein."
                )
            if item.account.number in numbers:
                raise ValueError("Die Personenkontenliste enthält doppelte Kontonummern.")
            numbers.add(item.account.number)

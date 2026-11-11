"""Buchungsvorschläge zur Umsatzsteuerverrechnung aus dem Hauptbuch."""

from dataclasses import dataclass
from decimal import Decimal

from simpleob.accounting.account_balance import AccountBalance
from simpleob.accounting.ledger import Ledger
from simpleob.domain.account_type import AccountType
from simpleob.domain.accounting_account_roles import AccountingAccountRoles
from simpleob.domain.booking import Booking
from simpleob.domain.booking_line import BookingLine
from simpleob.domain.booking_type import BookingType
from simpleob.domain.chart_of_accounts_template import ChartOfAccountsTemplate
from simpleob.domain.entry_side import EntrySide
from simpleob.domain.fiscal_year import FiscalYear
from simpleob.domain.money import ZERO
from simpleob.domain.vat_accounts import VatAccounts


@dataclass(frozen=True, slots=True)
class VatAccountBalance:
    """Hauptbuchsaldo eines an der Verrechnung beteiligten Kontos."""

    account_number: str
    account_name: str
    debit_balance: Decimal
    credit_balance: Decimal
    opening_balance: Decimal


@dataclass(frozen=True, slots=True)
class VatReconciliationProposal:
    """Unveränderliche Vorschau samt Buchungsstand-Signatur."""

    fiscal_year: FiscalYear
    account_balances: tuple[VatAccountBalance, ...]
    existing_clearing_balance: Decimal
    resulting_clearing_balance: Decimal
    bookings: tuple[Booking, ...]
    snapshot: tuple[object, ...]


class VatReconciliationService:
    """Ermittelt verrechenbare Steuerkontensalden aus dem Hauptbuch."""

    def build_proposal(
        self,
        *,
        bookings: tuple[Booking, ...],
        ledger: Ledger,
        fiscal_year: FiscalYear,
        vat_accounts: VatAccounts,
        account_roles: AccountingAccountRoles,
        chart_of_accounts: ChartOfAccountsTemplate,
    ) -> VatReconciliationProposal:
        """Erzeugt einen nicht speichernden, saldenbasierten Vorschlag."""

        source_accounts, clearing_account = self._validate_configuration(
            vat_accounts=vat_accounts,
            account_roles=account_roles,
            chart_of_accounts=chart_of_accounts,
        )
        relevant_accounts = frozenset((*source_accounts, clearing_account))
        opening_balances = self._opening_balances(
            bookings=bookings,
            relevant_accounts=relevant_accounts,
        )

        unresolved = tuple(
            (number, amount)
            for number, amount in sorted(opening_balances.items())
            if amount != ZERO
        )
        if unresolved:
            details = ", ".join(
                f"{number}: {amount:.2f} €" for number, amount in unresolved
            )
            raise ValueError(
                "Eröffnungswerte auf Umsatzsteuerkonten sind ungeklärt "
                "und werden nicht verrechnet: "
                + details
                + ". Bitte zuerst manuell zuordnen oder ausgleichen."
            )

        account_names = {
            account.account_number: account.name
            for account in chart_of_accounts.accounts
        }
        account_balances = tuple(
            VatAccountBalance(
                account_number=number,
                account_name=account_names[number],
                debit_balance=self._balance(ledger, number).debit_balance,
                credit_balance=self._balance(ledger, number).credit_balance,
                opening_balance=opening_balances[number],
            )
            for number in (*source_accounts, clearing_account)
        )

        proposed_bookings: list[Booking] = []
        source_net_total = ZERO
        for number in source_accounts:
            balance = self._balance(ledger, number)
            signed_balance = balance.balance
            source_net_total += signed_balance
            if signed_balance > ZERO:
                lines = (
                    BookingLine(
                        clearing_account,
                        EntrySide.DEBIT,
                        signed_balance,
                    ),
                    BookingLine(
                        number,
                        EntrySide.CREDIT,
                        signed_balance,
                    ),
                )
            elif signed_balance < ZERO:
                amount = -signed_balance
                lines = (
                    BookingLine(number, EntrySide.DEBIT, amount),
                    BookingLine(clearing_account, EntrySide.CREDIT, amount),
                )
            else:
                continue
            proposed_bookings.append(
                Booking(
                    booking_date=fiscal_year.end_date,
                    voucher_no=None,
                    description=(
                        f"Umsatzsteuerverrechnung Konto {number} zum Jahresabschluss"
                    ),
                    booking_type=BookingType.REGULAR,
                    lines=lines,
                )
            )
        existing_clearing_balance = self._balance(
            ledger,
            clearing_account,
        ).balance
        resulting_clearing_balance = existing_clearing_balance + source_net_total
        snapshot = self._snapshot(
            bookings=bookings,
            relevant_accounts=relevant_accounts,
            fiscal_year=fiscal_year,
            vat_accounts=vat_accounts,
            account_roles=account_roles,
            ledger=ledger,
        )

        return VatReconciliationProposal(
            fiscal_year=fiscal_year,
            account_balances=account_balances,
            existing_clearing_balance=existing_clearing_balance,
            resulting_clearing_balance=resulting_clearing_balance,
            bookings=tuple(proposed_bookings),
            snapshot=snapshot,
        )

    @staticmethod
    def _validate_configuration(
        *,
        vat_accounts: VatAccounts,
        account_roles: AccountingAccountRoles,
        chart_of_accounts: ChartOfAccountsTemplate,
    ) -> tuple[tuple[str, ...], str]:
        if len(account_roles.vat_advance_payments) != 1:
            raise ValueError(
                "Das Umsatzsteuer-Vorauszahlungskonto ist nicht eindeutig konfiguriert."
            )
        if len(account_roles.vat_current_year) != 1:
            raise ValueError(
                "Das Umsatzsteuer-Verrechnungskonto ist nicht eindeutig konfiguriert."
            )

        source_accounts = (
            vat_accounts.output_tax_7,
            vat_accounts.output_tax_19,
            vat_accounts.input_tax_7,
            vat_accounts.input_tax_19,
            next(iter(account_roles.vat_advance_payments)),
        )
        clearing_account = next(iter(account_roles.vat_current_year))
        all_accounts = (*source_accounts, clearing_account)
        if len(set(all_accounts)) != len(all_accounts):
            raise ValueError(
                "Die Umsatzsteuerkonten und das Verrechnungskonto müssen "
                "eindeutig voneinander getrennt konfiguriert sein."
            )

        account_types = {
            account.account_number: account.account_type
            for account in chart_of_accounts.accounts
        }
        expected_types = {
            vat_accounts.output_tax_7: AccountType.LIABILITY,
            vat_accounts.output_tax_19: AccountType.LIABILITY,
            vat_accounts.input_tax_7: AccountType.ASSET,
            vat_accounts.input_tax_19: AccountType.ASSET,
            next(iter(account_roles.vat_advance_payments)): AccountType.ASSET,
            clearing_account: AccountType.LIABILITY,
        }
        for number, expected_type in expected_types.items():
            actual_type = account_types.get(number)
            if actual_type is not expected_type:
                raise ValueError(
                    f"Das konfigurierte Umsatzsteuerkonto {number} fehlt "
                    "im Kontenrahmen oder hat einen ungeeigneten Kontentyp."
                )

        rules = {
            rule.account_number: rule
            for rule in chart_of_accounts.account_mapping_rules
        }
        clearing_rule = rules.get(clearing_account)
        if (
            clearing_rule is None
            or clearing_rule.debit_position is None
            or clearing_rule.credit_position is None
            or clearing_rule.debit_position.code != "HGB.266.AKTIVA.B.II.4"
            or clearing_rule.credit_position.code != "HGB.266.PASSIVA.C.8"
        ):
            raise ValueError(
                "Das Umsatzsteuer-Verrechnungskonto benötigt die HGB- "
                "Zuordnungen Soll B.II.4 und Haben C.8."
            )

        return source_accounts, clearing_account

    @staticmethod
    def _opening_balances(
        *,
        bookings: tuple[Booking, ...],
        relevant_accounts: frozenset[str],
    ) -> dict[str, Decimal]:
        opening_ids = {
            booking.booking_id
            for booking in bookings
            if booking.booking_type is BookingType.OPENING
        }
        balances = {number: ZERO for number in relevant_accounts}
        for booking in bookings:
            is_opening = booking.booking_type is BookingType.OPENING
            reverses_opening = (
                booking.booking_type is BookingType.REVERSAL
                and booking.reversal_of_booking_id in opening_ids
            )
            if not is_opening and not reverses_opening:
                continue
            for line in booking.lines:
                if line.account_number not in relevant_accounts:
                    continue
                amount = line.amount
                balances[line.account_number] += (
                    amount if line.side is EntrySide.DEBIT else -amount
                )
        return balances

    @staticmethod
    def _balance(ledger: Ledger, account_number: str) -> AccountBalance:
        if ledger.has_account(account_number):
            return ledger.get_account(account_number)
        return AccountBalance(account_number)

    @classmethod
    def _snapshot(
        cls,
        *,
        bookings: tuple[Booking, ...],
        relevant_accounts: frozenset[str],
        fiscal_year: FiscalYear,
        vat_accounts: VatAccounts,
        account_roles: AccountingAccountRoles,
        ledger: Ledger,
    ) -> tuple[object, ...]:
        booking_fingerprint = tuple(
            (
                str(booking.booking_id),
                booking.booking_date,
                booking.booking_type.value,
                (
                    str(booking.reversal_of_booking_id)
                    if booking.reversal_of_booking_id is not None
                    else None
                ),
                tuple(
                    (line.account_number, line.side.value, line.amount)
                    for line in booking.lines
                ),
            )
            for booking in bookings
        )
        balances = tuple(
            (
                number,
                cls._balance(ledger, number).debit_balance,
                cls._balance(ledger, number).credit_balance,
            )
            for number in sorted(relevant_accounts)
        )
        return (
            fiscal_year.start_date,
            fiscal_year.end_date,
            vat_accounts.account_numbers,
            account_roles.vat_advance_payments,
            account_roles.vat_current_year,
            balances,
            booking_fingerprint,
        )

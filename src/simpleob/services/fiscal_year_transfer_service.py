"""Service für die Überleitung in ein neues Geschäftsjahr."""

from datetime import date
from decimal import Decimal

from simpleob.accounting.ledger import Ledger
from simpleob.domain.account_type import AccountType
from simpleob.domain.accounting_account_roles import AccountingAccountRoles
from simpleob.domain.booking import Booking
from simpleob.domain.booking_line import BookingLine
from simpleob.domain.booking_type import BookingType
from simpleob.domain.chart_of_accounts_template import ChartOfAccountsTemplate
from simpleob.domain.entry_side import EntrySide


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
        account_roles: AccountingAccountRoles | None = None,
        chart_of_accounts: ChartOfAccountsTemplate | None = None,
    ) -> tuple[Booking, ...]:
        """Erzeugt Saldovorträge für Bestandskonten."""

        bookings: list[Booking] = []

        balance_sheet_account_types = {
            AccountType.ASSET,
            AccountType.LIABILITY,
            AccountType.EQUITY,
        }

        vat_current_account = None
        vat_receivable_account = None
        vat_payable_account = None
        if account_roles is not None and account_roles.vat_current_year:
            (
                vat_current_account,
            ) = tuple(account_roles.vat_current_year)
            (
                vat_receivable_account,
            ) = tuple(account_roles.vat_prior_year_receivables)
            (
                vat_payable_account,
            ) = tuple(account_roles.vat_prior_year_payables)
            self._validate_vat_transfer_configuration(
                account_roles=account_roles,
                account_types=account_types,
                chart_of_accounts=chart_of_accounts,
            )

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

            if source_account_number == vat_current_account:
                if balance.debit_balance > Decimal("0.00"):
                    target_account_number = vat_receivable_account
                elif balance.credit_balance > Decimal("0.00"):
                    target_account_number = vat_payable_account
                else:
                    continue
            else:
                target_account_number = self._opening_account_number(
                    source_account_number
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

    @staticmethod
    def _validate_vat_transfer_configuration(
        *,
        account_roles: AccountingAccountRoles,
        account_types: dict[str, AccountType],
        chart_of_accounts: ChartOfAccountsTemplate | None,
    ) -> None:
        """Prüft die Umsatzsteuerkonten vor dem Erzeugen von Buchungen."""

        configured = (
            (account_roles.vat_advance_payments, AccountType.ASSET, "Umsatzsteuer-Vorauszahlung"),
            (account_roles.vat_current_year, AccountType.LIABILITY, "Umsatzsteuer laufendes Jahr"),
            (account_roles.vat_prior_year_receivables, AccountType.ASSET, "Umsatzsteuerforderung Vorjahr"),
            (account_roles.vat_prior_year_payables, AccountType.LIABILITY, "Umsatzsteuerverbindlichkeit Vorjahr"),
        )
        for accounts, expected_type, label in configured:
            number = next(iter(accounts))
            if number not in account_types:
                raise ValueError(
                    f"Das konfigurierte Konto {label} {number} "
                    "ist im Mandantenkontenrahmen nicht vorhanden."
                )
            if account_types[number] is not expected_type:
                raise ValueError(
                    f"Das konfigurierte Konto {label} {number} muss "
                    f"den Kontotyp {expected_type.name} haben."
                )

        if chart_of_accounts is None:
            raise ValueError(
                "Die HGB-Zuordnungen der Umsatzsteuerkonten können "
                "bei der Geschäftsjahresübernahme nicht geprüft werden."
            )

        chart_account_numbers = {
            account.account_number
            for account in chart_of_accounts.accounts
        }
        missing_from_chart = sorted(
            number
            for accounts, _expected_type, _label in configured
            for number in accounts
            if number not in chart_account_numbers
        )
        if missing_from_chart:
            raise ValueError(
                "Konfigurierte Umsatzsteuerkonten fehlen im "
                "Mandantenkontenrahmen: "
                + ", ".join(missing_from_chart)
            )

        rules = {
            rule.account_number: rule
            for rule in chart_of_accounts.account_mapping_rules
        }
        required_positions = (
            (account_roles.vat_advance_payments, "debit_position", "HGB.266.AKTIVA.B.II.4"),
            (account_roles.vat_current_year, "debit_position", "HGB.266.AKTIVA.B.II.4"),
            (account_roles.vat_current_year, "credit_position", "HGB.266.PASSIVA.C.8"),
            (account_roles.vat_prior_year_receivables, "debit_position", "HGB.266.AKTIVA.B.II.4"),
            (account_roles.vat_prior_year_payables, "credit_position", "HGB.266.PASSIVA.C.8"),
        )
        for accounts, side, expected_code in required_positions:
            number = next(iter(accounts))
            rule = rules.get(number)
            position = getattr(rule, side, None)
            if position is None or position.code != expected_code:
                side_label = "Soll" if side == "debit_position" else "Haben"
                raise ValueError(
                    f"Dem Umsatzsteuerkonto {number} fehlt die "
                    f"erforderliche HGB-{side_label}-Zuordnung "
                    f"{expected_code}."
                )

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
                booking_type=BookingType.OPENING,
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
                booking_type=BookingType.OPENING,
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

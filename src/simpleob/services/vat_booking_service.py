"""Erzeugung von Umsatzsteuerbuchungen."""

from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from simpleob.domain.booking import Booking
from simpleob.domain.booking_line import BookingLine
from simpleob.domain.entry_side import EntrySide
from simpleob.domain.money import ZERO
from simpleob.domain.vat_accounts import VatAccounts
from simpleob.domain.vat_booking_item import (
    VatBookingItem,
)

CENT = Decimal("0.01")
HUNDRED = Decimal("100")


class VatBookingService:
    """Erzeugt Buchungen mit Vor- oder Umsatzsteuer."""

    def build_output_booking(
        self,
        *,
        booking_date: date,
        counter_account_number: str,
        items: tuple[VatBookingItem, ...],
        vat_accounts: VatAccounts,
        voucher_no: str | None = None,
        description: str | None = None,
    ) -> Booking:
        """Erzeugt eine Ausgangsbuchung."""

        lines: list[BookingLine] = []
        gross_total = ZERO

        for item in self._validate_items(items):
            net_amount, tax_amount = (
                self._split_gross_amount(item)
            )

            gross_total += item.gross_amount

            lines.append(
                BookingLine(
                    account_number=item.account_number,
                    side=EntrySide.CREDIT,
                    amount=net_amount,
                )
            )

            if tax_amount > ZERO:
                lines.append(
                    BookingLine(
                        account_number=(
                            self._output_tax_account(
                                item.tax_rate,
                                vat_accounts,
                            )
                        ),
                        side=EntrySide.CREDIT,
                        amount=tax_amount,
                    )
                )

        lines.insert(
            0,
            BookingLine(
                account_number=counter_account_number,
                side=EntrySide.DEBIT,
                amount=gross_total,
            ),
        )

        return Booking(
            booking_date=booking_date,
            voucher_no=voucher_no,
            description=description,
            lines=tuple(lines),
        )

    def build_input_booking(
        self,
        *,
        booking_date: date,
        counter_account_number: str,
        items: tuple[VatBookingItem, ...],
        vat_accounts: VatAccounts,
        voucher_no: str | None = None,
        description: str | None = None,
    ) -> Booking:
        """Erzeugt eine Eingangsbuchung."""

        lines: list[BookingLine] = []
        gross_total = ZERO

        for item in self._validate_items(items):
            net_amount, tax_amount = (
                self._split_gross_amount(item)
            )

            gross_total += item.gross_amount

            lines.append(
                BookingLine(
                    account_number=item.account_number,
                    side=EntrySide.DEBIT,
                    amount=net_amount,
                )
            )

            if tax_amount > ZERO:
                lines.append(
                    BookingLine(
                        account_number=(
                            self._input_tax_account(
                                item.tax_rate,
                                vat_accounts,
                            )
                        ),
                        side=EntrySide.DEBIT,
                        amount=tax_amount,
                    )
                )

        lines.append(
            BookingLine(
                account_number=counter_account_number,
                side=EntrySide.CREDIT,
                amount=gross_total,
            )
        )

        return Booking(
            booking_date=booking_date,
            voucher_no=voucher_no,
            description=description,
            lines=tuple(lines),
        )

    def build_customer_credit_note(
        self,
        *,
        booking_date: date,
        counter_account_number: str,
        items: tuple[VatBookingItem, ...],
        vat_accounts: VatAccounts,
        voucher_no: str | None = None,
        description: str | None = None,
    ) -> Booking:
        """Erzeugt eine Kundengutschrift."""

        lines: list[BookingLine] = []
        gross_total = ZERO

        for item in self._validate_items(items):
            net_amount, tax_amount = (
                self._split_gross_amount(item)
            )

            gross_total += item.gross_amount

            lines.append(
                BookingLine(
                    account_number=item.account_number,
                    side=EntrySide.DEBIT,
                    amount=net_amount,
                )
            )

            if tax_amount > ZERO:
                lines.append(
                    BookingLine(
                        account_number=(
                            self._output_tax_account(
                                item.tax_rate,
                                vat_accounts,
                            )
                        ),
                        side=EntrySide.DEBIT,
                        amount=tax_amount,
                    )
                )

        lines.append(
            BookingLine(
                account_number=counter_account_number,
                side=EntrySide.CREDIT,
                amount=gross_total,
            )
        )

        return Booking(
            booking_date=booking_date,
            voucher_no=voucher_no,
            description=description,
            lines=tuple(lines),
        )

    def build_supplier_credit_note(
        self,
        *,
        booking_date: date,
        counter_account_number: str,
        items: tuple[VatBookingItem, ...],
        vat_accounts: VatAccounts,
        voucher_no: str | None = None,
        description: str | None = None,
    ) -> Booking:
        """Erzeugt eine Lieferantengutschrift."""

        lines: list[BookingLine] = []
        gross_total = ZERO

        for item in self._validate_items(items):
            net_amount, tax_amount = (
                self._split_gross_amount(item)
            )

            gross_total += item.gross_amount

            lines.append(
                BookingLine(
                    account_number=item.account_number,
                    side=EntrySide.CREDIT,
                    amount=net_amount,
                )
            )

            if tax_amount > ZERO:
                lines.append(
                    BookingLine(
                        account_number=(
                            self._input_tax_account(
                                item.tax_rate,
                                vat_accounts,
                            )
                        ),
                        side=EntrySide.CREDIT,
                        amount=tax_amount,
                    )
                )

        lines.insert(
            0,
            BookingLine(
                account_number=counter_account_number,
                side=EntrySide.DEBIT,
                amount=gross_total,
            ),
        )

        return Booking(
            booking_date=booking_date,
            voucher_no=voucher_no,
            description=description,
            lines=tuple(lines),
        )

    @staticmethod
    def _validate_items(
        items: tuple[VatBookingItem, ...],
    ) -> tuple[VatBookingItem, ...]:
        if not isinstance(items, tuple):
            raise TypeError(
                "items must be a tuple"
            )

        if not items:
            raise ValueError(
                "items must not be empty"
            )

        if not all(
            isinstance(item, VatBookingItem)
            for item in items
        ):
            raise TypeError(
                "items must contain only VatBookingItem objects"
            )

        return items

    @staticmethod
    def _split_gross_amount(
        item: VatBookingItem,
    ) -> tuple[Decimal, Decimal]:
        if item.tax_rate == 0:
            return (
                item.gross_amount,
                ZERO,
            )

        divisor = (
            Decimal("1")
            + Decimal(item.tax_rate) / HUNDRED
        )

        net_amount = (
            item.gross_amount / divisor
        ).quantize(
            CENT,
            rounding=ROUND_HALF_UP,
        )

        tax_amount = (
            item.gross_amount - net_amount
        ).quantize(
            CENT,
            rounding=ROUND_HALF_UP,
        )

        return (
            net_amount,
            tax_amount,
        )

    @staticmethod
    def _input_tax_account(
        tax_rate: int,
        vat_accounts: VatAccounts,
    ) -> str:
        if tax_rate == 7:
            return vat_accounts.input_tax_7

        if tax_rate == 19:
            return vat_accounts.input_tax_19

        raise ValueError(
            "Für 0 % ist kein Vorsteuerkonto erforderlich."
        )

    @staticmethod
    def _output_tax_account(
        tax_rate: int,
        vat_accounts: VatAccounts,
    ) -> str:
        if tax_rate == 7:
            return vat_accounts.output_tax_7

        if tax_rate == 19:
            return vat_accounts.output_tax_19

        raise ValueError(
            "Für 0 % ist kein Umsatzsteuerkonto erforderlich."
        )

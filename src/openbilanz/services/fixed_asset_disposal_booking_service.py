"""Erzeugung von Buchungen für den Verkauf eines Anlageguts."""

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from openbilanz.domain.booking import Booking
from openbilanz.domain.booking_line import BookingLine
from openbilanz.domain.booking_type import BookingType
from openbilanz.domain.entry_side import EntrySide
from openbilanz.domain.money import to_decimal

_CENT = Decimal("0.01")


@dataclass(frozen=True, slots=True)
class FixedAssetDisposalBookings:
    """Die beiden Buchungen eines Anlagenverkaufs."""

    sale_booking: Booking
    book_value_booking: Booking


class FixedAssetDisposalBookingService:
    """Erzeugt Verkaufs- und Buchwertabgangsbuchungen."""

    def build_bookings(
        self,
        *,
        disposal_date: date,
        asset_code: str,
        net_sale_amount: Decimal,
        book_value: Decimal,
        settlement_account_number: str,
        revenue_account_number: str,
        output_tax_account_number: str,
        asset_account_number: str,
        book_value_expense_account_number: str,
        tax_rate: Decimal = Decimal("0.19"),
    ) -> FixedAssetDisposalBookings:
        """Erzeugt die beiden Buchungen eines Anlagenverkaufs."""

        if not isinstance(
            disposal_date,
            date,
        ):
            raise TypeError(
                "disposal_date must be a date"
            )

        net_sale_amount = to_decimal(
            net_sale_amount
        )
        book_value = to_decimal(
            book_value
        )
        tax_rate = to_decimal(
            tax_rate
        )

        if net_sale_amount <= Decimal("0.00"):
            raise ValueError(
                "net_sale_amount must be greater than 0.00"
            )

        if book_value <= Decimal("0.00"):
            raise ValueError(
                "book_value must be greater than 0.00"
            )

        if tax_rate < Decimal("0.00"):
            raise ValueError(
                "tax_rate must not be negative"
            )

        tax_amount = (
            net_sale_amount
            * tax_rate
        ).quantize(
            _CENT,
            rounding=ROUND_HALF_UP,
        )

        gross_sale_amount = (
            net_sale_amount
            + tax_amount
        )

        sale_lines = [
            BookingLine(
                account_number=(
                    settlement_account_number
                ),
                side=EntrySide.DEBIT,
                amount=gross_sale_amount,
            ),
            BookingLine(
                account_number=(
                    revenue_account_number
                ),
                side=EntrySide.CREDIT,
                amount=net_sale_amount,
            ),
        ]

        if tax_amount > Decimal("0.00"):
            sale_lines.append(
                BookingLine(
                    account_number=(
                        output_tax_account_number
                    ),
                    side=EntrySide.CREDIT,
                    amount=tax_amount,
                )
            )

        sale_booking = Booking(
            booking_date=disposal_date,
            description=(
                f"Verkauf Anlagegut – {asset_code}"
            ),
            booking_type=BookingType.REGULAR,
            lines=tuple(sale_lines),
        )

        book_value_booking = Booking(
            booking_date=disposal_date,
            description=(
                f"Buchwertabgang Anlagegut – {asset_code}"
            ),
            booking_type=BookingType.REGULAR,
            lines=(
                BookingLine(
                    account_number=(
                        book_value_expense_account_number
                    ),
                    side=EntrySide.DEBIT,
                    amount=book_value,
                ),
                BookingLine(
                    account_number=(
                        asset_account_number
                    ),
                    side=EntrySide.CREDIT,
                    amount=book_value,
                ),
            ),
        )

        return FixedAssetDisposalBookings(
            sale_booking=sale_booking,
            book_value_booking=book_value_booking,
        )

"""Berechnung und Buchungsvorschlag für Anlagenverkäufe."""

from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from simpleob.domain.accounting_control_accounts import (
    AccountingControlAccounts,
)
from simpleob.domain.booking import Booking
from simpleob.domain.booking_line import BookingLine
from simpleob.domain.entry_side import EntrySide
from simpleob.domain.fixed_asset_disposal_calculation import (
    FixedAssetDisposalCalculation,
)
from simpleob.domain.money import ZERO, to_decimal
from simpleob.domain.vat_accounts import VatAccounts

CENT = Decimal("0.01")
HUNDRED = Decimal("100")


class FixedAssetDisposalService:
    """Berechnet einen Anlagenverkauf und dessen Buchung."""

    def calculate(
        self,
        *,
        booking_date: date,
        acquisition_cost: Decimal,
        accumulated_depreciation: Decimal,
        gross_proceeds: Decimal,
        tax_rate: int,
        asset_account_number: str,
        counter_account_number: str,
        control_accounts: AccountingControlAccounts,
        vat_accounts: VatAccounts,
        voucher_no: str | None = None,
        description: str | None = None,
    ) -> FixedAssetDisposalCalculation:
        """Berechnet Restbuchwert, Erfolg und Buchung."""

        if not isinstance(booking_date, date):
            raise TypeError(
                "booking_date must be a date"
            )

        acquisition_cost = to_decimal(
            acquisition_cost
        )
        accumulated_depreciation = to_decimal(
            accumulated_depreciation
        )
        gross_proceeds = to_decimal(
            gross_proceeds
        )

        if acquisition_cost <= ZERO:
            raise ValueError(
                "acquisition_cost must be greater than zero"
            )

        if accumulated_depreciation < ZERO:
            raise ValueError(
                "accumulated_depreciation must not be negative"
            )

        if accumulated_depreciation >= acquisition_cost:
            raise ValueError(
                "accumulated_depreciation must be less than "
                "acquisition_cost"
            )

        if gross_proceeds <= ZERO:
            raise ValueError(
                "gross_proceeds must be greater than zero"
            )

        if tax_rate not in (0, 7, 19):
            raise ValueError(
                "tax_rate must be 0, 7 or 19"
            )

        asset_account_number = (
            self._validate_account_number(
                asset_account_number,
                "asset_account_number",
            )
        )
        counter_account_number = (
            self._validate_account_number(
                counter_account_number,
                "counter_account_number",
            )
        )

        carrying_amount = (
            acquisition_cost
            - accumulated_depreciation
        ).quantize(
            CENT,
            rounding=ROUND_HALF_UP,
        )

        net_proceeds, tax_amount = (
            self._split_gross_amount(
                gross_proceeds=gross_proceeds,
                tax_rate=tax_rate,
            )
        )

        difference = (
            net_proceeds - carrying_amount
        ).quantize(
            CENT,
            rounding=ROUND_HALF_UP,
        )

        gain = max(
            difference,
            ZERO,
        )
        loss = max(
            -difference,
            ZERO,
        )

        lines: list[BookingLine] = [
            BookingLine(
                account_number=counter_account_number,
                side=EntrySide.DEBIT,
                amount=gross_proceeds,
            ),
            BookingLine(
                account_number=asset_account_number,
                side=EntrySide.CREDIT,
                amount=carrying_amount,
            ),
        ]

        if loss > ZERO:
            lines.append(
                BookingLine(
                    account_number=(
                        control_accounts
                        .fixed_asset_disposal_loss_account
                    ),
                    side=EntrySide.DEBIT,
                    amount=loss,
                )
            )

        if gain > ZERO:
            lines.append(
                BookingLine(
                    account_number=(
                        control_accounts
                        .fixed_asset_disposal_gain_account
                    ),
                    side=EntrySide.CREDIT,
                    amount=gain,
                )
            )

        if tax_amount > ZERO:
            lines.append(
                BookingLine(
                    account_number=self._output_tax_account(
                        tax_rate=tax_rate,
                        vat_accounts=vat_accounts,
                    ),
                    side=EntrySide.CREDIT,
                    amount=tax_amount,
                )
            )

        booking = Booking(
            booking_date=booking_date,
            voucher_no=voucher_no,
            description=description,
            lines=tuple(lines),
        )

        return FixedAssetDisposalCalculation(
            acquisition_cost=acquisition_cost,
            accumulated_depreciation=(
                accumulated_depreciation
            ),
            carrying_amount=carrying_amount,
            gross_proceeds=gross_proceeds,
            net_proceeds=net_proceeds,
            tax_amount=tax_amount,
            gain=gain,
            loss=loss,
            booking=booking,
        )

    @staticmethod
    def _split_gross_amount(
        *,
        gross_proceeds: Decimal,
        tax_rate: int,
    ) -> tuple[Decimal, Decimal]:
        if tax_rate == 0:
            return (
                gross_proceeds,
                ZERO,
            )

        divisor = (
            Decimal("1")
            + Decimal(tax_rate) / HUNDRED
        )

        net_proceeds = (
            gross_proceeds / divisor
        ).quantize(
            CENT,
            rounding=ROUND_HALF_UP,
        )

        tax_amount = (
            gross_proceeds - net_proceeds
        ).quantize(
            CENT,
            rounding=ROUND_HALF_UP,
        )

        return (
            net_proceeds,
            tax_amount,
        )

    @staticmethod
    def _output_tax_account(
        *,
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

    @staticmethod
    def _validate_account_number(
        account_number: str,
        field_name: str,
    ) -> str:
        if not isinstance(account_number, str):
            raise TypeError(
                f"{field_name} must be a str"
            )

        account_number = account_number.strip()

        if not account_number:
            raise ValueError(
                f"{field_name} must not be blank"
            )

        if not account_number.isdigit():
            raise ValueError(
                f"{field_name} must contain digits only"
            )

        return account_number

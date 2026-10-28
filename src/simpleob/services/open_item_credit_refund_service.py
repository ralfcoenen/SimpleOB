"""Atomare Haupt- und Nebenbuchung von Guthabenrückerstattungen."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from simpleob.database.booking_repository import BookingRepository
from simpleob.database.chart_of_accounts_repository import ChartOfAccountsRepository
from simpleob.database.open_item_credit_refund_repository import (
    OpenItemCreditRefundRepository,
)
from simpleob.database.open_item_offset_repository import OpenItemOffsetRepository
from simpleob.domain.booking import Booking
from simpleob.domain.booking_line import BookingLine
from simpleob.domain.entry_side import EntrySide
from simpleob.domain.fiscal_year import FiscalYear
from simpleob.domain.money import ZERO, to_decimal
from simpleob.domain.open_item_credit_refund import OpenItemCreditRefund
from simpleob.domain.open_item_offset import OffsetDirection


class OpenItemCreditRefundService:
    """Bucht die Auszahlung oder Erstattung genau eines Guthaben-OPs."""

    def __init__(
        self,
        *,
        booking_repository: BookingRepository,
        refund_repository: OpenItemCreditRefundRepository,
        offset_repository: OpenItemOffsetRepository,
        chart_of_accounts_repository: ChartOfAccountsRepository,
    ) -> None:
        self._booking_repository = booking_repository
        self._refund_repository = refund_repository
        self._offset_repository = offset_repository
        self._chart_of_accounts_repository = chart_of_accounts_repository

    def cash_bank_account_numbers(self, company_id: UUID) -> frozenset[str]:
        roles = self._chart_of_accounts_repository.load_account_roles(company_id)
        if roles is None:
            return frozenset()
        return roles.cash_accounts | roles.bank_accounts

    def post_refund(
        self,
        *,
        company_id: UUID,
        fiscal_year: FiscalYear,
        partner_id: UUID,
        open_item_id: UUID,
        direction: OffsetDirection,
        amount: Decimal,
        refund_date: date,
        booking_date: date,
        cash_bank_account_number: str,
        description: str | None = None,
        refund_id: UUID | None = None,
    ) -> OpenItemCreditRefund:
        """Bucht genau eine Rückerstattung und reduziert den Guthaben-OP."""
        try:
            if not isinstance(direction, OffsetDirection):
                raise TypeError("direction must be an OffsetDirection")
            amount = to_decimal(amount)
            if amount <= ZERO:
                raise ValueError("Der Rückerstattungsbetrag muss größer als 0,00 sein.")

            # SQLite otherwise allows competing readers to validate the same
            # credit before either transaction obtains its first write lock.
            self._offset_repository.reserve_credit_mutation()
            credit = self._offset_repository.get_credit(
                company_id=company_id,
                partner_id=partner_id,
                open_item_id=open_item_id,
                direction=direction,
                for_update=True,
            )
            if credit is None:
                raise ValueError("Der Guthaben-OP ist nicht vorhanden.")
            if credit.available_amount <= ZERO:
                raise ValueError("Das Guthaben ist bereits vollständig verbraucht.")
            if amount > credit.available_amount:
                raise ValueError("Der Rückerstattungsbetrag übersteigt das verfügbare Guthaben.")
            if credit.origin_booking_date is None:
                raise ValueError("Das Buchungsdatum der Guthabenentstehung ist nicht feststellbar.")
            if booking_date < credit.origin_booking_date:
                raise ValueError(
                    "Das Buchungsdatum der Rückerstattung darf nicht vor dem "
                    f"Entstehungsdatum des Guthabens ({credit.origin_booking_date:%d.%m.%Y}) liegen."
                )

            self._booking_repository.require_open_fiscal_year(
                company_id=company_id,
                fiscal_year=fiscal_year,
                booking_date=booking_date,
                for_update=True,
            )
            self._chart_of_accounts_repository.validate_payment_cash_bank_account(
                company_id=company_id,
                account_number=cash_bank_account_number,
            )

            if direction is OffsetDirection.CUSTOMER:
                control_side = EntrySide.DEBIT
                cash_side = EntrySide.CREDIT
                refund_label = "Auszahlung Kundenguthaben"
            else:
                control_side = EntrySide.CREDIT
                cash_side = EntrySide.DEBIT
                refund_label = "Lieferantenerstattung"
            booking = Booking(
                booking_date=booking_date,
                description=(
                    description
                    or f"{refund_label}, {credit.document_number}"
                ),
                lines=(
                    BookingLine(credit.account_number, control_side, amount),
                    BookingLine(cash_bank_account_number, cash_side, amount),
                ),
            )
            refund = OpenItemCreditRefund(
                company_id=company_id,
                partner_id=partner_id,
                open_item_id=open_item_id,
                direction=direction,
                amount=amount,
                refund_date=refund_date,
                booking_id=booking.booking_id,
                **({"refund_id": refund_id} if refund_id is not None else {}),
            )
            self._booking_repository.add(
                company_id=company_id,
                fiscal_year=fiscal_year,
                booking=booking,
                commit=False,
            )
            self._refund_repository.add(
                refund=refund,
                fiscal_year=fiscal_year,
                commit=False,
            )
            self._booking_repository.commit()
            return refund
        except Exception:
            self._booking_repository.rollback()
            raise

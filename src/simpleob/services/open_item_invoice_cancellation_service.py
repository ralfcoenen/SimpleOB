"""Vollständiges Storno von Kunden- und Lieferantenrechnungen."""

from datetime import date
from uuid import UUID

from simpleob.database.open_item_invoice_cancellation_repository import (
    OpenItemInvoiceCancellationRepository,
)
from simpleob.domain.fiscal_year import FiscalYear
from simpleob.domain.open_item_invoice_cancellation import (
    InvoiceCancellationPaymentAssessment,
    InvoiceCancellationPreview,
)


class OpenItemInvoiceCancellationService:
    """Anwendungsdienst für den dedizierten OP-Rechnungsstornoweg."""

    def __init__(
        self,
        repository: OpenItemInvoiceCancellationRepository,
    ) -> None:
        self._repository = repository

    def preview(
        self,
        *,
        company_id: UUID,
        fiscal_year: FiscalYear,
        open_item_id: UUID,
    ) -> InvoiceCancellationPreview:
        return self._repository.preview(
            company_id=company_id,
            fiscal_year=fiscal_year,
            open_item_id=open_item_id,
        )

    def assess_payment_history(
        self,
        *,
        company_id: UUID,
        fiscal_year: FiscalYear,
        open_item_id: UUID,
        proposed_booking_date: date,
    ) -> InvoiceCancellationPaymentAssessment:
        """Liefert nur eine Zulassungs-/Betragsprüfung, keine Stornierung."""
        return self._repository.assess_payment_history(
            company_id=company_id,
            fiscal_year=fiscal_year,
            open_item_id=open_item_id,
            proposed_booking_date=proposed_booking_date,
        )

    def cancel_invoice(
        self,
        *,
        company_id: UUID,
        fiscal_year: FiscalYear,
        open_item_id: UUID,
        booking_date: date,
        reason: str,
        confirmed: bool,
    ) -> UUID:
        if confirmed is not True:
            raise ValueError("Das Rechnungsstorno wurde nicht ausdrücklich bestätigt.")
        return self._repository.add_atomic(
            company_id=company_id,
            fiscal_year=fiscal_year,
            open_item_id=open_item_id,
            booking_date=booking_date,
            reason=reason,
        )

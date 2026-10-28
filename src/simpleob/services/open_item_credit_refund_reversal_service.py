"""Fachlicher Service für vollständige Guthabenrückerstattungsrücknahmen."""

from datetime import date
from uuid import UUID

from simpleob.database.open_item_credit_refund_reversal_repository import (
    OpenItemCreditRefundReversalRepository,
)
from simpleob.domain.fiscal_year import FiscalYear
from simpleob.domain.open_item_credit_refund_reversal import (
    OpenItemCreditRefundReversal,
    OpenItemCreditRefundReversalCandidate,
)


class OpenItemCreditRefundReversalService:
    """Delegiert die atomare Rücknahme an den spezialisierten Schreibpfad."""

    def __init__(self, repository: OpenItemCreditRefundReversalRepository) -> None:
        self._repository = repository

    def list_candidates(
        self, *, company_id: UUID, fiscal_year: FiscalYear
    ) -> tuple[OpenItemCreditRefundReversalCandidate, ...]:
        """Liefert noch nicht zurückgenommene Erstattungen zur Auswahl."""
        return self._repository.list_candidates(
            company_id=company_id,
            fiscal_year=fiscal_year,
        )

    def reverse_refund(
        self,
        *,
        company_id: UUID,
        fiscal_year: FiscalYear,
        refund_id: UUID,
        reason: str,
        booking_date: date | None,
    ) -> OpenItemCreditRefundReversal:
        return self._repository.reverse_refund(
            company_id=company_id,
            fiscal_year=fiscal_year,
            refund_id=refund_id,
            reason=reason,
            booking_date=booking_date,
        )

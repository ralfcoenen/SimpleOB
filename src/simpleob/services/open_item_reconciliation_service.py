"""Anwendungsservice für die lesende OP-Abstimmung."""

from datetime import date
from uuid import UUID

from simpleob.database.open_item_reconciliation_repository import (
    OpenItemReconciliationRepository,
)
from simpleob.domain.open_item_reconciliation import OpenItemReconciliationReport


class OpenItemReconciliationService:
    """Stellt stichtagsbezogene OP-Abstimmungen bereit, ohne Daten zu ändern."""

    def __init__(self, repository: OpenItemReconciliationRepository) -> None:
        self._repository = repository

    def reconcile(self, *, company_id: UUID, as_of_date: date) -> OpenItemReconciliationReport:
        return self._repository.reconcile(company_id=company_id, as_of_date=as_of_date)

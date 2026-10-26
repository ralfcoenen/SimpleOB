"""Lesende Anwendungsfunktionen für OP-Übersichten."""

from uuid import UUID

from simpleob.database.open_item_overview_repository import (
    OpenItemOverviewRepository,
)
from simpleob.domain.open_item_overview import (
    OpenItemOverviewDetail,
    OpenItemOverviewReport,
)


class OpenItemOverviewService:
    """Stellt aktuelle mandantenbezogene OP-Daten lesend bereit."""

    def __init__(self, repository: OpenItemOverviewRepository) -> None:
        self._repository = repository

    def list_items(
        self,
        *,
        company_id: UUID,
        include_settled: bool = False,
    ) -> OpenItemOverviewReport:
        return self._repository.list_items(
            company_id=company_id,
            include_settled=include_settled,
        )

    def get_detail(
        self,
        *,
        company_id: UUID,
        open_item_id: UUID,
    ) -> OpenItemOverviewDetail | None:
        return self._repository.get_detail(
            company_id=company_id,
            open_item_id=open_item_id,
        )

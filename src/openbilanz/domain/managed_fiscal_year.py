"""Verwaltetes Geschäftsjahr."""

from dataclasses import dataclass

from openbilanz.domain.fiscal_year import FiscalYear
from openbilanz.domain.fiscal_year_status import FiscalYearStatus


@dataclass(frozen=True, slots=True)
class ManagedFiscalYear:
    """Verbindet ein Geschäftsjahr mit seinem Bearbeitungsstatus."""

    fiscal_year: FiscalYear
    status: FiscalYearStatus
    opening_source: FiscalYear | None = None

    def __post_init__(self) -> None:
        if not isinstance(
            self.fiscal_year,
            FiscalYear,
        ):
            raise TypeError(
                "fiscal_year must be a FiscalYear"
            )

        if not isinstance(
            self.status,
            FiscalYearStatus,
        ):
            raise TypeError(
                "status must be a FiscalYearStatus"
            )

        if (
            self.opening_source is not None
            and not isinstance(
                self.opening_source,
                FiscalYear,
            )
        ):
            raise TypeError(
                "opening_source must be a FiscalYear or None"
            )

    @property
    def is_open(self) -> bool:
        """Prüft, ob das Geschäftsjahr offen ist."""

        return self.status is FiscalYearStatus.OPEN

    @property
    def is_closed(self) -> bool:
        """Prüft, ob das Geschäftsjahr abgeschlossen ist."""

        return self.status is FiscalYearStatus.CLOSED

    @property
    def has_opening_source(self) -> bool:
        """Prüft, ob das Geschäftsjahr aus einem Vorjahr eröffnet wurde."""

        return self.opening_source is not None

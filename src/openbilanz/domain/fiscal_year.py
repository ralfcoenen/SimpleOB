from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class FiscalYear:
    """Ein fachlich definierter Geschäftsjahreszeitraum."""

    start_date: date
    end_date: date

    def __post_init__(self) -> None:
        if not isinstance(self.start_date, date):
            raise TypeError("start_date must be a date")

        if not isinstance(self.end_date, date):
            raise TypeError("end_date must be a date")

        if self.start_date > self.end_date:
            raise ValueError("start_date must not be after end_date")

    def contains(self, value: date) -> bool:
        """Prüft, ob ein Datum innerhalb des Geschäftsjahres liegt."""

        if not isinstance(value, date):
            raise TypeError("value must be a date")

        return self.start_date <= value <= self.end_date

    @property
    def duration_days(self) -> int:
        """Anzahl der Tage des Geschäftsjahres einschließlich Start- und Endtag."""
        return (self.end_date - self.start_date).days + 1

    @property
    def calendar_years(self) -> tuple[int, ...]:
        """Alle vom Geschäftsjahr berührten Kalenderjahre."""
        return tuple(range(self.start_date.year, self.end_date.year + 1))

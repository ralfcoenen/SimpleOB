"""Zeitliche Zuordnung des Vorsteuerabzugs."""

from dataclasses import dataclass, field
from datetime import date
from uuid import UUID, uuid4


@dataclass(frozen=True, slots=True)
class VatInputTiming:
    """Ordnet einer Eingangsrechnung die relevanten Vorsteuerdaten zu."""

    booking_id: UUID
    service_date: date
    invoice_received_date: date
    timing_id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        if not isinstance(self.booking_id, UUID):
            raise TypeError("booking_id must be a UUID")

        if not isinstance(self.service_date, date):
            raise TypeError("service_date must be a date")

        if not isinstance(self.invoice_received_date, date):
            raise TypeError("invoice_received_date must be a date")

        if not isinstance(self.timing_id, UUID):
            raise TypeError("timing_id must be a UUID")

    @property
    def deductible_date(self) -> date:
        """Liefert den frühesten Tag, an dem beide Voraussetzungen vorliegen."""

        return max(
            self.service_date,
            self.invoice_received_date,
        )

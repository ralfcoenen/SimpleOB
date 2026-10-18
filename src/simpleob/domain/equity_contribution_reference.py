"""Fachliche Referenz auf eine als Einlage gekennzeichnete Buchungszeile."""

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class EquityContributionReference:
    """Referenziert eine Buchungszeile, die eine BVV-Einlage darstellt."""

    booking_id: UUID
    booking_line_position: int

    def __post_init__(self) -> None:
        if not isinstance(self.booking_id, UUID):
            raise TypeError("booking_id must be a UUID")

        if not isinstance(self.booking_line_position, int):
            raise TypeError(
                "booking_line_position must be an int"
            )

        if self.booking_line_position < 0:
            raise ValueError(
                "booking_line_position must not be negative"
            )

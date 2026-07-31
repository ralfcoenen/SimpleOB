"""Journal für das Domänenmodell von OpenBilanz-UG."""

from collections.abc import Iterator
from dataclasses import dataclass, field

from openbilanz.domain.booking import Booking
from openbilanz.domain.errors import DuplicateBookingError


@dataclass(slots=True)
class Journal:
    """
    Repräsentiert eine chronologische Sammlung von Buchungen.

    Das Journal kann kontrolliert um neue Buchungen erweitert werden.
    Bereits enthaltene Buchungen werden weder verändert noch entfernt.

    Die Buchungen werden in der Reihenfolge gespeichert, in der sie dem
    Journal hinzugefügt wurden.
    
    
    """

    _bookings: tuple[Booking, ...] = field(
        default_factory=tuple,
        init=False,
        repr=False,
    )

    @property
    def bookings(self) -> tuple[Booking, ...]:
        """
        Gibt alle Buchungen in Einfügereihenfolge zurück.

        Returns:
            Ein unveränderliches Tupel mit allen enthaltenen Buchungen.
        """
        return self._bookings
    
    def add(self, booking: Booking) -> None:
        """
        Fügt dem Journal eine Buchung hinzu.

        Args:
            booking:
                Die hinzuzufügende Buchung.

        Raises:
            TypeError:
                Wenn booking kein Booking-Objekt ist.
            ValueError:
                Wenn die Buchungs-ID bereits im Journal vorhanden ist.
            DuplicateBookingError:
                Wenn die Buchungs-ID bereits im Journal enthalten ist.
        """
        
        if not isinstance(booking, Booking):
            raise TypeError("booking muss ein Booking-Objekt sein.")

        if any(
            existing_booking.booking_id == booking.booking_id
            for existing_booking in self._bookings
        ):
            raise DuplicateBookingError(
                "Die Buchungs-ID ist bereits im Journal enthalten."
            )

        self._bookings += (booking,)
                

    def __len__(self) -> int:
        """Gibt die Anzahl der enthaltenen Buchungen zurück."""
        return len(self._bookings)

    def __iter__(self) -> Iterator[Booking]:
        """Ermöglicht die Iteration über alle Buchungen."""
        return iter(self._bookings)

    def __contains__(self, booking: object) -> bool:
        """Prüft, ob eine Buchung im Journal enthalten ist."""
        return booking in self._bookings

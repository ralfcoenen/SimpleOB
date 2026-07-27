"""Journal für das Domänenmodell von OpenBilanz-UG."""

from collections.abc import Iterator
from datetime import date
from uuid import UUID

from openbilanz.domain.booking import Booking


class Journal:
    """
    Verwaltet eine geordnete Sammlung gültiger Buchungen.

    Buchungen werden in der Reihenfolge gespeichert, in der sie dem
    Journal hinzugefügt wurden. Doppelte Buchungs-IDs sind nicht zulässig.
    """

    def __init__(self) -> None:
        """Erzeugt ein leeres Journal."""
        self._bookings: list[Booking] = []
        self._bookings_by_id: dict[UUID, Booking] = {}

    @property
    def bookings(self) -> tuple[Booking, ...]:
        """Gibt alle Buchungen als unveränderliches Tupel zurück."""
        return tuple(self._bookings)

    def add(self, booking: Booking) -> None:
        """
        Fügt dem Journal eine Buchung hinzu.

        Raises:
            TypeError:
                Wenn kein Booking-Objekt übergeben wurde.
            ValueError:
                Wenn die Buchungs-ID bereits im Journal vorhanden ist.
        """
        if not isinstance(booking, Booking):
            raise TypeError(
                "Dem Journal können nur Booking-Objekte hinzugefügt werden."
            )

        if booking.booking_id in self._bookings_by_id:
            raise ValueError(
                "Eine Buchung mit dieser Buchungs-ID "
                "ist bereits im Journal vorhanden."
            )

        self._bookings.append(booking)
        self._bookings_by_id[booking.booking_id] = booking

    def get(self, booking_id: UUID) -> Booking:
        """
        Gibt eine Buchung anhand ihrer Buchungs-ID zurück.

        Raises:
            TypeError:
                Wenn die Buchungs-ID keine UUID ist.
            KeyError:
                Wenn keine Buchung mit dieser ID existiert.
        """
        if not isinstance(booking_id, UUID):
            raise TypeError("Die Buchungs-ID muss eine UUID sein.")

        try:
            return self._bookings_by_id[booking_id]
        except KeyError as exc:
            raise KeyError(
                f"Keine Buchung mit der ID {booking_id} gefunden."
            ) from exc

    def find_by_voucher_no(
        self,
        voucher_no: str,
    ) -> tuple[Booking, ...]:
        """
        Sucht Buchungen anhand ihrer Belegnummer.

        Die Suche berücksichtigt Groß- und Kleinschreibung nicht.
        """
        normalized_voucher_no = self._normalize_search_text(
            voucher_no,
            field_name="Belegnummer",
        )

        return tuple(
            booking
            for booking in self._bookings
            if booking.voucher_no is not None
            and booking.voucher_no.casefold()
            == normalized_voucher_no.casefold()
        )

    def find_by_date(
        self,
        booking_date: date,
    ) -> tuple[Booking, ...]:
        """Gibt alle Buchungen eines bestimmten Datums zurück."""
        booking_date = self._validate_date(
            booking_date,
            field_name="Buchungsdatum",
        )

        return tuple(
            booking
            for booking in self._bookings
            if booking.booking_date == booking_date
        )

    def find_by_date_range(
        self,
        start_date: date,
        end_date: date,
    ) -> tuple[Booking, ...]:
        """
        Gibt alle Buchungen innerhalb eines Datumsbereichs zurück.

        Anfangs- und Enddatum sind einschließlich.
        """
        start_date = self._validate_date(
            start_date,
            field_name="Anfangsdatum",
        )
        end_date = self._validate_date(
            end_date,
            field_name="Enddatum",
        )

        if start_date > end_date:
            raise ValueError(
                "Das Anfangsdatum darf nicht nach dem Enddatum liegen."
            )

        return tuple(
            booking
            for booking in self._bookings
            if start_date <= booking.booking_date <= end_date
        )

    def __contains__(self, booking_id: object) -> bool:
        """Prüft, ob eine Buchungs-ID im Journal vorhanden ist."""
        return booking_id in self._bookings_by_id

    def __iter__(self) -> Iterator[Booking]:
        """Ermöglicht die Iteration über alle Buchungen."""
        return iter(self._bookings)

    def __len__(self) -> int:
        """Gibt die Anzahl der Buchungen zurück."""
        return len(self._bookings)

    def __bool__(self) -> bool:
        """Gibt zurück, ob das Journal Buchungen enthält."""
        return bool(self._bookings)

    @staticmethod
    def _validate_date(
        value: date,
        *,
        field_name: str,
    ) -> date:
        """Prüft einen Datumswert."""
        if not isinstance(value, date):
            raise TypeError(f"{field_name} muss ein Datum sein.")

        return value

    @staticmethod
    def _normalize_search_text(
        value: str,
        *,
        field_name: str,
    ) -> str:
        """Prüft und normalisiert einen Suchtext."""
        if not isinstance(value, str):
            raise TypeError(f"{field_name} muss eine Zeichenkette sein.")

        normalized_value = value.strip()

        if not normalized_value:
            raise ValueError(f"{field_name} darf nicht leer sein.")

        return normalized_value
    
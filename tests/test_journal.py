"""Unit-Tests für das Journal."""

import pytest

from openbilanz.domain.journal import Journal
from tests.factories import create_booking


class TestJournal:
    """Tests für das Journal."""

    def test_create_empty_journal(self) -> None:
        """Ein neues Journal ist zunächst leer."""
        journal = Journal()

        assert len(journal) == 0
        assert journal.bookings == ()

    def test_add_booking(self) -> None:
        """Eine Buchung kann dem Journal hinzugefügt werden."""
        booking = create_booking()
        journal = Journal()

        journal.add(booking)

        assert len(journal) == 1
        assert journal.bookings == (booking,)

    def test_add_multiple_bookings(self) -> None:
        """Mehrere Buchungen werden gespeichert."""
        booking1 = create_booking()
        booking2 = create_booking()
        journal = Journal()

        journal.add(booking1)
        journal.add(booking2)

        assert len(journal) == 2
        assert journal.bookings == (
            booking1,
            booking2,
        )

    def test_iteration_returns_bookings(self) -> None:
        """Das Journal ist über seine Buchungen iterierbar."""
        booking1 = create_booking()
        booking2 = create_booking()
        journal = Journal()

        journal.add(booking1)
        journal.add(booking2)

        assert list(journal) == [
            booking1,
            booking2,
        ]

    def test_contains_booking(self) -> None:
        """Enthaltene Buchungen können mit 'in' geprüft werden."""
        booking = create_booking()
        journal = Journal()

        journal.add(booking)

        assert booking in journal

    def test_contains_returns_false_for_missing_booking(self) -> None:
        """Nicht enthaltene Buchungen werden nicht gefunden."""
        stored_booking = create_booking()
        missing_booking = create_booking()
        journal = Journal()

        journal.add(stored_booking)

        assert missing_booking not in journal

    def test_bookings_returns_tuple(self) -> None:
        """Die öffentliche Buchungssammlung ist ein Tupel."""
        booking = create_booking()
        journal = Journal()

        journal.add(booking)

        assert isinstance(journal.bookings, tuple)

    def test_preserves_insertion_order(self) -> None:
        """Die Einfügereihenfolge der Buchungen bleibt erhalten."""
        booking1 = create_booking()
        booking2 = create_booking()
        booking3 = create_booking()
        journal = Journal()

        journal.add(booking1)
        journal.add(booking2)
        journal.add(booking3)

        assert journal.bookings == (
            booking1,
            booking2,
            booking3,
        )

    @pytest.mark.parametrize(
        "invalid_booking",
        [
            None,
            object(),
            123,
            "booking",
        ],
    )
    def test_add_rejects_invalid_object(
        self,
        invalid_booking: object,
    ) -> None:
        """Nur Booking-Objekte dürfen hinzugefügt werden."""
        journal = Journal()

        with pytest.raises(
            TypeError,
            match="booking muss eine Booking sein",
        ):
            journal.add(invalid_booking)

    def test_rejected_object_does_not_modify_journal(self) -> None:
        """Ein abgelehntes Objekt verändert das Journal nicht."""
        booking = create_booking()
        journal = Journal()
        journal.add(booking)

        original_bookings = journal.bookings

        with pytest.raises(TypeError):
            journal.add(None)

        assert journal.bookings == original_bookings
        assert len(journal) == 1
        
        
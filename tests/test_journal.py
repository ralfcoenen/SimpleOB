from openbilanz.domain.journal import Journal
from tests.factories import create_booking
import pytest


def test_new_journal_is_empty() -> None:
    """
    Ein neu erzeugtes Journal enthält keine Buchungen.
    """
    journal = Journal()

    assert len(journal.bookings) == 0
    

def test_add_booking_to_journal() -> None:
    """
    Eine Buchung kann in das Journal aufgenommen werden.
    """
    journal = Journal()
    booking = create_booking()

    journal.add(booking)

    assert len(journal.bookings) == 1
    assert journal.bookings[0] == booking
    
    
def test_journal_preserves_booking_order() -> None:
    """
    Das Journal gibt Buchungen in der Reihenfolge zurück,
    in der sie aufgenommen wurden.
    """
    journal = Journal()

    first_booking = create_booking()
    second_booking = create_booking()

    journal.add(first_booking)
    journal.add(second_booking)

    assert journal.bookings == (
        first_booking,
        second_booking,
    )

def test_journal_is_iterable() -> None:
    """
    Über die Buchungen eines Journals kann iteriert werden.
    """
    journal = Journal()
    first_booking = create_booking()
    second_booking = create_booking()

    journal.add(first_booking)
    journal.add(second_booking)

    assert list(journal) == [
        first_booking,
        second_booking,
    ]
    
  
def test_journal_rejects_non_booking_objects() -> None:
    """
    Das Journal akzeptiert ausschließlich Buchungen.
    """
    journal = Journal()

    with pytest.raises(TypeError):
        journal.add("keine Buchung")
        
def test_journal_rejects_duplicate_booking_id() -> None:
    """
    Eine Buchungs-ID darf im Journal nur einmal vorkommen.
    """
    journal = Journal()
    booking = create_booking()

    journal.add(booking)

    with pytest.raises(
        ValueError,
        match="Buchungs-ID ist bereits im Journal enthalten",
    ):
        journal.add(booking)
        

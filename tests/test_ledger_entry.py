"""Unit-Tests für LedgerEntry."""

from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from openbilanz.accounting.ledger_entry import LedgerEntry
from openbilanz.domain.entry_side import EntrySide


def test_ledger_entry_rejects_empty_account_number() -> None:
    """Eine leere Kontonummer ist nicht zulässig."""
    with pytest.raises(
        ValueError,
        match="Die Kontonummer darf nicht leer sein",
    ):
        LedgerEntry(
            booking_id=uuid4(),
            booking_date=date(2026, 1, 15),
            voucher_no="RE-2026-001",
            description="Ausgangsrechnung",
            account_number="   ",
            side=EntrySide.DEBIT,
            amount=Decimal("100.00"),
        )

def test_ledger_entry_stores_account_movement() -> None:
    """Ein Hauptbucheintrag speichert alle Daten einer Kontenbewegung."""
    booking_id = uuid4()

    entry = LedgerEntry(
        booking_id=booking_id,
        booking_date=date(2026, 1, 15),
        voucher_no="RE-2026-001",
        description="Ausgangsrechnung",
        account_number="1200",
        side=EntrySide.DEBIT,
        amount=Decimal("100.00"),
    )

    assert entry.booking_id == booking_id
    assert isinstance(entry.booking_id, UUID)
    assert entry.booking_date == date(2026, 1, 15)
    assert entry.voucher_no == "RE-2026-001"
    assert entry.description == "Ausgangsrechnung"
    assert entry.account_number == "1200"
    assert entry.side is EntrySide.DEBIT
    assert entry.amount == Decimal("100.00")
    
def test_ledger_entry_normalizes_account_number_and_amount() -> None:
    """Kontonummer und Geldbetrag werden normalisiert."""
    entry = LedgerEntry(
        booking_id=uuid4(),
        booking_date=date(2026, 1, 15),
        voucher_no="RE-2026-001",
        description="Ausgangsrechnung",
        account_number=" 1200 ",
        side=EntrySide.DEBIT,
        amount=Decimal("100.123"),
    )

    assert entry.account_number == "1200"
    assert entry.amount == Decimal("100.12")  
    
@pytest.mark.parametrize(
    "amount",
    [
        Decimal("0.00"),
        Decimal("-0.01"),
    ],
)
def test_ledger_entry_rejects_non_positive_amount(
    amount: Decimal,
) -> None:
    """Der Buchungsbetrag muss größer als 0,00 sein."""
    with pytest.raises(
        ValueError,
        match="Ein Buchungsbetrag muss größer als 0,00 sein",
    ):
        LedgerEntry(
            booking_id=uuid4(),
            booking_date=date(2026, 1, 15),
            voucher_no="RE-2026-001",
            description="Ausgangsrechnung",
            account_number="1200",
            side=EntrySide.DEBIT,
            amount=amount,
        )
@pytest.mark.parametrize(
    "booking_id",
    [
        "not-a-uuid",
        123,
        None,
    ],
)
def test_ledger_entry_rejects_invalid_booking_id(
    booking_id: object,
) -> None:
    """Die Buchungs-ID muss eine UUID sein."""
    with pytest.raises(
        TypeError,
        match="Die Buchungs-ID muss eine UUID sein",
    ):
        LedgerEntry(
            booking_id=booking_id,  # type: ignore[arg-type]
            booking_date=date(2026, 1, 15),
            voucher_no="RE-2026-001",
            description="Ausgangsrechnung",
            account_number="1200",
            side=EntrySide.DEBIT,
            amount=Decimal("100.00"),
        )
        
@pytest.mark.parametrize(
    "booking_date",
    [
        "2026-01-15",
        20260115,
        None,
    ],
)
def test_ledger_entry_rejects_invalid_booking_date(
    booking_date: object,
) -> None:
    """Das Buchungsdatum muss ein date-Objekt sein."""
    with pytest.raises(
        TypeError,
        match="Das Buchungsdatum muss ein date-Objekt sein",
    ):
        LedgerEntry(
            booking_id=uuid4(),
            booking_date=booking_date,  # type: ignore[arg-type]
            voucher_no="RE-2026-001",
            description="Ausgangsrechnung",
            account_number="1200",
            side=EntrySide.DEBIT,
            amount=Decimal("100.00"),
        )
        
@pytest.mark.parametrize(
    "side",
    [
        "DEBIT",
        "CREDIT",
        1,
        None,
    ],
)
def test_ledger_entry_rejects_invalid_side(
    side: object,
    ) -> None:
    """Die Buchungsseite muss ein EntrySide-Wert sein."""
    with pytest.raises(
        TypeError,
        match="Die Buchungsseite muss ein EntrySide-Wert sein",
    ):
        LedgerEntry(
            booking_id=uuid4(),
            booking_date=date(2026, 1, 15),
            voucher_no="RE-2026-001",
            description="Ausgangsrechnung",
            account_number="1200",
            side=side,  # type: ignore[arg-type]
            amount=Decimal("100.00"),
        )

@pytest.mark.parametrize(
    "voucher_no",
    [
        "",
        "   ",
    ],
)
def test_ledger_entry_rejects_empty_voucher_no(
    voucher_no: str,
) -> None:
    """Die Belegnummer darf nicht leer sein."""
    with pytest.raises(
        ValueError,
        match="Die Belegnummer darf nicht leer sein",
    ):
        LedgerEntry(
            booking_id=uuid4(),
            booking_date=date(2026, 1, 15),
            voucher_no=voucher_no,
            description="Ausgangsrechnung",
            account_number="1200",
            side=EntrySide.DEBIT,
            amount=Decimal("100.00"),
        )

@pytest.mark.parametrize(
    "description",
    [
        "",
        "   ",
    ],
)
def test_ledger_entry_rejects_empty_description(
    description: str,
) -> None:
    """Der Buchungstext darf nicht leer sein."""
    with pytest.raises(
        ValueError,
        match="Der Buchungstext darf nicht leer sein",
    ):
        LedgerEntry(
            booking_id=uuid4(),
            booking_date=date(2026, 1, 15),
            voucher_no="RE-2026-001",
            description=description,
            account_number="1200",
            side=EntrySide.DEBIT,
            amount=Decimal("100.00"),
        )

def test_ledger_entry_normalizes_voucher_no_and_description() -> None:
    """Belegnummer und Buchungstext werden von Leerzeichen bereinigt."""
    entry = LedgerEntry(
        booking_id=uuid4(),
        booking_date=date(2026, 1, 15),
        voucher_no=" RE-2026-001 ",
        description=" Ausgangsrechnung ",
        account_number="1200",
        side=EntrySide.DEBIT,
        amount=Decimal("100.00"),
    )

    assert entry.voucher_no == "RE-2026-001"
    assert entry.description == "Ausgangsrechnung"
    
@pytest.mark.parametrize(
    ("field_name", "field_value", "expected_message"),
    [
        (
            "voucher_no",
            None,
            "Die Belegnummer muss eine Zeichenkette sein",
        ),
        (
            "description",
            123,
            "Der Buchungstext muss eine Zeichenkette sein",
        ),
        (
            "account_number",
            None,
            "Die Kontonummer muss eine Zeichenkette sein",
        ),
    ],
)
def test_ledger_entry_rejects_invalid_text_types(
    field_name: str,
    field_value: object,
    expected_message: str,
    ) -> None:
    """Textfelder müssen Zeichenketten sein."""
    values = {
        "booking_id": uuid4(),
        "booking_date": date(2026, 1, 15),
        "voucher_no": "RE-2026-001",
        "description": "Ausgangsrechnung",
        "account_number": "1200",
        "side": EntrySide.DEBIT,
        "amount": Decimal("100.00"),
    }
    values[field_name] = field_value

    with pytest.raises(TypeError, match=expected_message):
        LedgerEntry(**values)  # type: ignore[arg-type]
    

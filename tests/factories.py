"""
Factory-Funktionen für Unit-Tests.

Dieses Modul stellt Hilfsfunktionen zum Erzeugen häufig verwendeter
Testobjekte bereit. Dadurch bleiben die Unit-Tests kurz, lesbar und
verwenden konsistente Testdaten.
"""

from decimal import Decimal
from datetime import date

from openbilanz.domain.booking import Booking
from openbilanz.domain.booking_line import BookingLine
from openbilanz.domain.entry_side import EntrySide


def create_booking_line(
    account_no: str = "1200",
    side: EntrySide = EntrySide.DEBIT,
    amount: Decimal = Decimal("100.00"),
) -> BookingLine:
    """
    Erzeugt eine einzelne Buchungszeile.
    """
    return BookingLine(
        account_no=account_no,
        side=side,
        amount=amount,
    )


def create_booking() -> Booking:
    """
    Erzeugt einen einfachen ausgeglichenen Buchungssatz.

    Soll:
        1200 Bank       100,00

    Haben:
        8400 Erlöse     100,00
    """
    return Booking(
        booking_date=date(2026, 1, 1),
        voucher_no="TEST-001",
        description="Testbuchung",
        lines=(
            create_booking_line(
                account_no="1200",
                side=EntrySide.DEBIT,
            ),
            create_booking_line(
                account_no="8400",
                side=EntrySide.CREDIT,
            ),
        ),
    )
    
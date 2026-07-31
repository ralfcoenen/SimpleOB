"""
Factory-Funktionen für Unit-Tests.

Dieses Modul stellt Hilfsfunktionen zum Erzeugen häufig verwendeter
Testobjekte bereit. Dadurch bleiben die Unit-Tests kurz, lesbar und
verwenden konsistente Testdaten.
"""

from datetime import date
from decimal import Decimal

from openbilanz.domain.account import Account
from openbilanz.domain.account_type import AccountType
from openbilanz.domain.booking import Booking
from openbilanz.domain.booking_line import BookingLine
from openbilanz.domain.chart_of_accounts import ChartOfAccounts
from openbilanz.domain.entry_side import EntrySide
from openbilanz.domain.template_account import TemplateAccount


def create_booking_line(
    account_number: str = "1200",
    side: EntrySide = EntrySide.DEBIT,
    amount: Decimal = Decimal("100.00"),
) -> BookingLine:
    """
    Erzeugt eine einzelne Buchungszeile.
    """
    return BookingLine(
        account_number=account_number,
        side=side,
        amount=amount,
    )

def create_account(
    account_number: str = "1200",
    name: str = "Bank",
    account_type: AccountType = AccountType.ASSET,
    is_active: bool = True,
) -> Account:
    """
    Erzeugt ein Konto für Unit-Tests.
    """
    return Account(
        template=TemplateAccount(
            account_number=account_number,
            name=name,
            account_type=account_type,
        ),
        is_active=is_active,
    )


def create_chart_of_accounts() -> ChartOfAccounts:
    """
    Erzeugt einen Kontenplan mit den Konten der Standard-Testbuchung.
    """
    return ChartOfAccounts(
        accounts=(
            create_account(
                account_number="1200",
                name="Bank",
                account_type=AccountType.ASSET,
            ),
            create_account(
                account_number="8400",
                name="Erlöse",
                account_type=AccountType.REVENUE,
            ),
        )
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
                account_number="1200",
                side=EntrySide.DEBIT,
            ),
            create_booking_line(
                account_number="8400",
                side=EntrySide.CREDIT,
            ),
        ),
    )

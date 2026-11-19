import pytest

from simpleob.domain.account import Account
from simpleob.domain.account_type import AccountType
from simpleob.domain.booking import Booking
from simpleob.domain.booking_line import BookingLine
from simpleob.domain.booking_type import BookingType
from simpleob.domain.booking_validator import BookingValidator
from simpleob.domain.chart_of_accounts import ChartOfAccounts
from simpleob.domain.entry_side import EntrySide
from simpleob.domain.errors import (
    UnknownAccountError,
)
from simpleob.domain.person_account_role import PersonAccountRole
from simpleob.domain.template_account import TemplateAccount
from tests.factories import (
    create_booking,
    create_booking_line,
    create_chart_of_accounts,
)


def test_accepts_booking_when_all_accounts_exist() -> None:
    """
    Eine Buchung mit ausschließlich vorhandenen Konten
    wird akzeptiert.
    """
    chart = create_chart_of_accounts()
    booking = create_booking()

    validator = BookingValidator(chart)

    validator.validate(booking)


def test_rejects_booking_with_unknown_account() -> None:
    """
    Eine Buchung mit einem unbekannten Konto
    wird abgelehnt.
    """
    chart = create_chart_of_accounts()
    booking = create_booking()

    unknown_line = create_booking_line(
        account_number="9999",
        side=booking.lines[0].side,
        amount=booking.lines[0].amount,
    )

    booking_with_unknown_account = Booking(
        booking_date=booking.booking_date,
        voucher_no=booking.voucher_no,
        description=booking.description,
        lines=(
            unknown_line,
            booking.lines[1],
        ),
    )

    validator = BookingValidator(chart)

    with pytest.raises(UnknownAccountError):
        validator.validate(booking_with_unknown_account)


def test_inactive_person_account_is_rejected_for_regular_booking_but_allowed_for_reversal():
    person_account = Account(
        TemplateAccount("10000", "Inaktiver Kunde", AccountType.ASSET),
        is_active=False,
        person_account_role=PersonAccountRole.DEBITOR,
    )
    other_account = Account(
        TemplateAccount("9000", "Gegenkonto", AccountType.EQUITY),
    )
    validator = BookingValidator(
        ChartOfAccounts(accounts=(person_account, other_account))
    )
    regular = Booking(
        booking_date=create_booking().booking_date,
        lines=(
            BookingLine("10000", EntrySide.DEBIT, "25.00"),
            BookingLine("9000", EntrySide.CREDIT, "25.00"),
        ),
    )
    with pytest.raises(ValueError, match="inaktive Personenkonten"):
        validator.validate(regular)

    reversal = Booking(
        booking_date=create_booking().booking_date,
        booking_type=BookingType.REVERSAL,
        reversal_of_booking_id=regular.booking_id,
        lines=(
            BookingLine("10000", EntrySide.CREDIT, "25.00"),
            BookingLine("9000", EntrySide.DEBIT, "25.00"),
        ),
    )
    validator.validate(reversal)
        

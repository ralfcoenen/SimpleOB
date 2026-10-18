from datetime import date
from decimal import Decimal

import pytest

from simpleob.domain.account import Account
from simpleob.domain.account_type import AccountType
from simpleob.domain.opening_balance import OpeningBalance
from simpleob.domain.opening_balance_item import OpeningBalanceItem
from simpleob.domain.template_account import TemplateAccount
from simpleob.services.opening_balance_service import (
    OpeningBalanceService,
)


def _account(
    number: str,
    name: str,
    account_type: AccountType,
) -> Account:
    return Account(
        template=TemplateAccount(
            account_number=number,
            name=name,
            account_type=account_type,
        ),
    )


def test_creates_opening_bookings_for_balanced_opening_balance() -> None:
    bank = _account(
        "1200",
        "Bank",
        AccountType.ASSET,
    )
    equity = _account(
        "1800",
        "Eigenkapital",
        AccountType.EQUITY,
    )

    opening_balance = OpeningBalance(
        items=(
            OpeningBalanceItem(
                account=bank,
                amount=Decimal("25000.00"),
            ),
            OpeningBalanceItem(
                account=equity,
                amount=Decimal("25000.00"),
            ),
        ),
    )

    service = OpeningBalanceService(
        opening_balance_account_number="9000",
    )

    bookings = service.create_bookings(
        opening_balance=opening_balance,
        booking_date=date(2026, 1, 1),
    )

    assert len(bookings) == 2

    bank_booking = bookings[0]

    assert bank_booking.debit_lines[0].account_number == "1200"
    assert bank_booking.credit_lines[0].account_number == "9000"
    assert bank_booking.debit_total == Decimal("25000.00")

    equity_booking = bookings[1]

    assert equity_booking.debit_lines[0].account_number == "9000"
    assert equity_booking.credit_lines[0].account_number == "1800"
    assert equity_booking.debit_total == Decimal("25000.00")


def test_creates_opening_bookings_for_assets_liabilities_and_equity() -> None:
    bank = _account(
        "1200",
        "Bank",
        AccountType.ASSET,
    )
    liabilities = _account(
        "1600",
        "Verbindlichkeiten",
        AccountType.LIABILITY,
    )
    equity = _account(
        "1800",
        "Eigenkapital",
        AccountType.EQUITY,
    )

    opening_balance = OpeningBalance(
        items=(
            OpeningBalanceItem(
                account=bank,
                amount=Decimal("25000.00"),
            ),
            OpeningBalanceItem(
                account=liabilities,
                amount=Decimal("8000.00"),
            ),
            OpeningBalanceItem(
                account=equity,
                amount=Decimal("17000.00"),
            ),
        ),
    )

    bookings = OpeningBalanceService(
        opening_balance_account_number="9000",
    ).create_bookings(
        opening_balance=opening_balance,
        booking_date=date(2026, 1, 1),
    )

    assert len(bookings) == 3

    assert bookings[0].debit_lines[0].account_number == "1200"
    assert bookings[0].credit_lines[0].account_number == "9000"
    assert bookings[0].debit_total == Decimal("25000.00")

    assert bookings[1].debit_lines[0].account_number == "9000"
    assert bookings[1].credit_lines[0].account_number == "1600"
    assert bookings[1].debit_total == Decimal("8000.00")

    assert bookings[2].debit_lines[0].account_number == "9000"
    assert bookings[2].credit_lines[0].account_number == "1800"
    assert bookings[2].debit_total == Decimal("17000.00")


def test_rejects_unbalanced_opening_balance() -> None:
    bank = _account(
        "1200",
        "Bank",
        AccountType.ASSET,
    )
    equity = _account(
        "1800",
        "Eigenkapital",
        AccountType.EQUITY,
    )

    opening_balance = OpeningBalance(
        items=(
            OpeningBalanceItem(
                account=bank,
                amount=Decimal("25000.00"),
            ),
            OpeningBalanceItem(
                account=equity,
                amount=Decimal("17000.00"),
            ),
        ),
    )

    service = OpeningBalanceService(
        opening_balance_account_number="9000",
    )

    with pytest.raises(
        ValueError,
        match="ausgeglichen",
    ):
        service.create_bookings(
            opening_balance=opening_balance,
            booking_date=date(2026, 1, 1),
        )

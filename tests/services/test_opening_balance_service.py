from datetime import date
from decimal import Decimal

import pytest

from simpleob.domain.account import Account
from simpleob.domain.account_type import AccountType
from simpleob.domain.entry_side import EntrySide
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
                side=EntrySide.DEBIT,
            ),
            OpeningBalanceItem(
                account=equity,
                amount=Decimal("25000.00"),
                side=EntrySide.CREDIT,
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
                side=EntrySide.DEBIT,
            ),
            OpeningBalanceItem(
                account=liabilities,
                amount=Decimal("8000.00"),
                side=EntrySide.CREDIT,
            ),
            OpeningBalanceItem(
                account=equity,
                amount=Decimal("17000.00"),
                side=EntrySide.CREDIT,
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
                side=EntrySide.DEBIT,
            ),
            OpeningBalanceItem(
                account=equity,
                amount=Decimal("17000.00"),
                side=EntrySide.CREDIT,
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


def test_debit_loss_carryforward_on_2970_is_posted_against_9000() -> None:
    carryforward = _account(
        "2970",
        "Gewinn-/Verlustvortrag",
        AccountType.EQUITY,
    )
    opening_balance = OpeningBalance(
        items=(
            OpeningBalanceItem(
                account=carryforward,
                amount=Decimal("4000.00"),
                side=EntrySide.DEBIT,
            ),
            OpeningBalanceItem(
                account=_account("1200", "Bank", AccountType.ASSET),
                amount=Decimal("4000.00"),
                side=EntrySide.CREDIT,
            ),
        ),
    )

    bookings = OpeningBalanceService(
        opening_balance_account_number="9000",
    ).create_bookings(
        opening_balance=opening_balance,
        booking_date=date(2026, 1, 1),
    )

    assert bookings[0].debit_lines[0].account_number == "2970"
    assert bookings[0].credit_lines[0].account_number == "9000"


def test_reverses_direction_for_asset_credit_and_liability_debit() -> None:
    asset = _account("1200", "Bank", AccountType.ASSET)
    liability = _account("3300", "Verbindlichkeit", AccountType.LIABILITY)
    opening_balance = OpeningBalance(
        items=(
            OpeningBalanceItem(asset, Decimal("500.00"), EntrySide.CREDIT),
            OpeningBalanceItem(liability, Decimal("500.00"), EntrySide.DEBIT),
        ),
    )

    bookings = OpeningBalanceService(
        opening_balance_account_number="9000",
    ).create_bookings(
        opening_balance=opening_balance,
        booking_date=date(2026, 1, 1),
    )

    assert bookings[0].debit_lines[0].account_number == "9000"
    assert bookings[0].credit_lines[0].account_number == "1200"
    assert bookings[1].debit_lines[0].account_number == "3300"
    assert bookings[1].credit_lines[0].account_number == "9000"


def test_zero_saldos_do_not_create_bookings() -> None:
    opening_balance = OpeningBalance(
        items=(
            OpeningBalanceItem(
                _account("1200", "Bank", AccountType.ASSET),
                Decimal("0.00"),
                EntrySide.DEBIT,
            ),
        ),
    )

    bookings = OpeningBalanceService(
        opening_balance_account_number="9000",
    ).create_bookings(
        opening_balance=opening_balance,
        booking_date=date(2026, 1, 1),
    )

    assert bookings == ()


def test_opening_balance_account_cannot_be_opened_as_a_regular_account() -> None:
    opening_balance = OpeningBalance(
        items=(
            OpeningBalanceItem(
                _account("9000", "Saldenvortrag", AccountType.EQUITY),
                Decimal("100.00"),
                EntrySide.DEBIT,
            ),
            OpeningBalanceItem(
                _account("1200", "Bank", AccountType.ASSET),
                Decimal("100.00"),
                EntrySide.CREDIT,
            ),
        ),
    )

    with pytest.raises(ValueError, match="Eröffnungsbilanzkonto"):
        OpeningBalanceService(
            opening_balance_account_number="9000",
        ).create_bookings(
            opening_balance=opening_balance,
            booking_date=date(2026, 1, 1),
        )

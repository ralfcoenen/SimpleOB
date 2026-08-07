from datetime import date
from decimal import Decimal

from openbilanz.accounting.ledger import Ledger
from openbilanz.domain.account import Account
from openbilanz.domain.account_type import AccountType
from openbilanz.domain.journal import Journal
from openbilanz.domain.opening_balance import OpeningBalance
from openbilanz.domain.opening_balance_item import OpeningBalanceItem
from openbilanz.domain.template_account import TemplateAccount
from openbilanz.services.opening_balance_service import (
    OpeningBalanceService,
)
from openbilanz.services.posting_service import PostingService


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


def test_posts_opening_balance_to_journal_and_ledger() -> None:
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

    journal = Journal()
    ledger = Ledger()
    posting_service = PostingService()

    for booking in bookings:
        posting_service.post_booking(
            booking=booking,
            ledger=ledger,
            journal=journal,
        )

    assert len(journal) == 3

    assert ledger.get_account("1200").debit_balance == Decimal("25000.00")
    assert ledger.get_account("1600").credit_balance == Decimal("8000.00")
    assert ledger.get_account("1800").credit_balance == Decimal("17000.00")

    assert ledger.get_account("9000").debit == Decimal("25000.00")
    assert ledger.get_account("9000").credit == Decimal("25000.00")

    assert ledger.is_balanced

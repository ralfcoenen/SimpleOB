from decimal import Decimal

from openbilanz.domain.account import Account
from openbilanz.domain.account_type import AccountType
from openbilanz.domain.opening_balance import OpeningBalance
from openbilanz.domain.opening_balance_item import OpeningBalanceItem
from openbilanz.domain.template_account import TemplateAccount

def test_empty_opening_balance_is_balanced() -> None:
    balance = OpeningBalance(
        items=(),
    )

    assert balance.total_assets == Decimal("0.00")
    assert balance.total_liabilities_and_equity == Decimal("0.00")
    assert balance.is_balanced
    


def test_asset_item_increases_total_assets() -> None:
    account = Account(
        template=TemplateAccount(
            account_number="1200",
            name="Bank",
            account_type=AccountType.ASSET,
        ),
    )

    balance = OpeningBalance(
        items=(
            OpeningBalanceItem(
                account=account,
                amount=Decimal("25000.00"),
            ),
        ),
    )

    assert balance.total_assets == Decimal("25000.00")
    assert balance.total_liabilities_and_equity == Decimal("0.00")
    assert not balance.is_balanced

def test_liability_item_increases_total_liabilities_and_equity() -> None:
    account = Account(
        template=TemplateAccount(
            account_number="1600",
            name="Verbindlichkeiten",
            account_type=AccountType.LIABILITY,
        ),
    )

    balance = OpeningBalance(
        items=(
            OpeningBalanceItem(
                account=account,
                amount=Decimal("8000.00"),
            ),
        ),
    )

    assert balance.total_assets == Decimal("0.00")
    assert (
        balance.total_liabilities_and_equity
        == Decimal("8000.00")
    )
    assert not balance.is_balanced
    
def test_opening_balance_is_balanced_with_equal_totals() -> None:
    bank = Account(
        template=TemplateAccount(
            account_number="1200",
            name="Bank",
            account_type=AccountType.ASSET,
        ),
    )
    liabilities = Account(
        template=TemplateAccount(
            account_number="1600",
            name="Verbindlichkeiten",
            account_type=AccountType.LIABILITY,
        ),
    )
    equity = Account(
        template=TemplateAccount(
            account_number="1800",
            name="Eigenkapital",
            account_type=AccountType.EQUITY,
        ),
    )

    balance = OpeningBalance(
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

    assert balance.total_assets == Decimal("25000.00")
    assert (
        balance.total_liabilities_and_equity
        == Decimal("25000.00")
    )
    assert balance.is_balanced

from openbilanz.domain.account import Account
from openbilanz.domain.account_type import AccountType
from openbilanz.domain.template_account import TemplateAccount
from openbilanz.ui.opening_balance_dialog import OpeningBalanceDialog


def _account(
    number: str,
    name: str,
    account_type: AccountType,
    *,
    is_active: bool = True,
) -> Account:
    return Account(
        template=TemplateAccount(
            account_number=number,
            name=name,
            account_type=account_type,
        ),
        is_active=is_active,
    )


def test_filters_accounts_for_opening_balance() -> None:
    accounts = (
        _account("1200", "Bank", AccountType.ASSET),
        _account("1600", "Verbindlichkeiten", AccountType.LIABILITY),
        _account("1800", "Eigenkapital", AccountType.EQUITY),
        _account("8020", "Jahresüberschuss", AccountType.EQUITY),
        _account("8021", "Jahresfehlbetrag", AccountType.EQUITY),
        _account("8990", "GuV-Sammelkonto", AccountType.EQUITY),
        _account("4000", "Umsatzerlöse", AccountType.REVENUE),
        _account(
            "1210",
            "Inaktives Bankkonto",
            AccountType.ASSET,
            is_active=False,
        ),
    )

    filtered = OpeningBalanceDialog._filter_accounts(
        accounts=accounts,
        excluded_account_numbers={
            "8990",
            "8020",
            "8021",
        },
    )

    assert tuple(account.number for account in filtered) == (
        "1200",
        "1600",
        "1800",
    )

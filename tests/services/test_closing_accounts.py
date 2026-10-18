from dataclasses import is_dataclass

from simpleob.services.closing_accounts import ClosingAccounts


def test_closing_accounts_contains_required_accounts() -> None:
    accounts = ClosingAccounts(
        income_summary_account="8990",
        profit_account="8020",
        loss_account="8021",
    )

    assert is_dataclass(accounts)
    assert accounts.income_summary_account == "8990"
    assert accounts.profit_account == "8020"
    assert accounts.loss_account == "8021"
    
    
from openbilanz.domain import Account, AccountType, ChartOfAccounts, TemplateAccount
import pytest

from openbilanz.domain import (
    Account,
    AccountType,
    ChartOfAccounts,
    ChartOfAccountsTemplate,
    TemplateAccount,
)


def test_creates_chart_of_accounts_from_template() -> None:
    template = ChartOfAccountsTemplate(
        name="SKR03",
        accounts=(
            TemplateAccount(
                account_number="1000",
                name="Kasse",
                account_type=AccountType.ASSET,
            ),
            TemplateAccount(
                account_number="1200",
                name="Bank",
                account_type=AccountType.ASSET,
            ),
        ),
    )
    
    chart = ChartOfAccounts.from_template(template)

    assert len(chart) == 2

    assert chart.accounts[0].number == "1000"
    assert chart.accounts[0].name == "Kasse"

    assert chart.accounts[1].number == "1200"
    assert chart.accounts[1].name == "Bank"


def make_account(
    account_number: str = "1200",
    name: str = "Bank",
    account_type: AccountType = AccountType.ASSET,
) -> Account:
    template = TemplateAccount(
        account_number=account_number,
        name=name,
        account_type=account_type,
    )

    return Account(template=template)


class TestConstruction:
    def test_creates_empty_chart_of_accounts(self) -> None:
        chart = ChartOfAccounts()

        assert len(chart) == 0

    def test_creates_chart_with_accounts(self) -> None:
        accounts = (
            make_account("1000", "Kasse"),
            make_account("1200", "Bank"),
        )

        chart = ChartOfAccounts(accounts=accounts)

        assert len(chart) == 2
        
class TestValidation:
    def test_rejects_non_account_objects(self) -> None:
        with pytest.raises(
            TypeError,
            match="all accounts must be Account instances",
        ):
            ChartOfAccounts(
                accounts=("1200",),  # type: ignore[arg-type]
            )
        
        
import pytest

from openbilanz.domain import (
    Account,
    AccountType,
    ChartOfAccounts,
    ChartOfAccountsTemplate,
    TemplateAccount,
)


def make_account(
    number: str = "1000",
    name: str = "Kasse",
    account_type: AccountType = AccountType.ASSET,
) -> Account:
    return Account(
        template=TemplateAccount(
            account_number=number,
            name=name,
            account_type=account_type,
        )
    )


def test_creates_empty_chart_of_accounts() -> None:
    chart = ChartOfAccounts()

    assert len(chart) == 0


def test_creates_chart_with_accounts() -> None:
    account1 = make_account("1000", "Kasse")
    account2 = make_account("1200", "Bank")

    chart = ChartOfAccounts(accounts=(account1, account2))

    assert len(chart) == 2


def test_rejects_non_account_objects() -> None:
    with pytest.raises(TypeError, match="all accounts must be Account instances"):
        ChartOfAccounts(accounts=("not an account",))


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


def test_accounts_created_from_template_are_active() -> None:
    template = ChartOfAccountsTemplate(
        name="SKR03",
        accounts=(
            TemplateAccount(
                account_number="1000",
                name="Kasse",
                account_type=AccountType.ASSET,
            ),
        ),
    )

    chart = ChartOfAccounts.from_template(template)

    assert chart.accounts[0].is_active is True
    
def test_returns_account_by_number() -> None:
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

    account = chart.account("1200")

    assert account.number == "1200"
    assert account.name == "Bank"
   
def test_returns_account_by_number() -> None:
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

    account = chart.account("1200")

    assert account.number == "1200"
    assert account.name == "Bank"
    

def test_raises_key_error_for_unknown_account_number() -> None:
    template = ChartOfAccountsTemplate(
        name="SKR03",
        accounts=(
            TemplateAccount(
                account_number="1000",
                name="Kasse",
                account_type=AccountType.ASSET,
            ),
        ),
    )

    chart = ChartOfAccounts.from_template(template)

    with pytest.raises(KeyError, match="1200"):
        chart.account("1200")
        
     

import pytest

from openbilanz.domain import (
    Account,
    AccountType,
    ChartOfAccounts,
    ChartOfAccountsTemplate,
    TemplateAccount,
    UnknownAccountError,
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


def make_chart(*accounts: Account) -> ChartOfAccounts:
    return ChartOfAccounts(accounts=accounts)


def test_creates_empty_chart_of_accounts() -> None:
    chart = make_chart()

    assert len(chart) == 0


def test_creates_chart_with_accounts() -> None:
    account1 = make_account(
        number="1000",
        name="Kasse",
    )
    account2 = make_account(
        number="1200",
        name="Bank",
    )

    chart = make_chart(account1, account2)

    assert len(chart) == 2


def test_rejects_non_account_objects() -> None:
    with pytest.raises(
        TypeError,
        match="all accounts must be Account instances",
    ):
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
    account1 = make_account(
        number="1000",
        name="Kasse",
    )
    account2 = make_account(
        number="1200",
        name="Bank",
    )

    chart = make_chart(account1, account2)

    account = chart.account("1200")

    assert account.number == "1200"
    assert account.name == "Bank"


def test_raises_unknown_account_error_for_unknown_account_number() -> None:
    account = make_account(
        number="1000",
        name="Kasse",
    )

    chart = make_chart(account)

    with pytest.raises(UnknownAccountError, match="1200"):
        chart.account("1200")


def test_rejects_duplicate_account_numbers() -> None:
    account1 = make_account(
        number="1000",
        name="Kasse",
    )
    account2 = make_account(
        number="1000",
        name="Nebenkasse",
    )

    with pytest.raises(
        ValueError,
        match="duplicate account number: 1000",
    ):
        make_chart(account1, account2)


def test_is_iterable() -> None:
    account1 = make_account(
        number="1000",
        name="Kasse",
    )
    account2 = make_account(
        number="1200",
        name="Bank",
    )

    chart = make_chart(account1, account2)

    account_numbers = [
        account.number
        for account in chart
    ]

    assert account_numbers == [
        "1000",
        "1200",
    ]


def test_contains_account() -> None:
    account = make_account(
        number="1000",
        name="Kasse",
    )

    chart = make_chart(account)

    assert account in chart


def test_does_not_contain_unknown_account() -> None:
    account = make_account(
        number="1000",
        name="Kasse",
    )
    unknown_account = make_account(
        number="1200",
        name="Bank",
    )

    chart = make_chart(account)

    assert unknown_account not in chart



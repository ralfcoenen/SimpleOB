import pytest

from openbilanz.domain import Account, AccountType, TemplateAccount


def make_template() -> TemplateAccount:
    return TemplateAccount(
        account_number="1200",
        name="Bank",
        account_type=AccountType.ASSET,
    )


class TestAccountType:
    def test_contains_asset_type(self) -> None:
        assert AccountType.ASSET.name == "ASSET"

    def test_contains_liability_type(self) -> None:
        assert AccountType.LIABILITY.name == "LIABILITY"

    def test_contains_expense_type(self) -> None:
        assert AccountType.EXPENSE.name == "EXPENSE"

    def test_contains_revenue_type(self) -> None:
        assert AccountType.REVENUE.name == "REVENUE"


class TestAccount:
    def test_create_account(self) -> None:
        account = Account(template=make_template())

        assert account.number == "1200"
        assert account.name == "Bank"
        assert account.account_type is AccountType.ASSET

    def test_account_exposes_template(self) -> None:
        template = make_template()

        account = Account(template=template)

        assert account.template is template

    def test_account_is_active_by_default(self) -> None:
        account = Account(template=make_template())

        assert account.is_active is True

    def test_account_can_be_inactive(self) -> None:
        account = Account(
            template=make_template(),
            is_active=False,
        )

        assert account.is_active is False

    def test_account_is_immutable(self) -> None:
        account = Account(template=make_template())

        with pytest.raises(AttributeError):
            account.is_active = False  # type: ignore[misc]

    def test_accounts_with_equal_values_are_equal(self) -> None:
        first = Account(template=make_template())
        second = Account(template=make_template())

        assert first == second

    def test_accounts_with_different_templates_are_not_equal(self) -> None:
        first = Account(template=make_template())
        second = Account(
            template=TemplateAccount(
                account_number="1210",
                name="Bank 2",
                account_type=AccountType.ASSET,
            )
        )

        assert first != second

    def test_accounts_with_different_active_states_are_not_equal(self) -> None:
        first = Account(
            template=make_template(),
            is_active=True,
        )
        second = Account(
            template=make_template(),
            is_active=False,
        )

        assert first != second

    def test_account_is_hashable(self) -> None:
        account = Account(template=make_template())

        accounts = {account}

        assert account in accounts

    def test_equal_accounts_have_equal_hashes(self) -> None:
        first = Account(template=make_template())
        second = Account(template=make_template())

        assert hash(first) == hash(second)

    @pytest.mark.parametrize(
        "invalid_template",
        [
            None,
            "1200",
            1200,
            True,
            [],
            {},
        ],
    )
    def test_rejects_invalid_template(
        self,
        invalid_template: object,
    ) -> None:
        with pytest.raises(
            TypeError,
            match="template must be a TemplateAccount",
        ):
            Account(
                template=invalid_template,  # type: ignore[arg-type]
            )

    @pytest.mark.parametrize(
        "invalid_is_active",
        [
            None,
            0,
            1,
            "True",
            [],
            {},
        ],
    )
    def test_rejects_non_boolean_is_active(
        self,
        invalid_is_active: object,
    ) -> None:
        with pytest.raises(
            TypeError,
            match="is_active must be a bool",
        ):
            Account(
                template=make_template(),
                is_active=invalid_is_active,  # type: ignore[arg-type]
            )

    def test_str_returns_number_and_name(self) -> None:
        account = Account(template=make_template())

        assert str(account) == "1200 – Bank"

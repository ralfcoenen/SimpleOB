import pytest

from openbilanz.domain.account import Account, AccountType


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
        account = Account(
            number="1200",
            name="Bank",
            account_type=AccountType.ASSET,
        )

        assert account.number == "1200"
        assert account.name == "Bank"
        assert account.account_type is AccountType.ASSET

    def test_account_is_immutable(self) -> None:
        account = Account(
            number="1200",
            name="Bank",
            account_type=AccountType.ASSET,
        )

        with pytest.raises(AttributeError):
            account.name = "Geschäftskonto"  # type: ignore[misc]

    def test_accounts_with_equal_values_are_equal(self) -> None:
        first = Account(
            number="1200",
            name="Bank",
            account_type=AccountType.ASSET,
        )
        second = Account(
            number="1200",
            name="Bank",
            account_type=AccountType.ASSET,
        )

        assert first == second

    def test_accounts_with_different_numbers_are_not_equal(self) -> None:
        first = Account(
            number="1200",
            name="Bank",
            account_type=AccountType.ASSET,
        )
        second = Account(
            number="1210",
            name="Bank",
            account_type=AccountType.ASSET,
        )

        assert first != second

    def test_account_is_hashable(self) -> None:
        account = Account(
            number="1200",
            name="Bank",
            account_type=AccountType.ASSET,
        )

        accounts = {account}

        assert account in accounts

    @pytest.mark.parametrize(
        "number",
        [
            "",
            " ",
            "   ",
        ],
    )
    def test_rejects_empty_account_number(self, number: str) -> None:
        with pytest.raises(
            ValueError,
            match="account number must not be empty",
        ):
            Account(
                number=number,
                name="Bank",
                account_type=AccountType.ASSET,
            )

    def test_rejects_non_string_account_number(self) -> None:
        with pytest.raises(
            TypeError,
            match="account number must be a string",
        ):
            Account(
                number=1200,  # type: ignore[arg-type]
                name="Bank",
                account_type=AccountType.ASSET,
            )

    @pytest.mark.parametrize(
        "name",
        [
            "",
            " ",
            "   ",
        ],
    )
    def test_rejects_empty_account_name(self, name: str) -> None:
        with pytest.raises(
            ValueError,
            match="account name must not be empty",
        ):
            Account(
                number="1200",
                name=name,
                account_type=AccountType.ASSET,
            )

    def test_rejects_non_string_account_name(self) -> None:
        with pytest.raises(
            TypeError,
            match="account name must be a string",
        ):
            Account(
                number="1200",
                name=123,  # type: ignore[arg-type]
                account_type=AccountType.ASSET,
            )

    def test_rejects_invalid_account_type(self) -> None:
        with pytest.raises(
            TypeError,
            match="account_type must be an AccountType",
        ):
            Account(
                number="1200",
                name="Bank",
                account_type="ASSET",  # type: ignore[arg-type]
            )

    def test_str_returns_number_and_name(self) -> None:
        account = Account(
            number="1200",
            name="Bank",
            account_type=AccountType.ASSET,
        )

        assert str(account) == "1200 – Bank"

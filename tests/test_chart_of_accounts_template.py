from collections.abc import Iterator

import pytest

from openbilanz.domain import AccountType, ChartOfAccountsTemplate, TemplateAccount


def create_account(
    account_number: str = "1200",
    name: str = "Bank",
    account_type: AccountType = AccountType.ASSET,
) -> TemplateAccount:
    return TemplateAccount(
        account_number=account_number,
        name=name,
        account_type=account_type,
    )


def create_template() -> ChartOfAccountsTemplate:
    return ChartOfAccountsTemplate(
        name="SKR03",
        accounts=(
            create_account("1000", "Kasse"),
            create_account("1200", "Bank"),
            create_account("8400", "Erlöse 19 % USt"),
        ),
    )


class TestConstruction:
    def test_creates_template_with_name_and_accounts(self):
        accounts = (
            create_account("1000", "Kasse"),
            create_account("1200", "Bank"),
        )

        template = ChartOfAccountsTemplate(
            name="SKR03",
            accounts=accounts,
        )

        assert template.name == "SKR03"
        assert template.accounts == accounts

    def test_accepts_empty_accounts_tuple(self):
        template = ChartOfAccountsTemplate(
            name="Leerer Kontenrahmen",
            accounts=(),
        )

        assert template.accounts == ()
        assert len(template) == 0

    def test_is_immutable(self):
        template = create_template()

        with pytest.raises(AttributeError):
            template.name = "SKR04"  # type: ignore[misc]

    def test_accounts_are_immutable(self):
        template = create_template()

        with pytest.raises(TypeError):
            template.accounts[0] = create_account()  # type: ignore[index]


class TestNameValidation:
    @pytest.mark.parametrize(
        "value",
        [
            None,
            123,
            [],
            object(),
        ],
    )
    def test_rejects_non_string_name(self, value):
        with pytest.raises(TypeError, match="name"):
            ChartOfAccountsTemplate(
                name=value,  # type: ignore[arg-type]
                accounts=(),
            )

    @pytest.mark.parametrize(
        "value",
        [
            "",
            " ",
            "\t",
            "\n",
        ],
    )
    def test_rejects_blank_name(self, value: str):
        with pytest.raises(ValueError, match="name"):
            ChartOfAccountsTemplate(
                name=value,
                accounts=(),
            )

    @pytest.mark.parametrize(
        "value",
        [
            " SKR03",
            "SKR03 ",
            " SKR03 ",
            "\tSKR03",
            "SKR03\n",
        ],
    )
    def test_rejects_surrounding_whitespace(self, value: str):
        with pytest.raises(ValueError, match="name"):
            ChartOfAccountsTemplate(
                name=value,
                accounts=(),
            )


class TestAccountsValidation:
    @pytest.mark.parametrize(
        "value",
        [
            None,
            [],
            {},
            set(),
            "not accounts",
        ],
    )
    def test_rejects_non_tuple_accounts(self, value):
        with pytest.raises(TypeError, match="accounts"):
            ChartOfAccountsTemplate(
                name="SKR03",
                accounts=value,  # type: ignore[arg-type]
            )

    def test_rejects_non_template_account_elements(self):
        with pytest.raises(TypeError, match="TemplateAccount"):
            ChartOfAccountsTemplate(
                name="SKR03",
                accounts=(
                    create_account(),
                    object(),  # type: ignore[arg-type]
                ),
            )

    def test_rejects_duplicate_account_numbers(self):
        with pytest.raises(ValueError, match="duplicate"):
            ChartOfAccountsTemplate(
                name="SKR03",
                accounts=(
                    create_account("1200", "Bank"),
                    create_account("1200", "Bankkonto"),
                ),
            )

    def test_allows_different_account_numbers(self):
        template = ChartOfAccountsTemplate(
            name="SKR03",
            accounts=(
                create_account("1000", "Kasse"),
                create_account("1200", "Bank"),
            ),
        )

        assert len(template) == 2


class TestCollectionBehaviour:
    def test_len_returns_number_of_accounts(self):
        template = create_template()

        assert len(template) == 3

    def test_iter_returns_accounts_in_original_order(self):
        template = create_template()

        assert tuple(template) == template.accounts

    def test_iter_returns_iterator(self):
        template = create_template()

        assert isinstance(iter(template), Iterator)

    def test_contains_returns_true_for_existing_account_number(self):
        template = create_template()

        assert template.contains("1200") is True

    def test_contains_returns_false_for_unknown_account_number(self):
        template = create_template()

        assert template.contains("9999") is False

    def test_in_operator_returns_true_for_existing_account_number(self):
        template = create_template()

        assert "1200" in template

    def test_in_operator_returns_false_for_unknown_account_number(self):
        template = create_template()

        assert "9999" not in template


class TestGet:
    def test_get_returns_matching_account(self):
        template = create_template()

        account = template.get("1200")

        assert account == create_account("1200", "Bank")

    def test_get_raises_key_error_for_unknown_account_number(self):
        template = create_template()

        with pytest.raises(KeyError, match="9999"):
            template.get("9999")

    def test_get_returns_original_account_instance(self):
        account = create_account("1200", "Bank")
        template = ChartOfAccountsTemplate(
            name="SKR03",
            accounts=(account,),
        )

        assert template.get("1200") is account


class TestValueObjectBehaviour:
    def test_equal_templates_are_equal(self):
        first = create_template()
        second = create_template()

        assert first == second

    def test_templates_with_different_names_are_not_equal(self):
        accounts = create_template().accounts

        first = ChartOfAccountsTemplate(
            name="SKR03",
            accounts=accounts,
        )
        second = ChartOfAccountsTemplate(
            name="SKR04",
            accounts=accounts,
        )

        assert first != second

    def test_templates_with_different_accounts_are_not_equal(self):
        first = ChartOfAccountsTemplate(
            name="SKR03",
            accounts=(create_account("1200", "Bank"),),
        )
        second = ChartOfAccountsTemplate(
            name="SKR03",
            accounts=(create_account("1000", "Kasse"),),
        )

        assert first != second

    def test_templates_with_different_account_order_are_not_equal(self):
        first_account = create_account("1000", "Kasse")
        second_account = create_account("1200", "Bank")

        first = ChartOfAccountsTemplate(
            name="SKR03",
            accounts=(first_account, second_account),
        )
        second = ChartOfAccountsTemplate(
            name="SKR03",
            accounts=(second_account, first_account),
        )

        assert first != second

    def test_template_is_hashable(self):
        template = create_template()

        assert {template} == {template}

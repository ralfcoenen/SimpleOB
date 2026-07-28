import pytest

from openbilanz.domain import TemplateAccount


def test_template_account_can_be_created() -> None:
    account = TemplateAccount(
        account_number="8400",
        name="Erlöse 19 % USt",
    )

    assert account.account_number == "8400"
    assert account.name == "Erlöse 19 % USt"


@pytest.mark.parametrize(
    "invalid_account_number",
    [
        None,
        8400,
        8400.0,
        True,
        [],
        {},
    ],
)
def test_account_number_must_be_a_string(
    invalid_account_number: object,
) -> None:
    with pytest.raises(TypeError):
        TemplateAccount(
            account_number=invalid_account_number,  # type: ignore[arg-type]
            name="Erlöse 19 % USt",
        )


@pytest.mark.parametrize(
    "invalid_account_number",
    [
        "",
        " ",
        "   ",
    ],
)
def test_account_number_must_not_be_blank(
    invalid_account_number: str,
) -> None:
    with pytest.raises(ValueError):
        TemplateAccount(
            account_number=invalid_account_number,
            name="Erlöse 19 % USt",
        )


@pytest.mark.parametrize(
    "invalid_account_number",
    [
        " 8400",
        "8400 ",
        " 8400 ",
    ],
)
def test_account_number_must_not_have_surrounding_whitespace(
    invalid_account_number: str,
) -> None:
    with pytest.raises(ValueError):
        TemplateAccount(
            account_number=invalid_account_number,
            name="Erlöse 19 % USt",
        )


@pytest.mark.parametrize(
    "invalid_account_number",
    [
        "84 00",
        "84-00",
        "A840",
        "840A",
        "84.00",
    ],
)
def test_account_number_must_contain_digits_only(
    invalid_account_number: str,
) -> None:
    with pytest.raises(ValueError):
        TemplateAccount(
            account_number=invalid_account_number,
            name="Erlöse 19 % USt",
        )


@pytest.mark.parametrize(
    "invalid_name",
    [
        None,
        8400,
        19.0,
        True,
        [],
        {},
    ],
)
def test_name_must_be_a_string(
    invalid_name: object,
) -> None:
    with pytest.raises(TypeError):
        TemplateAccount(
            account_number="8400",
            name=invalid_name,  # type: ignore[arg-type]
        )


@pytest.mark.parametrize(
    "invalid_name",
    [
        "",
        " ",
        "   ",
    ],
)
def test_name_must_not_be_blank(
    invalid_name: str,
) -> None:
    with pytest.raises(ValueError):
        TemplateAccount(
            account_number="8400",
            name=invalid_name,
        )


@pytest.mark.parametrize(
    "invalid_name",
    [
        " Erlöse 19 % USt",
        "Erlöse 19 % USt ",
        " Erlöse 19 % USt ",
    ],
)
def test_name_must_not_have_surrounding_whitespace(
    invalid_name: str,
) -> None:
    with pytest.raises(ValueError):
        TemplateAccount(
            account_number="8400",
            name=invalid_name,
        )


def test_template_account_is_immutable() -> None:
    account = TemplateAccount(
        account_number="8400",
        name="Erlöse 19 % USt",
    )

    with pytest.raises(AttributeError):
        account.name = "Andere Bezeichnung"  # type: ignore[misc]


def test_equal_template_accounts_are_equal() -> None:
    first = TemplateAccount(
        account_number="8400",
        name="Erlöse 19 % USt",
    )
    second = TemplateAccount(
        account_number="8400",
        name="Erlöse 19 % USt",
    )

    assert first == second


def test_different_account_numbers_are_not_equal() -> None:
    first = TemplateAccount(
        account_number="8400",
        name="Erlöse 19 % USt",
    )
    second = TemplateAccount(
        account_number="8300",
        name="Erlöse 19 % USt",
    )

    assert first != second


def test_different_names_are_not_equal() -> None:
    first = TemplateAccount(
        account_number="8400",
        name="Erlöse 19 % USt",
    )
    second = TemplateAccount(
        account_number="8400",
        name="Umsatzerlöse",
    )

    assert first != second


def test_equal_template_accounts_have_equal_hashes() -> None:
    first = TemplateAccount(
        account_number="8400",
        name="Erlöse 19 % USt",
    )
    second = TemplateAccount(
        account_number="8400",
        name="Erlöse 19 % USt",
    )

    assert hash(first) == hash(second)


def test_template_account_can_be_used_in_a_set() -> None:
    account = TemplateAccount(
        account_number="8400",
        name="Erlöse 19 % USt",
    )

    accounts = {account}

    assert account in accounts

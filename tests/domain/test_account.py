from simpleob.domain.account import Account
from simpleob.domain.account_type import AccountType
from simpleob.domain.template_account import TemplateAccount


def test_account_exposes_number_name_and_type_from_template() -> None:
    template = TemplateAccount(
        account_number="1200",
        name="Bank",
        account_type=AccountType.ASSET,
    )

    account = Account(template=template)

    assert account.number == "1200"
    assert account.name == "Bank"
    assert account.account_type is AccountType.ASSET
    assert account.is_active is True
    
    
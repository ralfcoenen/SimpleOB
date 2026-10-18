from simpleob.domain.account_type import AccountType


def test_account_type_contains_all_business_account_categories() -> None:
    assert AccountType.ASSET.name == "ASSET"
    assert AccountType.LIABILITY.name == "LIABILITY"
    assert AccountType.EQUITY.name == "EQUITY"
    assert AccountType.REVENUE.name == "REVENUE"
    assert AccountType.EXPENSE.name == "EXPENSE"
    
    
    
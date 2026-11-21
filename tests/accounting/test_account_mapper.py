from decimal import Decimal

import pytest

from simpleob.accounting.account_balance import AccountBalance
from simpleob.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
from simpleob.accounting.hgb_financial_statement_position_provider import (
    HgbFinancialStatementPositionProvider,
)
from simpleob.accounting.mapper import AccountMapper
from simpleob.domain.account_mapping_rule import AccountMappingRule
from simpleob.domain.account_type import AccountType
from simpleob.domain.chart_of_accounts_template import (
    ChartOfAccountsTemplate,
)
from simpleob.domain.template_account import TemplateAccount
from simpleob.hgb.balance_sheet_structure import (
    create_hgb_balance_sheet_structure,
)


def test_maps_debit_balance_to_debit_position() -> None:
    bank_position = FinancialStatementPosition(
        code="HGB.266.AKTIVA.B.IV",
        name="Kassenbestand und Guthaben bei Kreditinstituten",
    )

    account = TemplateAccount(
        account_number="1200",
        name="Bank",
        account_type=AccountType.ASSET,
    )

    rule = AccountMappingRule(
        account_number="1200",
        debit_position=bank_position,
        credit_position=None,
    )

    chart_of_accounts = ChartOfAccountsTemplate(
        name="SKR03",
        accounts=(account,),
        account_mapping_rules=(rule,),
    )

    balance = AccountBalance(
        account_number="1200",
        debit=Decimal("1250.00"),
        credit=Decimal("250.00"),
    )

    mapper = AccountMapper(chart_of_accounts)

    position, amount = mapper.map_balance(balance)

    assert position is bank_position
    assert amount == Decimal("1000.00")


def test_maps_credit_balance_to_credit_position() -> None:
    credit_position = FinancialStatementPosition(
        code="HGB.266.PASSIVA.C.2",
        name="Verbindlichkeiten gegenüber Kreditinstituten",
    )

    account = TemplateAccount(
        account_number="1200",
        name="Bank",
        account_type=AccountType.ASSET,
    )

    rule = AccountMappingRule(
        account_number="1200",
        debit_position=None,
        credit_position=credit_position,
    )

    chart = ChartOfAccountsTemplate(
        name="SKR03",
        accounts=(account,),
        account_mapping_rules=(rule,),
    )

    balance = AccountBalance(
        account_number="1200",
        debit=Decimal("250.00"),
        credit=Decimal("1250.00"),
    )

    mapper = AccountMapper(chart)

    position, amount = mapper.map_balance(balance)

    assert position is credit_position
    assert amount == Decimal("1000.00")


def test_maps_configured_bank_credit_balance_to_bank_liabilities() -> None:
    assets, liabilities = create_hgb_balance_sheet_structure()
    provider = HgbFinancialStatementPositionProvider((assets, liabilities))
    bank_asset = provider.get("HGB.266.AKTIVA.B.IV")
    bank_liability = provider.get("HGB.266.PASSIVA.C.2")
    account = TemplateAccount(
        account_number="98765",
        name="Freies Zahlungskonto",
        account_type=AccountType.ASSET,
    )
    chart = ChartOfAccountsTemplate(
        "Freier Kontenrahmen",
        (account,),
        account_mapping_rules=(
            AccountMappingRule("98765", bank_asset, None),
        ),
    )

    mapper = AccountMapper(
        chart,
        bank_account_numbers=frozenset({"98765"}),
    )
    position, amount = mapper.map_balance(
        AccountBalance("98765", debit=Decimal("25.00"), credit=Decimal("125.00"))
    )

    assert position.code == bank_liability.code == "HGB.266.PASSIVA.C.2"
    assert amount == Decimal("100.00")


def test_maps_configured_bank_debit_balance_to_existing_asset_position() -> None:
    account = TemplateAccount(
        account_number="198765",
        name="Zahlungskonto",
        account_type=AccountType.ASSET,
    )
    bank_position = FinancialStatementPosition(
        "HGB.266.AKTIVA.B.IV", "Bankguthaben"
    )
    chart = ChartOfAccountsTemplate(
        "Freier Kontenrahmen",
        (account,),
        account_mapping_rules=(
            AccountMappingRule("198765", bank_position, None),
        ),
    )

    position, amount = AccountMapper(
        chart,
        bank_account_numbers=frozenset({"198765"}),
    ).map_balance(AccountBalance("198765", debit=Decimal("100.00")))

    assert position.code == "HGB.266.AKTIVA.B.IV"
    assert amount == Decimal("100.00")


def test_zero_balance_bank_has_no_hgb_disclosure() -> None:
    account = TemplateAccount("198765", "Zahlungskonto", AccountType.ASSET)
    chart = ChartOfAccountsTemplate("Freier Kontenrahmen", (account,))

    with pytest.raises(ValueError, match="Nullsaldo"):
        AccountMapper(
            chart,
            bank_account_numbers=frozenset({"198765"}),
        ).map_balance(AccountBalance("198765"))


@pytest.mark.parametrize(
    ("debit_code", "credit_code", "side"),
    (
        ("HGB.266.AKTIVA.A.II.3", None, "Soll"),
        ("HGB.266.AKTIVA.B.IV", "HGB.266.PASSIVA.C.8", "Haben"),
    ),
)
def test_rejects_individual_hgb_mapping_conflicting_with_bank_role(
    debit_code: str | None,
    credit_code: str | None,
    side: str,
) -> None:
    assets, liabilities = create_hgb_balance_sheet_structure()
    provider = HgbFinancialStatementPositionProvider((assets, liabilities))
    account = TemplateAccount("198765", "Bank", AccountType.ASSET)
    rule = AccountMappingRule(
        "198765",
        provider.get(debit_code) if debit_code else None,
        provider.get(credit_code) if credit_code else None,
    )
    chart = ChartOfAccountsTemplate(
        "Konflikt",
        (account,),
        account_mapping_rules=(rule,),
    )

    with pytest.raises(ValueError, match=f"Konflikt bei Bankkonto 198765.*HGB-{side}zuordnung"):
        AccountMapper(chart, bank_account_numbers=frozenset({"198765"}))


def test_bank_role_update_changes_mapping_and_non_bank_asset_stays_unchanged() -> None:
    account = TemplateAccount("198765", "Zahlungskonto", AccountType.ASSET)
    cash = TemplateAccount("1234", "Kasse", AccountType.ASSET)
    receivable = TemplateAccount("2345", "Sonstige Forderung", AccountType.ASSET)
    bank_position = FinancialStatementPosition(
        "HGB.266.AKTIVA.B.IV", "Bankguthaben"
    )
    chart = ChartOfAccountsTemplate(
        "Freier Kontenrahmen",
        (account, cash, receivable),
        account_mapping_rules=(
            AccountMappingRule("198765", bank_position, None),
            AccountMappingRule("1234", bank_position, None),
            AccountMappingRule("2345", bank_position, None),
        ),
    )
    mapper = AccountMapper(chart)
    negative_bank = AccountBalance("198765", credit=Decimal("50.00"))
    before = (negative_bank.debit, negative_bank.credit, negative_bank.balance)

    with pytest.raises(ValueError, match="no credit position defined for account 198765"):
        mapper.map_balance(negative_bank)

    mapper.update_bank_account_numbers(frozenset({"198765"}))
    position, amount = mapper.map_balance(negative_bank)
    assert position.code == "HGB.266.PASSIVA.C.2"
    assert amount == Decimal("50.00")
    assert (negative_bank.debit, negative_bank.credit, negative_bank.balance) == before

    with pytest.raises(ValueError, match="no credit position defined for account 1234"):
        mapper.map_balance(AccountBalance("1234", credit=Decimal("50.00")))
    with pytest.raises(ValueError, match="no credit position defined for account 2345"):
        mapper.map_balance(AccountBalance("2345", credit=Decimal("50.00")))


def test_maps_debit_balance_of_liability_to_explicit_debit_position() -> None:
    debit_position = FinancialStatementPosition(
        code="HGB.266.PASSIVA.C.8",
        name="Sonstige Verbindlichkeiten",
    )
    account = TemplateAccount(
        account_number="3300",
        name="Lieferantenverbindlichkeiten",
        account_type=AccountType.LIABILITY,
    )
    chart = ChartOfAccountsTemplate(
        name="Verbindlichkeits-Test",
        accounts=(account,),
        account_mapping_rules=(
            AccountMappingRule(
                account_number="3300",
                debit_position=debit_position,
                credit_position=None,
            ),
        ),
    )

    position, amount = AccountMapper(chart).map_balance(
        AccountBalance(
            account_number="3300",
            debit=Decimal("1000.00"),
        )
    )

    assert position is debit_position
    assert amount == Decimal("1000.00")


@pytest.mark.parametrize(
    ("account_number", "position_code"),
    (
        ("8021", "HGB.266.PASSIVA.A.V"),
        ("9503", "HGB.266.PASSIVA.A.V"),
        ("2978", "HGB.266.PASSIVA.A.IV"),
        ("7720", "HGB.266.PASSIVA.A.IV"),
    ),
)
def test_maps_debit_balance_of_equity_to_debit_position_as_negative(
    account_number: str,
    position_code: str,
) -> None:
    position = FinancialStatementPosition(
        code=position_code,
        name="Eigenkapitalposition",
    )
    account = TemplateAccount(
        account_number=account_number,
        name="Eigenkapitalkonto",
        account_type=AccountType.EQUITY,
    )
    chart = ChartOfAccountsTemplate(
        name="Eigenkapital-Test",
        accounts=(account,),
        account_mapping_rules=(
            AccountMappingRule(
                account_number=account_number,
                debit_position=position,
                credit_position=None,
            ),
        ),
    )

    mapped_position, amount = AccountMapper(chart).map_balance(
        AccountBalance(
            account_number=account_number,
            debit=Decimal("1000.00"),
        )
    )

    assert mapped_position is position
    assert amount == Decimal("-1000.00")


@pytest.mark.parametrize(
    ("account_number", "position_code"),
    (
        ("8020", "HGB.266.PASSIVA.A.V"),
        ("9502", "HGB.266.PASSIVA.A.V"),
        ("2970", "HGB.266.PASSIVA.A.IV"),
    ),
)
def test_maps_credit_balance_of_equity_to_credit_position_as_positive(
    account_number: str,
    position_code: str,
) -> None:
    position = FinancialStatementPosition(
        code=position_code,
        name="Eigenkapitalposition",
    )
    account = TemplateAccount(
        account_number=account_number,
        name="Eigenkapitalkonto",
        account_type=AccountType.EQUITY,
    )
    chart = ChartOfAccountsTemplate(
        name="Eigenkapital-Test",
        accounts=(account,),
        account_mapping_rules=(
            AccountMappingRule(
                account_number=account_number,
                debit_position=None,
                credit_position=position,
            ),
        ),
    )

    mapped_position, amount = AccountMapper(chart).map_balance(
        AccountBalance(
            account_number=account_number,
            credit=Decimal("1000.00"),
        )
    )

    assert mapped_position is position
    assert amount == Decimal("1000.00")


def test_equity_credit_balance_without_credit_position_still_fails() -> None:
    debit_position = FinancialStatementPosition(
        code="HGB.266.PASSIVA.A.V",
        name="Jahresfehlbetrag",
    )
    account = TemplateAccount(
        account_number="9503",
        name="Jahresfehlbetrag",
        account_type=AccountType.EQUITY,
    )
    chart = ChartOfAccountsTemplate(
        name="Eigenkapital-Test",
        accounts=(account,),
        account_mapping_rules=(
            AccountMappingRule(
                account_number="9503",
                debit_position=debit_position,
                credit_position=None,
            ),
        ),
    )

    with pytest.raises(ValueError, match="no credit position defined"):
        AccountMapper(chart).map_balance(
            AccountBalance(
                account_number="9503",
                credit=Decimal("1000.00"),
            )
        )


def test_maps_equity_debit_balance_to_credit_position_as_negative() -> None:
    carryforward_position = FinancialStatementPosition(
        code="HGB.266.PASSIVA.A.IV",
        name="Gewinnvortrag/Verlustvortrag",
    )

    account = TemplateAccount(
        account_number="2970",
        name="Gewinnvortrag / Verlustvortrag",
        account_type=AccountType.EQUITY,
    )

    rule = AccountMappingRule(
        account_number="2970",
        debit_position=None,
        credit_position=carryforward_position,
    )

    chart = ChartOfAccountsTemplate(
        name="SimpleOB",
        accounts=(account,),
        account_mapping_rules=(rule,),
    )

    balance = AccountBalance(
        account_number="2970",
        debit=Decimal("3941.64"),
        credit=Decimal("0.00"),
    )

    mapper = AccountMapper(chart)

    position, amount = mapper.map_balance(balance)

    assert position is carryforward_position
    assert amount == Decimal("-3941.64")

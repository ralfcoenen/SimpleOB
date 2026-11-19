from decimal import Decimal

import pytest

from simpleob.accounting.account_balance import AccountBalance
from simpleob.accounting.financial_statement_builder import FinancialStatementBuilder
from simpleob.accounting.financial_statement_position import FinancialStatementPosition
from simpleob.accounting.hgb_financial_statement_position_provider import (
    HgbFinancialStatementPositionProvider,
)
from simpleob.accounting.mapper import AccountMapper
from simpleob.domain.account_mapping_rule import AccountMappingRule
from simpleob.domain.account_type import AccountType
from simpleob.domain.chart_of_accounts_template import ChartOfAccountsTemplate
from simpleob.domain.errors import InvalidPersonAccountClassificationError
from simpleob.domain.person_account_role import PersonAccountRole
from simpleob.domain.template_account import TemplateAccount
from simpleob.hgb.balance_sheet_structure import create_hgb_balance_sheet_structure

DEBITOR_RECEIVABLE = "HGB.266.AKTIVA.B.II.1"
CREDITOR_PAYABLE = "HGB.266.PASSIVA.C.4"


def _chart(
    *,
    extra_accounts: tuple[TemplateAccount, ...] = (),
    extra_rules: tuple[AccountMappingRule, ...] = (),
    roles: tuple[tuple[str, PersonAccountRole], ...] | None = None,
) -> ChartOfAccountsTemplate:
    accounts = (
        TemplateAccount("10000", "Debitor A", AccountType.ASSET),
        TemplateAccount("10001", "Debitor B", AccountType.ASSET),
        TemplateAccount("70000", "Kreditor A", AccountType.LIABILITY),
        TemplateAccount("70001", "Kreditor B", AccountType.LIABILITY),
        *extra_accounts,
    )
    return ChartOfAccountsTemplate(
        "Test",
        accounts,
        extra_rules,
        roles
        if roles is not None
        else (
            ("10000", PersonAccountRole.DEBITOR),
            ("10001", PersonAccountRole.DEBITOR),
            ("70000", PersonAccountRole.KREDITOR),
            ("70001", PersonAccountRole.KREDITOR),
        ),
    )


def _positions() -> tuple[FinancialStatementPosition, FinancialStatementPosition]:
    assets, liabilities = create_hgb_balance_sheet_structure()
    return assets, liabilities


@pytest.mark.parametrize(
    ("number", "role", "debit", "credit", "expected_code", "expected_amount"),
    (
        (
            "10000", PersonAccountRole.DEBITOR,
            "125.41", "0.00", DEBITOR_RECEIVABLE, "125.41",
        ),
        (
            "10000", PersonAccountRole.DEBITOR,
            "0.00", "43.27", CREDITOR_PAYABLE, "43.27",
        ),
        (
            "70000", PersonAccountRole.KREDITOR,
            "0.00", "98.12", CREDITOR_PAYABLE, "98.12",
        ),
        (
            "70000", PersonAccountRole.KREDITOR,
            "17.39", "0.00", DEBITOR_RECEIVABLE, "17.39",
        ),
    ),
)
def test_maps_person_account_role_and_balance_direction(
    number, role, debit, credit, expected_code, expected_amount
):
    chart = _chart()
    mapper = AccountMapper(chart)
    balance = AccountBalance(
        number,
        debit=Decimal(debit),
        credit=Decimal(credit),
    )

    position, amount = mapper.map_balance(balance)

    assert position.code == expected_code
    assert amount == Decimal(expected_amount)
    assert mapper.position_for(balance) == position
    assert chart.person_account_role(number) is role


def test_person_account_saldos_are_mapped_individually_before_summing():
    assets, liabilities = _positions()
    provider = HgbFinancialStatementPositionProvider((assets, liabilities))
    builder = FinancialStatementBuilder(AccountMapper(_chart()))

    amounts = builder.build(
        (
            AccountBalance("10000", debit=Decimal("100.00")),
            AccountBalance("10001", credit=Decimal("30.00")),
            AccountBalance("70000", credit=Decimal("70.00")),
            AccountBalance("70001", debit=Decimal("20.00")),
        ),
        root_positions=(assets, liabilities),
    )

    receivable_leaf = provider.get(DEBITOR_RECEIVABLE)
    trade_payable = provider.get(CREDITOR_PAYABLE)
    payable_leaf = provider.get("HGB.266.PASSIVA.C")
    receivables = provider.get("HGB.266.AKTIVA.B.II")

    assert amounts[receivable_leaf] == Decimal("120.00")
    assert amounts[trade_payable] == Decimal("100.00")
    assert amounts[receivables] == Decimal("120.00")
    assert amounts[payable_leaf] == Decimal("100.00")


def test_zero_person_balance_has_no_mapping_and_does_not_block_builder():
    mapper = AccountMapper(_chart())
    zero = AccountBalance(
        "10000",
        debit=Decimal("25.00"),
        credit=Decimal("25.00"),
    )

    with pytest.raises(ValueError, match="Nullsaldo.*keine HGB-Bilanzposition"):
        mapper.map_balance(zero)
    with pytest.raises(ValueError, match="Nullsaldo.*keine HGB-Bilanzposition"):
        mapper.position_for(zero)
    assert FinancialStatementBuilder(mapper).build((zero,)) == {}


def test_person_account_does_not_use_an_individual_hgb_mapping_rule():
    position = FinancialStatementPosition(
        code="HGB.TEST",
        name="Unzulässige Einzelzuordnung",
    )
    chart = _chart(
        extra_rules=(
            AccountMappingRule("10000", position, position),
        ),
    )

    with pytest.raises(
        InvalidPersonAccountClassificationError,
        match="keine individuelle HGB-Zuordnung",
    ):
        AccountMapper(chart).map_balance(
            AccountBalance("10000", debit=Decimal("10.00"))
        )


@pytest.mark.parametrize(
    ("number", "role", "account_type"),
    (
        ("10000", PersonAccountRole.KREDITOR, AccountType.LIABILITY),
        ("70000", PersonAccountRole.DEBITOR, AccountType.ASSET),
        ("10000", PersonAccountRole.DEBITOR, AccountType.LIABILITY),
    ),
)
def test_rejects_person_account_role_range_or_account_type_conflicts(
    number, role, account_type
):
    account = TemplateAccount(number, "Widerspruch", account_type)
    chart = ChartOfAccountsTemplate(
        "Test",
        (account,),
        person_account_roles=((number, role),),
    )

    with pytest.raises(InvalidPersonAccountClassificationError):
        AccountMapper(chart).map_balance(
            AccountBalance(number, debit=Decimal("1.00"))
        )


def test_account_number_range_alone_does_not_classify_a_person_account():
    position = FinancialStatementPosition("HGB.TEST", "Sachkonto")
    account = TemplateAccount("10000", "Sachkonto", AccountType.ASSET)
    chart = ChartOfAccountsTemplate(
        "Test",
        (account,),
        (AccountMappingRule("10000", position, None),),
    )

    assert not chart.is_person_account("10000")
    assert chart.person_account_role("10000") is None
    with pytest.raises(
        InvalidPersonAccountClassificationError,
        match="Kontonummer allein bestimmt keine Debitoren- oder Kreditorenrolle",
    ):
        AccountMapper(chart).map_balance(
            AccountBalance("10000", debit=Decimal("1.00"))
        )


def test_unclassified_account_in_person_number_range_must_have_normal_mapping():
    chart = ChartOfAccountsTemplate(
        "Test",
        (TemplateAccount("10000", "Konto", AccountType.ASSET),),
    )

    with pytest.raises(
        InvalidPersonAccountClassificationError,
        match="keine gültige Personenkontenzuordnung",
    ):
        AccountMapper(chart).map_balance(
            AccountBalance("10000", debit=Decimal("1.00"))
        )


def test_existing_sachkonto_mapping_is_unchanged_with_person_accounts():
    position = FinancialStatementPosition("HGB.TEST.BANK", "Bank")
    chart = _chart(
        extra_accounts=(
            TemplateAccount("1200", "Bank", AccountType.ASSET),
        ),
        extra_rules=(
            AccountMappingRule("1200", position, None),
        ),
    )
    builder = FinancialStatementBuilder(AccountMapper(chart))

    amounts = builder.build(
        (
            AccountBalance("10000", debit=Decimal("100.00")),
            AccountBalance("1200", debit=Decimal("25.00")),
        )
    )

    assert amounts[position] == Decimal("25.00")
    assert sum(amounts.values()) == Decimal("125.00")

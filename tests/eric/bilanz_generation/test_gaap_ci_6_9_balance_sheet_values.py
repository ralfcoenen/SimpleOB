"""Tests für die GAAP-CI-Bilanzwerte der Taxonomie 6.9."""

from decimal import Decimal

import pytest

from simpleob.accounting.account_balance import AccountBalance
from simpleob.accounting.balance_sheet import BalanceSheet
from simpleob.accounting.financial_statement_builder import (
    FinancialStatementBuilder,
)
from simpleob.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
from simpleob.accounting.hgb_financial_statement_position_provider import (
    HgbFinancialStatementPositionProvider,
)
from simpleob.accounting.mapper import AccountMapper
from simpleob.domain.account_mapping_rule import AccountMappingRule
from simpleob.domain.account_type import AccountType
from simpleob.domain.balance_sheet_presentation import (
    BalanceSheetPresentation,
)
from simpleob.domain.chart_of_accounts_template import ChartOfAccountsTemplate
from simpleob.domain.template_account import TemplateAccount
from simpleob.eric.bilanz_generation.gaap_ci_6_9_balance_sheet_values import (
    GaapCi69BalanceSheetValueBuilder,
)
from simpleob.hgb.balance_sheet_structure import (
    create_hgb_balance_sheet_structure,
)
from simpleob.hgb.income_statement_structure import (
    create_hgb_income_statement_structure,
)
from simpleob.services.uncovered_equity_deficit_presentation_service import (
    UncoveredEquityDeficitPresentationService,
)


def _walk(
    position: FinancialStatementPosition,
) -> tuple[FinancialStatementPosition, ...]:
    result = [position]

    for child in position.children:
        result.extend(_walk(child))

    return tuple(result)


def _position_for(
    root: FinancialStatementPosition,
    code: str,
) -> FinancialStatementPosition:
    for position in _walk(root):
        if position.code == code:
            return position

    raise AssertionError(
        f"position not found: {code}"
    )


def _balance_sheet() -> tuple[
    BalanceSheet,
    FinancialStatementPosition,
]:
    assets, liabilities = create_hgb_balance_sheet_structure()
    income_statement = create_hgb_income_statement_structure()

    cash = _position_for(
        assets,
        "HGB.266.AKTIVA.B.IV",
    )

    subscribed_capital = _position_for(
        liabilities,
        "HGB.266.PASSIVA.A.I",
    )

    net_income = _position_for(
        liabilities,
        "HGB.266.PASSIVA.A.V",
    )

    balance_sheet = BalanceSheet(
        assets=assets,
        liabilities=liabilities,
        amounts={
            assets: Decimal("25000.00"),
            cash: Decimal("25000.00"),
            liabilities: Decimal("25000.00"),
            subscribed_capital: Decimal("20000.00"),
            net_income: Decimal("5000.00"),
        },
    )

    return balance_sheet, income_statement


def test_builds_gaap_ci_values_from_hgb_balance_sheet() -> None:
    balance_sheet, income_statement = _balance_sheet()

    values = GaapCi69BalanceSheetValueBuilder.build(
        balance_sheet=balance_sheet,
        income_statement=income_statement,
    )

    assert values[
        ("bs.ass",)
    ] == Decimal("25000.00")

    assert values[
        ("bs.ass.currAss.cashEquiv",)
    ] == Decimal("25000.00")

    assert values[
        ("bs.eqLiab",)
    ] == Decimal("25000.00")

    assert values[
        ("bs.eqLiab.equity.subscribed",)
    ] == Decimal("20000.00")

    assert values[
        ("bs.eqLiab.equity.netIncome",)
    ] == Decimal("5000.00")


def test_negative_bank_balance_maps_to_existing_bank_liability_taxonomy_fact():
    assets, liabilities = create_hgb_balance_sheet_structure()
    income_statement = create_hgb_income_statement_structure()
    provider = HgbFinancialStatementPositionProvider((assets, liabilities))
    account = TemplateAccount("198765", "Freies Zahlungskonto", AccountType.ASSET)
    chart = ChartOfAccountsTemplate(
        "Bankkonto mit freier Nummer",
        (account,),
        account_mapping_rules=(
            AccountMappingRule(
                "198765",
                provider.get("HGB.266.AKTIVA.B.IV"),
                None,
            ),
        ),
    )
    mapper = AccountMapper(
        chart,
        bank_account_numbers=frozenset({"198765"}),
    )
    amounts = FinancialStatementBuilder(mapper).build(
        (AccountBalance("198765", credit=Decimal("375.00")),),
        root_positions=(assets, liabilities),
    )
    balance_sheet = BalanceSheet(
        assets=assets,
        liabilities=liabilities,
        amounts=amounts,
    )

    values = GaapCi69BalanceSheetValueBuilder.build(
        balance_sheet=balance_sheet,
        income_statement=income_statement,
    )

    assert values[("bs.eqLiab.liab.bank",)] == Decimal("375.00")
    assert ("bs.ass.currAss.cashEquiv.bank",) not in values


def test_zero_amounts_are_omitted() -> None:
    balance_sheet, income_statement = _balance_sheet()

    other_receivables = _position_for(
        balance_sheet.assets,
        "HGB.266.AKTIVA.B.II.4",
    )

    balance_sheet = BalanceSheet(
        assets=balance_sheet.assets,
        liabilities=balance_sheet.liabilities,
        amounts={
            **balance_sheet.amounts,
            other_receivables: Decimal("0.00"),
        },
    )

    values = GaapCi69BalanceSheetValueBuilder.build(
        balance_sheet=balance_sheet,
        income_statement=income_statement,
    )

    assert (
        "bs.ass.currAss.receiv.other",
    ) not in values


def test_unmapped_positions_are_omitted() -> None:
    balance_sheet, income_statement = _balance_sheet()

    unmapped_position = FinancialStatementPosition(
        code="TEST.UNMAPPED",
        name="Nicht gemappt",
    )

    balance_sheet = BalanceSheet(
        assets=balance_sheet.assets,
        liabilities=balance_sheet.liabilities,
        amounts={
            **balance_sheet.amounts,
            unmapped_position: Decimal("123.45"),
        },
    )

    values = GaapCi69BalanceSheetValueBuilder.build(
        balance_sheet=balance_sheet,
        income_statement=income_statement,
    )

    assert (
        "TEST.UNMAPPED",
    ) not in values


def test_rejects_invalid_balance_sheet() -> None:
    _, income_statement = _balance_sheet()

    with pytest.raises(
        TypeError,
        match="balance_sheet must be a BalanceSheet",
    ):
        GaapCi69BalanceSheetValueBuilder.build(
            balance_sheet=object(),
            income_statement=income_statement,
        )


def test_rejects_invalid_income_statement() -> None:
    balance_sheet, _ = _balance_sheet()

    with pytest.raises(
        TypeError,
        match=(
            "income_statement must be a "
            "FinancialStatementPosition"
        ),
    ):
        GaapCi69BalanceSheetValueBuilder.build(
            balance_sheet=balance_sheet,
            income_statement=object(),
        )


def test_variant_b_maps_balance_profit_to_taxonomy_profit_loss() -> None:
    balance_sheet, income_statement = _balance_sheet()

    values = GaapCi69BalanceSheetValueBuilder.build(
        balance_sheet=balance_sheet,
        income_statement=income_statement,
        presentation=BalanceSheetPresentation.AFTER_APPROPRIATION,
    )

    assert values[("bs.eqLiab.equity.profitLoss",)] == Decimal("5000.00")
    assert ("bs.eqLiab.equity.netIncome",) not in values


def test_uncovered_equity_deficit_maps_both_taxonomy_facts() -> None:
    assets, liabilities = create_hgb_balance_sheet_structure()
    income_statement = create_hgb_income_statement_structure()
    positions = {
        position.code: position
        for position in _walk(assets) + _walk(liabilities)
    }
    raw = BalanceSheet(
        assets=assets,
        liabilities=liabilities,
        amounts={
            assets: Decimal("2000.00"),
            positions["HGB.266.AKTIVA.B.IV"]: Decimal("2000.00"),
            liabilities: Decimal("2000.00"),
            positions["HGB.266.PASSIVA.A"]: Decimal("-5000.00"),
            positions["HGB.266.PASSIVA.A.I"]: Decimal("1000.00"),
            positions["HGB.266.PASSIVA.A.IV"]: Decimal("-6000.00"),
            positions["HGB.266.PASSIVA.C"]: Decimal("7000.00"),
            positions["HGB.266.PASSIVA.C.4"]: Decimal("7000.00"),
        },
    )

    presented = UncoveredEquityDeficitPresentationService.apply(raw)
    values = GaapCi69BalanceSheetValueBuilder.build(
        balance_sheet=presented,
        income_statement=income_statement,
    )

    assert values[("bs.ass.deficitNotCoveredByCapital",)] == Decimal("5000.00")
    assert values[("bs.eqLiab.equity.deficitNotCoveredByCapital",)] == Decimal("5000.00")
    assert values[("bs.eqLiab",)] == Decimal("7000.00")
    assert values[("bs.ass",)] == Decimal("7000.00")
    assert presented.amount_for(positions["HGB.266.PASSIVA.A"]) == Decimal("0.00")
    assert raw.amount_for(positions["HGB.266.PASSIVA.A"]) == Decimal("-5000.00")
    assert not raw.uncovered_equity_deficit_applied


def test_deficit_mapping_preserves_variant_b_balance_profit() -> None:
    assets, liabilities = create_hgb_balance_sheet_structure()
    income_statement = create_hgb_income_statement_structure()
    positions = {
        position.code: position
        for position in _walk(assets) + _walk(liabilities)
    }
    raw = BalanceSheet(
        assets=assets,
        liabilities=liabilities,
        amounts={
            assets: Decimal("2000.00"),
            positions["HGB.266.AKTIVA.B.IV"]: Decimal("2000.00"),
            liabilities: Decimal("2000.00"),
            positions["HGB.266.PASSIVA.A"]: Decimal("-5000.00"),
            positions["HGB.266.PASSIVA.A.I"]: Decimal("1000.00"),
            positions["HGB.266.PASSIVA.A.IV"]: Decimal("-7000.00"),
            positions["HGB.266.PASSIVA.A.V"]: Decimal("1000.00"),
            positions["HGB.266.PASSIVA.C"]: Decimal("7000.00"),
            positions["HGB.266.PASSIVA.C.4"]: Decimal("7000.00"),
        },
    )

    presented = UncoveredEquityDeficitPresentationService.apply(raw)
    values = GaapCi69BalanceSheetValueBuilder.build(
        balance_sheet=presented,
        income_statement=income_statement,
        presentation=BalanceSheetPresentation.AFTER_APPROPRIATION,
    )

    assert values[("bs.eqLiab.equity.profitLoss",)] == Decimal("1000.00")
    assert ("bs.eqLiab.equity.netIncome",) not in values
    assert values[("bs.eqLiab.equity.deficitNotCoveredByCapital",)] == Decimal("5000.00")


@pytest.mark.parametrize(
    ("equity", "expected_deficit"),
    (
        (Decimal("0.00"), Decimal("0.00")),
        (Decimal("500.00"), Decimal("0.00")),
        (Decimal("-500.00"), Decimal("500.00")),
        (Decimal("-5000.00"), Decimal("5000.00")),
        (Decimal("-100.00"), Decimal("100.00")),
    ),
)
def test_deficit_is_only_presented_for_negative_equity(
    equity: Decimal,
    expected_deficit: Decimal,
) -> None:
    assets, liabilities = create_hgb_balance_sheet_structure()
    income_statement = create_hgb_income_statement_structure()
    positions = {
        position.code: position
        for position in _walk(assets) + _walk(liabilities)
    }
    balance_sheet = BalanceSheet(
        assets=assets,
        liabilities=liabilities,
        amounts={
            assets: Decimal("1000.00"),
            positions["HGB.266.AKTIVA.B.IV"]: Decimal("1000.00"),
            liabilities: Decimal("1000.00"),
            positions["HGB.266.PASSIVA.A"]: equity,
            positions["HGB.266.PASSIVA.A.I"]: equity,
            positions["HGB.266.PASSIVA.C"]: Decimal("1000.00") - equity,
            positions["HGB.266.PASSIVA.C.4"]: Decimal("1000.00") - equity,
        },
    )

    presented = UncoveredEquityDeficitPresentationService.apply(
        balance_sheet
    )
    values = GaapCi69BalanceSheetValueBuilder.build(
        balance_sheet=presented,
        income_statement=income_statement,
    )

    if expected_deficit:
        assert values[("bs.ass.deficitNotCoveredByCapital",)] == expected_deficit
        assert values[("bs.eqLiab.equity.deficitNotCoveredByCapital",)] == expected_deficit
    else:
        assert ("bs.ass.deficitNotCoveredByCapital",) not in values
        assert ("bs.eqLiab.equity.deficitNotCoveredByCapital",) not in values

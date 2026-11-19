"""Tests für EBilanzPreparationService."""

from decimal import Decimal
from unittest.mock import Mock

from simpleob.accounting.financial_statement_builder import (
    FinancialStatementBuilder,
)
from simpleob.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
from simpleob.accounting.hgb_financial_statement_position_provider import (
    HgbFinancialStatementPositionProvider,
)
from simpleob.accounting.income_statement import IncomeStatement
from simpleob.accounting.ledger import Ledger
from simpleob.accounting.mapper import AccountMapper
from simpleob.domain.account_type import AccountType
from simpleob.domain.chart_of_accounts_template import ChartOfAccountsTemplate
from simpleob.domain.person_account_role import PersonAccountRole
from simpleob.domain.template_account import TemplateAccount
from simpleob.hgb.balance_sheet_structure import create_hgb_balance_sheet_structure
from simpleob.hgb.income_statement_structure import (
    create_hgb_income_statement_structure,
)
from simpleob.services.closing_service import ClosingService
from simpleob.services.e_bilanz_preparation_service import (
    EBilanzPreparationService,
)


def test_combines_pre_closing_income_statement_with_closed_balance_sheet(
) -> None:
    """GuV vor Abschluss und Bilanz nach Abschluss werden verbunden."""

    assets = Mock(
        spec=FinancialStatementPosition
    )
    liabilities = Mock(
        spec=FinancialStatementPosition
    )
    equity = Mock(
        spec=FinancialStatementPosition
    )
    income_statement_root = Mock(
        spec=FinancialStatementPosition
    )

    revenue_position = Mock(
        spec=FinancialStatementPosition
    )
    profit_position = Mock(
        spec=FinancialStatementPosition
    )

    equity.code = "HGB.266.PASSIVA.A"
    profit_position.code = "HGB.266.PASSIVA.A.V"

    liabilities.children = (equity,)
    equity.children = (profit_position,)

    income_statement = IncomeStatement(
        income_statement=income_statement_root,
        amounts={
            revenue_position: Decimal("16500.00"),
        },
    )

    ledger = Ledger()

    ledger.post(
        debit_account="1200",
        credit_account="8020",
        amount=Decimal("5080.00"),
    )

    statement_builder = Mock(
        spec=FinancialStatementBuilder
    )

    statement_builder.build.return_value = {
        profit_position: Decimal("5080.00"),
    }

    closing_service = Mock(
        spec=ClosingService
    )
    closing_service.calculate_net_income.return_value = (
        Decimal("5080.00")
    )

    service = EBilanzPreparationService(
        statement_builder=statement_builder,
        closing_service=closing_service,
        account_types={
            "1200": AccountType.ASSET,
            "8020": AccountType.EQUITY,
        },
        assets=assets,
        liabilities=liabilities,
        income_summary_account_number="8990",
    )

    result = service.prepare(
        income_statement=income_statement,
        closed_ledger=ledger,
    )

    assert result.balance_sheet.assets is assets
    assert result.balance_sheet.liabilities is liabilities

    assert dict(result.balance_sheet.amounts) == {
        profit_position: Decimal("5080.00"),
    }

    assert result.income_statement_amounts == {
        revenue_position: Decimal("16500.00"),
    }

    assert result.balance_sheet_amounts == {
        profit_position: Decimal("5080.00"),
    }

    assert result.amounts == {
        revenue_position: Decimal("16500.00"),
        profit_position: Decimal("5080.00"),
    }

    closing_service.calculate_net_income.assert_called_once_with(
        income_statement=income_statement,
    )

    statement_builder.build.assert_called_once()

    call_kwargs = (
        statement_builder.build.call_args.kwargs
    )

    assert call_kwargs["root_positions"] == (
        assets,
        liabilities,
    )

    assert (
        call_kwargs["closing_result"].net_income
        == Decimal("5080.00")
    )

    assert (
        call_kwargs["result_position"]
        is profit_position
    )

    balances = call_kwargs["balances"]

    assert {
        balance.account_number
        for balance in balances
    } == {
        "1200",
        "8020",
    }

def test_excludes_income_summary_account_from_balance_sheet(
) -> None:
    """Das technische GuV-Abschlusskonto 8990 wird ausgeschlossen."""

    assets = Mock(
        spec=FinancialStatementPosition
    )
    liabilities = Mock(
        spec=FinancialStatementPosition
    )
    equity = Mock(
        spec=FinancialStatementPosition
    )
    result_position = Mock(
        spec=FinancialStatementPosition
    )
    income_statement_root = Mock(
        spec=FinancialStatementPosition
    )

    equity.code = "HGB.266.PASSIVA.A"
    result_position.code = "HGB.266.PASSIVA.A.V"

    liabilities.children = (equity,)
    equity.children = (result_position,)

    income_statement = IncomeStatement(
        income_statement=income_statement_root,
        amounts={},
    )

    ledger = Ledger()

    ledger.post(
        debit_account="1200",
        credit_account="8990",
        amount=Decimal("100.00"),
    )

    statement_builder = Mock(
        spec=FinancialStatementBuilder
    )
    statement_builder.build.return_value = {}

    closing_service = Mock(
        spec=ClosingService
    )
    closing_service.calculate_net_income.return_value = (
        Decimal("0.00")
    )

    service = EBilanzPreparationService(
        statement_builder=statement_builder,
        closing_service=closing_service,
        account_types={
            "1200": AccountType.ASSET,
            "8990": AccountType.EQUITY,
        },
        assets=assets,
        liabilities=liabilities,
        income_summary_account_number="8990",
    )

    service.prepare(
        income_statement=income_statement,
        closed_ledger=ledger,
    )

    balances = (
        statement_builder
        .build
        .call_args
        .kwargs["balances"]
    )

    assert {
        balance.account_number
        for balance in balances
    } == {
        "1200",
    }


def test_real_preparation_adds_person_accounts_to_existing_hgb_positions():
    assets, liabilities = create_hgb_balance_sheet_structure()
    income_statement_root = create_hgb_income_statement_structure()
    provider = HgbFinancialStatementPositionProvider((assets, liabilities))
    chart = ChartOfAccountsTemplate(
        "Personenkonten",
        (
            TemplateAccount("10000", "Kunde", AccountType.ASSET),
            TemplateAccount("70000", "Lieferant", AccountType.LIABILITY),
        ),
        person_account_roles=(
            ("10000", PersonAccountRole.DEBITOR),
            ("70000", PersonAccountRole.KREDITOR),
        ),
    )
    ledger = Ledger()
    ledger.post("10000", "70000", Decimal("123.45"))
    service = EBilanzPreparationService(
        statement_builder=FinancialStatementBuilder(AccountMapper(chart)),
        closing_service=ClosingService(),
        account_types={
            "10000": AccountType.ASSET,
            "70000": AccountType.LIABILITY,
        },
        assets=assets,
        liabilities=liabilities,
        income_summary_account_number="8990",
    )

    result = service.prepare(
        income_statement=IncomeStatement(
            income_statement=income_statement_root,
            amounts={},
        ),
        closed_ledger=ledger,
    )

    receivables = provider.get("HGB.266.AKTIVA.B.II.1")
    payables = provider.get("HGB.266.PASSIVA.C.4")
    assert result.balance_sheet_amounts[receivables] == Decimal("123.45")
    assert result.balance_sheet_amounts[payables] == Decimal("123.45")
    assert result.balance_sheet.is_balanced()

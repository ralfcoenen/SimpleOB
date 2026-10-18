"""Gemeinsamer Kontext für HGB-Abschluss und E-Bilanz."""

from dataclasses import dataclass
from pathlib import Path

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
from simpleob.domain.account import Account
from simpleob.domain.account_type import AccountType
from simpleob.domain.chart_of_accounts_template import (
    ChartOfAccountsTemplate,
)
from simpleob.hgb.balance_sheet_structure import (
    create_hgb_balance_sheet_structure,
)
from simpleob.hgb.income_statement_structure import (
    create_hgb_income_statement_structure,
)
from simpleob.importers.csv_chart_of_accounts_importer import (
    CsvChartOfAccountsImporter,
)


@dataclass(frozen=True, slots=True)
class FinancialStatementContext:
    """Gemeinsame HGB-Strukturen einer OpenBilanz-Anwendung."""

    assets: FinancialStatementPosition
    liabilities: FinancialStatementPosition
    income_statement: FinancialStatementPosition
    chart_of_accounts: ChartOfAccountsTemplate
    accounts: tuple[Account, ...]
    account_mapper: AccountMapper
    statement_builder: FinancialStatementBuilder
    account_types: dict[str, AccountType]


def create_financial_statement_context(
    *,
    assets: FinancialStatementPosition,
    liabilities: FinancialStatementPosition,
    income_statement: FinancialStatementPosition,
    chart_of_accounts: ChartOfAccountsTemplate,
    accounts: tuple[Account, ...],
) -> FinancialStatementContext:
    """Erzeugt einen Abschlusskontext aus einem Kontenrahmen."""

    account_mapper = AccountMapper(
        chart_of_accounts
    )

    statement_builder = FinancialStatementBuilder(
        account_mapper
    )

    account_types = {
        account.account_number:
            account.account_type
        for account
        in chart_of_accounts.accounts
    }

    return FinancialStatementContext(
        assets=assets,
        liabilities=liabilities,
        income_statement=income_statement,
        chart_of_accounts=chart_of_accounts,
        accounts=accounts,
        account_mapper=account_mapper,
        statement_builder=statement_builder,
        account_types=account_types,
    )


def create_standard_financial_statement_context(
) -> FinancialStatementContext:
    """Erzeugt den OpenBilanz-Standardkontext."""

    (
        assets,
        liabilities,
    ) = create_hgb_balance_sheet_structure()

    income_statement = (
        create_hgb_income_statement_structure()
    )

    provider = HgbFinancialStatementPositionProvider(
        (
            assets,
            liabilities,
            income_statement,
        )
    )

    csv_file = (
        Path(__file__).resolve().parent.parent
        / "resources"
        / "chart_of_accounts"
        / "openbilanz_standard.csv"
    )

    chart_of_accounts = CsvChartOfAccountsImporter(
        position_provider=provider,
    ).load(csv_file)

    accounts = tuple(
        Account(
            template=template_account
        )
        for template_account
        in chart_of_accounts.accounts
    )

    return create_financial_statement_context(
        assets=assets,
        liabilities=liabilities,
        income_statement=income_statement,
        chart_of_accounts=chart_of_accounts,
        accounts=accounts,
    )

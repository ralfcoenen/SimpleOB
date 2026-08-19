"""Initialisierung mandantenspezifischer Kontenrahmen."""

from openbilanz.accounting.financial_statement_position_provider import (
    FinancialStatementPositionProvider,
)
from openbilanz.database.chart_of_accounts_repository import (
    ChartOfAccountsRepository,
)
from openbilanz.domain.account import Account
from openbilanz.domain.accounting_control_accounts import (
    AccountingControlAccounts,
)
from openbilanz.domain.chart_of_accounts_template import (
    ChartOfAccountsTemplate,
)
from openbilanz.domain.company import Company


class ChartOfAccountsInitializationService:
    """Initialisiert den Kontenrahmen eines Mandanten."""

    def __init__(
        self,
        *,
        repository: ChartOfAccountsRepository,
        position_provider: FinancialStatementPositionProvider,
    ) -> None:
        self._repository = repository
        self._position_provider = position_provider

    def initialize(
        self,
        *,
        company: Company,
        standard_chart_of_accounts: ChartOfAccountsTemplate,
    ) -> bool:
        """Initialisiert einen noch nicht vorhandenen Mandantenkontenrahmen.

        Liefert True, wenn der Kontenrahmen neu angelegt wurde.
        Liefert False, wenn bereits ein Kontenrahmen vorhanden war.
        """

        existing = self._repository.load_for_company(
            company_id=company.company_id,
            position_provider=self._position_provider,
        )

        if existing is not None:
            return False

        accounts = tuple(
            Account(
                template=template_account
            )
            for template_account
            in standard_chart_of_accounts.accounts
        )

        control_accounts = AccountingControlAccounts(
            opening_balance_account="9000",
            income_summary_account="8990",
            profit_account="8020",
            loss_account="8021",
        )

        self._repository.save_for_company(
            company_id=company.company_id,
            chart_of_accounts=standard_chart_of_accounts,
            accounts=accounts,
            commit=False,
        )

        self._repository.save_control_accounts(
            company_id=company.company_id,
            control_accounts=control_accounts,
            commit=False,
        )

        return True

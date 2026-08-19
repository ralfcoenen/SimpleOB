"""Tests für die Persistenz mandantenspezifischer Kontenrahmen."""

from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from openbilanz.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
from openbilanz.accounting.hgb_financial_statement_position_provider import (
    HgbFinancialStatementPositionProvider,
)
from openbilanz.database.chart_of_accounts_repository import (
    ChartOfAccountsRepository,
)
from openbilanz.database.company_repository import (
    CompanyRepository,
)
from openbilanz.database.database import Base
from openbilanz.domain.account import Account
from openbilanz.domain.account_mapping_rule import (
    AccountMappingRule,
)
from openbilanz.domain.account_type import AccountType
from openbilanz.domain.accounting_control_accounts import (
    AccountingControlAccounts,
)
from openbilanz.domain.chart_of_accounts_template import (
    ChartOfAccountsTemplate,
)
from openbilanz.domain.company import Company
from openbilanz.domain.template_account import TemplateAccount


def test_saves_and_loads_chart_of_accounts() -> None:
    """Konten, Aktivstatus und HGB-Zuordnungen bleiben erhalten."""

    engine = create_engine(
        "sqlite:///:memory:"
    )
    Base.metadata.create_all(engine)

    Session = sessionmaker(
        bind=engine
    )

    bank_position = FinancialStatementPosition(
        code="HGB.266.AKTIVA.B.IV",
        name="Guthaben bei Kreditinstituten",
    )

    revenue_position = FinancialStatementPosition(
        code="HGB.275.1",
        name="Umsatzerlöse",
    )

    assets = FinancialStatementPosition(
        code="HGB.266.AKTIVA",
        name="Aktiva",
        children=(bank_position,),
    )

    income_statement = FinancialStatementPosition(
        code="HGB.275",
        name="Gewinn- und Verlustrechnung",
        children=(revenue_position,),
    )

    provider = HgbFinancialStatementPositionProvider(
        (
            assets,
            income_statement,
        )
    )

    bank_template = TemplateAccount(
        account_number="1200",
        name="Bank",
        account_type=AccountType.ASSET,
    )

    revenue_template = TemplateAccount(
        account_number="8400",
        name="Umsatzerlöse",
        account_type=AccountType.REVENUE,
    )

    chart_of_accounts = ChartOfAccountsTemplate(
        name="Testkontenrahmen",
        accounts=(
            bank_template,
            revenue_template,
        ),
        account_mapping_rules=(
            AccountMappingRule(
                account_number="1200",
                debit_position=bank_position,
                credit_position=None,
            ),
            AccountMappingRule(
                account_number="8400",
                debit_position=None,
                credit_position=revenue_position,
            ),
        ),
    )

    accounts = (
        Account(
            template=bank_template,
        ),
        Account(
            template=revenue_template,
            is_active=False,
        ),
    )

    company = Company(
        company_id=uuid4(),
        name="Muster UG",
    )

    with Session() as session:
        company_repository = CompanyRepository(
            session
        )
        repository = ChartOfAccountsRepository(
            session
        )

        company_repository.add(
            company
        )

        repository.save_for_company(
            company_id=company.company_id,
            chart_of_accounts=chart_of_accounts,
            accounts=accounts,
        )

        loaded = repository.load_for_company(
            company_id=company.company_id,
            position_provider=provider,
        )

    assert loaded is not None

    loaded_chart, loaded_accounts = loaded

    assert tuple(
        account.account_number
        for account in loaded_chart.accounts
    ) == (
        "1200",
        "8400",
    )

    assert tuple(
        account.account_type
        for account in loaded_chart.accounts
    ) == (
        AccountType.ASSET,
        AccountType.REVENUE,
    )

    assert tuple(
        account.is_active
        for account in loaded_accounts
    ) == (
        True,
        False,
    )

    mapping_by_number = {
        rule.account_number: rule
        for rule in loaded_chart.account_mapping_rules
    }

    assert (
        mapping_by_number["1200"].debit_position
        == bank_position
    )
    assert (
        mapping_by_number["1200"].credit_position
        is None
    )

    assert (
        mapping_by_number["8400"].debit_position
        is None
    )
    assert (
        mapping_by_number["8400"].credit_position
        == revenue_position
    )


def test_saves_and_validates_control_accounts() -> None:
    """Technische Konten müssen im Mandantenkontenrahmen vorhanden sein."""

    engine = create_engine(
        "sqlite:///:memory:"
    )
    Base.metadata.create_all(engine)

    Session = sessionmaker(
        bind=engine
    )

    template_accounts = tuple(
        TemplateAccount(
            account_number=account_number,
            name=name,
            account_type=AccountType.EQUITY,
        )
        for account_number, name in (
            ("9000", "Eröffnungsbilanzkonto"),
            ("8990", "GuV-Sammelkonto"),
            ("8020", "Jahresüberschuss"),
            ("8021", "Jahresfehlbetrag"),
        )
    )

    chart_of_accounts = ChartOfAccountsTemplate(
        name="Testkontenrahmen",
        accounts=template_accounts,
    )

    accounts = tuple(
        Account(
            template=template_account
        )
        for template_account in template_accounts
    )

    company = Company(
        company_id=uuid4(),
        name="Muster UG",
    )

    control_accounts = AccountingControlAccounts(
        opening_balance_account="9000",
        income_summary_account="8990",
        profit_account="8020",
        loss_account="8021",
    )

    with Session() as session:
        company_repository = CompanyRepository(
            session
        )
        repository = ChartOfAccountsRepository(
            session
        )

        company_repository.add(
            company
        )

        repository.save_for_company(
            company_id=company.company_id,
            chart_of_accounts=chart_of_accounts,
            accounts=accounts,
        )

        repository.save_control_accounts(
            company_id=company.company_id,
            control_accounts=control_accounts,
        )

        loaded = repository.load_control_accounts(
            company.company_id
        )

        invalid_control_accounts = (
            AccountingControlAccounts(
                opening_balance_account="9999",
                income_summary_account="8990",
                profit_account="8020",
                loss_account="8021",
            )
        )

        with pytest.raises(
            ValueError,
            match="9999",
        ):
            repository.save_control_accounts(
                company_id=company.company_id,
                control_accounts=invalid_control_accounts,
            )

    assert loaded == control_accounts

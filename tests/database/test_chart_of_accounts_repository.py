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
from openbilanz.domain.accounting_account_roles import (
    AccountingAccountRoles,
)
from openbilanz.domain.accounting_control_accounts import (
    AccountingControlAccounts,
)
from openbilanz.domain.chart_of_accounts_template import (
    ChartOfAccountsTemplate,
)
from openbilanz.domain.company import Company
from openbilanz.domain.template_account import TemplateAccount
from openbilanz.domain.vat_accounts import VatAccounts


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

    template_accounts = (
        TemplateAccount(
            account_number="9000",
            name="Eröffnungsbilanzkonto",
            account_type=AccountType.EQUITY,
        ),
        TemplateAccount(
            account_number="8990",
            name="GuV-Sammelkonto",
            account_type=AccountType.EQUITY,
        ),
        TemplateAccount(
            account_number="8020",
            name="Jahresüberschuss",
            account_type=AccountType.EQUITY,
        ),
        TemplateAccount(
            account_number="8021",
            name="Jahresfehlbetrag",
            account_type=AccountType.EQUITY,
        ),
        TemplateAccount(
            account_number="2970",
            name="Gewinnvortrag / Verlustvortrag",
            account_type=AccountType.EQUITY,
        ),
        TemplateAccount(
            account_number="1571",
            name="Abziehbare Vorsteuer 7 %",
            account_type=AccountType.ASSET,
        ),
        TemplateAccount(
            account_number="1576",
            name="Abziehbare Vorsteuer 19 %",
            account_type=AccountType.ASSET,
        ),
        TemplateAccount(
            account_number="1771",
            name="Umsatzsteuer 7 %",
            account_type=AccountType.LIABILITY,
        ),
        TemplateAccount(
            account_number="1776",
            name="Umsatzsteuer 19 %",
            account_type=AccountType.LIABILITY,
        ),
        TemplateAccount(
            account_number="1000",
            name="Kasse",
            account_type=AccountType.ASSET,
        ),
        TemplateAccount(
            account_number="1200",
            name="Bank",
            account_type=AccountType.ASSET,
        ),
        TemplateAccount(
            account_number="8400",
            name="Umsatzerlöse 19 %",
            account_type=AccountType.REVENUE,
        ),
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
        profit_loss_carryforward_account="2970",
    )

    vat_accounts = VatAccounts(
        input_tax_7="1571",
        input_tax_19="1576",
        output_tax_7="1771",
        output_tax_19="1776",
    )

    account_roles = AccountingAccountRoles(
        cash_accounts=frozenset({"1000"}),
        bank_accounts=frozenset({"1200"}),
        general_rate_sales_accounts=frozenset({"8400"}),
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

        repository.save_vat_accounts(
            company_id=company.company_id,
            vat_accounts=vat_accounts,
        )

        repository.save_account_roles(
            company_id=company.company_id,
            account_roles=account_roles,
        )

        loaded = repository.load_control_accounts(
            company.company_id
        )

        loaded_vat_accounts = (
            repository.load_vat_accounts(
                company.company_id
            )
        )

        loaded_account_roles = (
            repository.load_account_roles(
                company.company_id
            )
        )

        invalid_control_accounts = AccountingControlAccounts(
            opening_balance_account="9999",
            income_summary_account="8990",
            profit_account="8020",
            loss_account="8021",
            profit_loss_carryforward_account="2970",
        )

        with pytest.raises(
            ValueError,
            match="9999",
        ):
            repository.save_control_accounts(
                company_id=company.company_id,
                control_accounts=invalid_control_accounts,
            )

        invalid_account_roles = AccountingAccountRoles(
            cash_accounts=frozenset({"9999"}),
            bank_accounts=frozenset({"1200"}),
            general_rate_sales_accounts=frozenset({"8400"}),
        )

        with pytest.raises(
            ValueError,
            match="9999",
        ):
            repository.save_account_roles(
                company_id=company.company_id,
                account_roles=invalid_account_roles,
            )

    assert loaded == control_accounts
    assert (
        loaded.profit_loss_carryforward_account
        == "2970"
    )
    assert loaded_vat_accounts == vat_accounts

    assert loaded_account_roles == account_roles


def test_adds_account_to_existing_chart_of_accounts() -> None:
    """Ein neues Konto wird dem Mandantenkontenrahmen hinzugefügt."""

    engine = create_engine(
        "sqlite:///:memory:"
    )
    Base.metadata.create_all(engine)

    Session = sessionmaker(
        bind=engine
    )

    company = Company(
        company_id=uuid4(),
        name="Muster UG",
    )

    position = FinancialStatementPosition(
        code="HGB.266.AKTIVA.B.IV",
        name="Guthaben bei Kreditinstituten",
    )

    provider = HgbFinancialStatementPositionProvider(
        (
            FinancialStatementPosition(
                code="HGB.266.AKTIVA",
                name="Aktiva",
                children=(position,),
            ),
        )
    )

    template_account = TemplateAccount(
        account_number="1210",
        name="Weitere Bank",
        account_type=AccountType.ASSET,
    )

    account = Account(
        template=template_account,
    )

    mapping_rule = AccountMappingRule(
        account_number="1210",
        debit_position=position,
        credit_position=None,
    )

    with Session() as session:
        CompanyRepository(session).add(
            company
        )

        repository = ChartOfAccountsRepository(
            session
        )

        repository.add_account(
            company_id=company.company_id,
            account=account,
            mapping_rule=mapping_rule,
        )

        loaded = repository.load_for_company(
            company_id=company.company_id,
            position_provider=provider,
        )

    assert loaded is not None

    chart_of_accounts, accounts = loaded

    assert tuple(
        item.account_number
        for item in chart_of_accounts.accounts
    ) == ("1210",)

    assert accounts == (account,)

    assert (
        chart_of_accounts
        .account_mapping_rules[0]
        .debit_position
        == position
    )

def test_updates_existing_account() -> None:
    """Ein vorhandenes Konto kann geändert werden."""

    engine = create_engine(
        "sqlite:///:memory:"
    )
    Base.metadata.create_all(engine)

    Session = sessionmaker(
        bind=engine
    )

    company = Company(
        company_id=uuid4(),
        name="Muster UG",
    )

    first_position = FinancialStatementPosition(
        code="HGB.266.AKTIVA.B.IV",
        name="Guthaben bei Kreditinstituten",
    )

    second_position = FinancialStatementPosition(
        code="HGB.266.AKTIVA.B.II.4",
        name="Sonstige Vermögensgegenstände",
    )

    assets = FinancialStatementPosition(
        code="HGB.266.AKTIVA",
        name="Aktiva",
        children=(
            first_position,
            second_position,
        ),
    )

    provider = HgbFinancialStatementPositionProvider(
        assets
    )

    original_template = TemplateAccount(
        account_number="1210",
        name="Weitere Bank",
        account_type=AccountType.ASSET,
    )

    updated_template = TemplateAccount(
        account_number="1210",
        name="Verrechnungskonto",
        account_type=AccountType.ASSET,
    )

    original_account = Account(
        template=original_template,
    )

    updated_account = Account(
        template=updated_template,
        is_active=False,
    )

    original_mapping = AccountMappingRule(
        account_number="1210",
        debit_position=first_position,
        credit_position=None,
    )

    updated_mapping = AccountMappingRule(
        account_number="1210",
        debit_position=second_position,
        credit_position=None,
    )

    with Session() as session:
        CompanyRepository(session).add(
            company
        )

        repository = ChartOfAccountsRepository(
            session
        )

        repository.add_account(
            company_id=company.company_id,
            account=original_account,
            mapping_rule=original_mapping,
        )

        repository.update_account(
            company_id=company.company_id,
            account=updated_account,
            mapping_rule=updated_mapping,
        )

        loaded = repository.load_for_company(
            company_id=company.company_id,
            position_provider=provider,
        )

    assert loaded is not None

    chart_of_accounts, accounts = loaded

    assert accounts == (updated_account,)

    mapping_rule = (
        chart_of_accounts
        .account_mapping_rules[0]
    )

    assert (
        mapping_rule.debit_position
        == second_position
    )

def test_replaces_existing_account_roles() -> None:
    """Eine vorhandene Rollenbelegung wird vollständig ersetzt."""

    engine = create_engine(
        "sqlite:///:memory:"
    )
    Base.metadata.create_all(engine)

    Session = sessionmaker(
        bind=engine
    )

    template_accounts = (
        TemplateAccount(
            account_number="1000",
            name="Kasse",
            account_type=AccountType.ASSET,
        ),
        TemplateAccount(
            account_number="1010",
            name="Nebenkasse",
            account_type=AccountType.ASSET,
        ),
        TemplateAccount(
            account_number="1200",
            name="Bank",
            account_type=AccountType.ASSET,
        ),
        TemplateAccount(
            account_number="1210",
            name="Weitere Bank",
            account_type=AccountType.ASSET,
        ),
        TemplateAccount(
            account_number="8400",
            name="Umsatzerlöse 19 %",
            account_type=AccountType.REVENUE,
        ),
        TemplateAccount(
            account_number="8410",
            name="Weitere Umsatzerlöse 19 %",
            account_type=AccountType.REVENUE,
        ),
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

    original_roles = AccountingAccountRoles(
        cash_accounts=frozenset({"1000"}),
        bank_accounts=frozenset({"1200"}),
        general_rate_sales_accounts=frozenset({"8400"}),
    )

    replacement_roles = AccountingAccountRoles(
        cash_accounts=frozenset({"1010"}),
        bank_accounts=frozenset({"1200", "1210"}),
        general_rate_sales_accounts=frozenset({"8410"}),
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

        repository.save_account_roles(
            company_id=company.company_id,
            account_roles=original_roles,
        )

        repository.save_account_roles(
            company_id=company.company_id,
            account_roles=replacement_roles,
        )

        loaded = repository.load_account_roles(
            company.company_id
        )

    assert loaded == replacement_roles

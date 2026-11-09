"""Tests für die Initialisierung mandantenspezifischer Kontenrahmen."""

from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from simpleob.accounting.hgb_financial_statement_position_provider import (
    HgbFinancialStatementPositionProvider,
)
from simpleob.database.chart_of_accounts_repository import (
    ChartOfAccountsRepository,
)
from simpleob.database.company_repository import (
    CompanyRepository,
)
from simpleob.database.database import Base
from simpleob.domain.account_type import AccountType
from simpleob.domain.accounting_account_roles import (
    AccountingAccountRoles,
)
from simpleob.domain.accounting_control_accounts import (
    AccountingControlAccounts,
)
from simpleob.domain.chart_of_accounts_template import (
    ChartOfAccountsTemplate,
)
from simpleob.domain.company import Company
from simpleob.domain.fiscal_year import FiscalYear
from simpleob.domain.template_account import TemplateAccount
from simpleob.domain.vat_accounts import VatAccounts
from simpleob.hgb.balance_sheet_structure import (
    create_hgb_balance_sheet_structure,
)
from simpleob.hgb.income_statement_structure import (
    create_hgb_income_statement_structure,
)
from simpleob.services.chart_of_accounts_initialization_service import (
    ChartOfAccountsInitializationService,
)


def _standard_chart_of_accounts() -> ChartOfAccountsTemplate:
    """Erzeugt eine minimale Standardvorlage."""

    return ChartOfAccountsTemplate(
        name="OpenBilanz Standard",
        accounts=(
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
                account_number="0846",
                name="Gesetzliche Rücklage",
                account_type=AccountType.EQUITY,
            ),
            TemplateAccount(
                account_number="0855",
                name="Andere Gewinnrücklagen",
                account_type=AccountType.EQUITY,
            ),
            TemplateAccount(
                account_number="0755",
                name=(
                    "Verbindlichkeiten gegenüber Gesellschaftern "
                    "für offene Ausschüttungen"
                ),
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
                account_number="1400",
                name="Forderungen aus Lieferungen und Leistungen",
                account_type=AccountType.ASSET,
            ),
            TemplateAccount(
                account_number="1410",
                name="Lieferantenguthaben",
                account_type=AccountType.ASSET,
            ),
            TemplateAccount(
                account_number="1600",
                name="Verbindlichkeiten aus Lieferungen und Leistungen",
                account_type=AccountType.LIABILITY,
            ),
            TemplateAccount(
                account_number="1610",
                name="Kundenguthaben",
                account_type=AccountType.LIABILITY,
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
                account_number="8400",
                name="Umsatzerlöse 19 %",
                account_type=AccountType.REVENUE,
            ),
            TemplateAccount(
                account_number="4830",
                name="Abschreibungen auf Sachanlagen",
                account_type=AccountType.EXPENSE,
            ),
            TemplateAccount(
                account_number="4900",
                name="Sonstige betriebliche Aufwendungen",
                account_type=AccountType.EXPENSE,
            ),
            TemplateAccount(
                account_number="8500",
                name="Sonstige betriebliche Erträge",
                account_type=AccountType.REVENUE,
            ),
        ),
    )

def _standard_account_taxonomy_concepts() -> dict[str, str]:
    """Erzeugt eine minimale Standard-Taxonomiezuordnung."""

    return {
        "4900": (
            "is.netIncome.regular.operatingTC."
            "otherCost.disposFixAss"
        ),
    }


def _position_provider() -> HgbFinancialStatementPositionProvider:
    assets, liabilities = (
        create_hgb_balance_sheet_structure()
    )

    income_statement = (
        create_hgb_income_statement_structure()
    )

    return HgbFinancialStatementPositionProvider(
        (
            assets,
            liabilities,
            income_statement,
        )
    )


def test_initializes_chart_of_accounts_for_company() -> None:
    """Ein neuer Mandant erhält den Standardkontenrahmen."""

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

        service = ChartOfAccountsInitializationService(
            repository=repository,
            position_provider=_position_provider(),
        )

        initialized = service.initialize(
            company=company,
            standard_chart_of_accounts=(
                _standard_chart_of_accounts()
            ),
            standard_account_taxonomy_concepts=(
                _standard_account_taxonomy_concepts()
            ),
            use_standard_defaults=True,
        )

        session.commit()

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
    loaded_account_taxonomy_concepts = (
        repository.load_account_taxonomy_concepts(
            company.company_id,
            taxonomy_version="6.9",
        )
    )

    assert initialized is True
    assert loaded is not None
    assert loaded.opening_balance_account == "9000"
    assert loaded.income_summary_account == "8990"
    assert loaded.profit_account == "8020"
    assert loaded.loss_account == "8021"
    assert loaded_vat_accounts is not None
    assert loaded_vat_accounts.input_tax_7 == "1571"
    assert loaded_vat_accounts.input_tax_19 == "1576"
    assert loaded_vat_accounts.output_tax_7 == "1771"
    assert loaded_vat_accounts.output_tax_19 == "1776"
    assert loaded_account_roles is not None
    assert loaded_account_roles.cash_accounts == frozenset(
        {"1000"}
    )
    assert loaded_account_roles.bank_accounts == frozenset(
        {"1200"}
    )
    assert (
        loaded_account_roles.general_rate_sales_accounts
        == frozenset({"8400"})
    )
    assert loaded_account_roles.customer_receivables == frozenset({"1400"})
    assert loaded_account_roles.supplier_payables == frozenset({"1600"})
    assert loaded_account_roles.customer_credit_balances == frozenset({"1610"})
    assert loaded_account_roles.supplier_credit_balances == frozenset({"1410"})
    assert loaded_account_taxonomy_concepts == {
        "4900": (
            "is.netIncome.regular.operatingTC."
            "otherCost.disposFixAss"
        ),
    }


def test_individual_chart_requires_explicit_system_and_vat_accounts() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    company = Company(company_id=uuid4(), name="Individuelle UG")

    with Session() as session:
        company_repository = CompanyRepository(session)
        repository = ChartOfAccountsRepository(session)
        company_repository.add(company, commit=False)
        service = ChartOfAccountsInitializationService(
            repository=repository,
            position_provider=_position_provider(),
        )

        with pytest.raises(ValueError, match="ausdrücklich zugeordnet"):
            service.initialize(
                company=company,
                standard_chart_of_accounts=ChartOfAccountsTemplate(
                    name="Fremder Rahmen",
                    accounts=(
                        TemplateAccount(
                            "7000", "Aktivkonto", AccountType.ASSET
                        ),
                    ),
                ),
            )
        session.rollback()
        assert repository.load_for_company(
            company_id=company.company_id,
            position_provider=_position_provider(),
        ) is None


def test_does_not_replace_existing_chart_of_accounts() -> None:
    """Ein vorhandener Mandantenkontenrahmen wird nicht überschrieben."""

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

    provider = _position_provider()

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

        service = ChartOfAccountsInitializationService(
            repository=repository,
            position_provider=provider,
        )

        first = service.initialize(
            company=company,
            standard_chart_of_accounts=(
                _standard_chart_of_accounts()
            ),
            standard_account_taxonomy_concepts=(
                _standard_account_taxonomy_concepts()
            ),
            use_standard_defaults=True,
        )

        session.commit()

        custom_roles = AccountingAccountRoles(
            cash_accounts=frozenset(("1000",)),
            bank_accounts=frozenset(("1200",)),
            general_rate_sales_accounts=frozenset(("8400",)),
            customer_receivables=frozenset(("1410",)),
            supplier_payables=frozenset(("1600",)),
            customer_credit_balances=frozenset(("0755",)),
            supplier_credit_balances=frozenset(("1400",)),
        )
        repository.save_account_roles(
            company_id=company.company_id,
            account_roles=custom_roles,
        )

        second = service.initialize(
            company=company,
            standard_chart_of_accounts=(
                _standard_chart_of_accounts()
            ),
            standard_account_taxonomy_concepts=(
                _standard_account_taxonomy_concepts()
            ),
            use_standard_defaults=True,
        )

        loaded = repository.load_for_company(
            company_id=company.company_id,
            position_provider=provider,
        )
        loaded_roles = repository.load_account_roles(company.company_id)

    assert first is True
    assert second is False
    assert loaded is not None
    assert loaded_roles == custom_roles

    chart_of_accounts, _ = loaded

    assert {
        account.account_number
        for account in chart_of_accounts.accounts
            } == {
                "0755",
                "0855",
                "0846",
                "1000",
                "1200",
                "1400",
                "1410",
                "1600",
                "1610",
                "1571",
                "1576",
                "1771",
                "1776",
                "2970",
                "4830",
                "4900",
                "8020",
                "8021",
                "8400",
                "8500",
                "8990",
                "9000",
            }


def test_initializes_alternative_chart_with_explicit_configuration() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    company = Company(company_id=uuid4(), name="Alternative UG")
    chart = ChartOfAccountsTemplate(
        name="Custom",
        accounts=(
            TemplateAccount("7000", "Eigenkapital", AccountType.EQUITY),
            TemplateAccount("7001", "Verbindlichkeit", AccountType.LIABILITY),
            TemplateAccount("7002", "Aufwand", AccountType.EXPENSE),
            TemplateAccount("7003", "Ertrag", AccountType.REVENUE),
            TemplateAccount("7004", "Aktivkonto", AccountType.ASSET),
        ),
    )
    controls = AccountingControlAccounts(
        opening_balance_account="7000",
        income_summary_account="7000",
        profit_account="7000",
        loss_account="7000",
        profit_loss_carryforward_account="7000",
        statutory_reserve_account="7000",
        other_revenue_reserves_account="7000",
        distribution_liability_account="7001",
        depreciation_expense_account="7002",
        fixed_asset_disposal_gain_account="7003",
        fixed_asset_disposal_loss_account="7002",
    )
    vat = VatAccounts("7004", "7004", "7001", "7001")
    roles = AccountingAccountRoles(
        cash_accounts=frozenset(),
        bank_accounts=frozenset(),
        general_rate_sales_accounts=frozenset(),
    )

    with Session() as session:
        company_repository = CompanyRepository(session)
        repository = ChartOfAccountsRepository(session)
        company_repository.add(company, commit=False)
        company_repository.add_fiscal_year(
            company.company_id,
            FiscalYear(date(2026, 1, 1), date(2026, 12, 31)),
            commit=False,
        )
        service = ChartOfAccountsInitializationService(
            repository=repository,
            position_provider=_position_provider(),
        )
        assert service.initialize(
            company=company,
            standard_chart_of_accounts=chart,
            control_accounts=controls,
            vat_accounts=vat,
            account_roles=roles,
            standard_account_taxonomy_concepts={},
        )
        session.commit()
        loaded = repository.load_for_company(
            company_id=company.company_id,
            position_provider=_position_provider(),
        )

    assert loaded is not None
    loaded_chart, _accounts = loaded
    assert tuple(account.account_number for account in loaded_chart.accounts) == (
        "7000", "7001", "7002", "7003", "7004",
    )


def test_failed_new_chart_initialization_rolls_back_company_and_fiscal_year() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    company = Company(company_id=uuid4(), name="Rollback UG")
    chart = ChartOfAccountsTemplate(
        name="Incomplete",
        accounts=(
            TemplateAccount(
                account_number="7000",
                name="Customkonto",
                account_type=AccountType.ASSET,
            ),
        ),
    )
    controls = AccountingControlAccounts(
        opening_balance_account="9999",
        income_summary_account="9999",
        profit_account="9999",
        loss_account="9999",
        profit_loss_carryforward_account="9999",
        statutory_reserve_account="9999",
        other_revenue_reserves_account="9999",
        distribution_liability_account="9999",
        depreciation_expense_account="9999",
        fixed_asset_disposal_gain_account="9999",
        fixed_asset_disposal_loss_account="9999",
    )
    vat = VatAccounts("7000", "7000", "7000", "7000")
    roles = AccountingAccountRoles(
        cash_accounts=frozenset(),
        bank_accounts=frozenset(),
        general_rate_sales_accounts=frozenset(),
    )

    with Session() as session:
        company_repository = CompanyRepository(session)
        repository = ChartOfAccountsRepository(session)
        company_repository.add(company, commit=False)
        company_repository.add_fiscal_year(
            company.company_id,
            FiscalYear(date(2026, 1, 1), date(2026, 12, 31)),
            commit=False,
        )
        service = ChartOfAccountsInitializationService(
            repository=repository,
            position_provider=_position_provider(),
        )
        with pytest.raises(ValueError, match="Technische Konten"):
            service.initialize(
                company=company,
                standard_chart_of_accounts=chart,
                control_accounts=controls,
                vat_accounts=vat,
                account_roles=roles,
                standard_account_taxonomy_concepts={},
            )
        session.rollback()
        assert company_repository.get(company.company_id) is None
        assert repository.load_for_company(
            company_id=company.company_id,
            position_provider=_position_provider(),
        ) is None

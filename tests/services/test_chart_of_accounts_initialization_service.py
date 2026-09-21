"""Tests für die Initialisierung mandantenspezifischer Kontenrahmen."""

from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

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
from openbilanz.domain.account_type import AccountType
from openbilanz.domain.chart_of_accounts_template import (
    ChartOfAccountsTemplate,
)
from openbilanz.domain.company import Company
from openbilanz.domain.template_account import TemplateAccount
from openbilanz.hgb.balance_sheet_structure import (
    create_hgb_balance_sheet_structure,
)
from openbilanz.hgb.income_statement_structure import (
    create_hgb_income_statement_structure,
)
from openbilanz.services.chart_of_accounts_initialization_service import (
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
    assert loaded_account_taxonomy_concepts == {
        "4900": (
            "is.netIncome.regular.operatingTC."
            "otherCost.disposFixAss"
        ),
    }


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
        )

        session.commit()

        second = service.initialize(
            company=company,
            standard_chart_of_accounts=(
                _standard_chart_of_accounts()
            ),
            standard_account_taxonomy_concepts=(
                _standard_account_taxonomy_concepts()
            ),
        )

        loaded = repository.load_for_company(
            company_id=company.company_id,
            position_provider=provider,
        )

    assert first is True
    assert second is False
    assert loaded is not None

    chart_of_accounts, _ = loaded

    assert {
        account.account_number
        for account in chart_of_accounts.accounts
            } == {
                "1000",
                "1200",
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

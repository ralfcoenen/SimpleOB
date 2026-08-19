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
        accounts=tuple(
            TemplateAccount(
                account_number=number,
                name=name,
                account_type=AccountType.EQUITY,
            )
            for number, name in (
                ("9000", "Eröffnungsbilanzkonto"),
                ("8990", "GuV-Sammelkonto"),
                ("8020", "Jahresüberschuss"),
                ("8021", "Jahresfehlbetrag"),
            )
        ),
    )


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
        )

        session.commit()

        loaded = repository.load_control_accounts(
            company.company_id
        )

    assert initialized is True
    assert loaded is not None
    assert loaded.opening_balance_account == "9000"
    assert loaded.income_summary_account == "8990"
    assert loaded.profit_account == "8020"
    assert loaded.loss_account == "8021"


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
        )

        session.commit()

        second = service.initialize(
            company=company,
            standard_chart_of_accounts=(
                _standard_chart_of_accounts()
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
        "9000",
        "8990",
        "8020",
        "8021",
    }
    
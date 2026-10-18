"""PostgreSQL-Konkurrenztest für die mandantenbezogene Kontensperre."""

import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from simpleob.database.chart_of_accounts_repository import (
    ChartOfAccountsRepository,
)
from simpleob.database.company_repository import CompanyRepository
from simpleob.database.lock_error import DatabaseLockError
from simpleob.database.models import (
    Konto,
    KontenTaxonomieZuordnung,
    Mandant,
)
from simpleob.domain.company import Company


@pytest.fixture
def postgres_chart_of_accounts_data():
    """Erzeugt einen Mandanten ausschließlich in der Testdatenbank."""

    database_url = os.environ.get("SIMPLEOB_POSTGRES_TEST_URL")

    if not database_url:
        pytest.skip("SIMPLEOB_POSTGRES_TEST_URL ist nicht gesetzt.")

    url = make_url(database_url)

    if (
        url.drivername != "postgresql+psycopg"
        or url.database != "simpleob_migration_test"
        or url.host not in ("localhost", "127.0.0.1")
    ):
        pytest.fail(
            "Nur die lokale PostgreSQL-Datenbank "
            "'simpleob_migration_test' ist zulässig."
        )

    engine = create_engine(database_url)
    Session = sessionmaker(bind=engine)

    company = Company(
        company_id=uuid4(),
        name="PostgreSQL Kontensperre Test",
    )

    try:
        with Session() as session:
            CompanyRepository(session).add(company)

        yield Session, company

    finally:
        try:
            with Session() as session:
                company_model = session.scalar(
                    select(Mandant).where(
                        Mandant.company_id == str(company.company_id)
                    )
                )

                if company_model is not None:
                    session.query(
                        KontenTaxonomieZuordnung
                    ).filter(
                        KontenTaxonomieZuordnung.mandant_id
                        == company_model.id
                    ).delete(synchronize_session=False)

                    session.query(Konto).filter(
                        Konto.mandant_id == company_model.id
                    ).delete(synchronize_session=False)

                    session.delete(company_model)
                    session.commit()
        finally:
            engine.dispose()


def test_company_lock_conflict_and_retry(
    postgres_chart_of_accounts_data,
):
    """Sperrkonflikt führt zu Rollback; Wiederholung gelingt."""

    Session, company = postgres_chart_of_accounts_data

    with Session() as session_a, Session() as session_b:
        repository_a = ChartOfAccountsRepository(session_a)
        repository_b = ChartOfAccountsRepository(session_b)

        locked_company = repository_a._lock_company(
            company.company_id
        )

        assert locked_company.company_id == str(company.company_id)

        try:
            with pytest.raises(
                DatabaseLockError,
                match="Kontenverwaltung momentan gesperrt",
            ):
                repository_b._lock_company(
                    company.company_id
                )

            # Nach dem Sperrfehler muss Session B wieder
            # für Datenbankoperationen verwendbar sein.
            with Session() as check_session:
                company_model = check_session.scalar(
                    select(Mandant).where(
                        Mandant.company_id == str(company.company_id)
                    )
                )

                assert company_model is not None

        finally:
            session_a.rollback()

        # Nach Freigabe der Sperre muss dieselbe
        # Session B den Mandanten sperren können.
        retried_company = repository_b._lock_company(
            company.company_id
        )

        assert retried_company.company_id == str(company.company_id)

        session_b.rollback()


def test_add_account_lock_conflict_and_retry(
    postgres_chart_of_accounts_data,
):
    """Ein Konto wird erst nach Freigabe der Mandantensperre angelegt."""

    from simpleob.database.models import Konto
    from simpleob.domain.account import Account
    from simpleob.domain.account_type import AccountType
    from simpleob.domain.template_account import TemplateAccount

    Session, company = postgres_chart_of_accounts_data

    account = Account(
        template=TemplateAccount(
            account_number="1299",
            name="Zusätzliches Bankkonto",
            account_type=AccountType.ASSET,
        )
    )

    def add_account(session):
        ChartOfAccountsRepository(session).add_account(
            company_id=company.company_id,
            account=account,
            mapping_rule=None,
        )

    with Session() as session_a, Session() as session_b:
        repository_a = ChartOfAccountsRepository(session_a)

        repository_a._lock_company(company.company_id)

        try:
            with pytest.raises(
                DatabaseLockError,
                match="Kontenverwaltung momentan gesperrt",
            ):
                add_account(session_b)

            with Session() as check_session:
                company_model = check_session.scalar(
                    select(Mandant).where(
                        Mandant.company_id == str(company.company_id)
                    )
                )

                assert company_model is not None

                existing = check_session.scalar(
                    select(Konto).where(
                        Konto.mandant_id == company_model.id,
                        Konto.account_number == "1299",
                    )
                )

                assert existing is None

        finally:
            session_a.rollback()

        add_account(session_b)

    with Session() as check_session:
        company_model = check_session.scalar(
            select(Mandant).where(
                Mandant.company_id == str(company.company_id)
            )
        )

        assert company_model is not None

        persisted = check_session.scalar(
            select(Konto).where(
                Konto.mandant_id == company_model.id,
                Konto.account_number == "1299",
            )
        )

        assert persisted is not None
        assert persisted.name == "Zusätzliches Bankkonto"


def test_account_configuration_lock_conflict(
    postgres_chart_of_accounts_data,
):
    """Die Kontenkonfiguration respektiert die Mandantensperre."""

    from simpleob.domain.accounting_account_roles import (
        AccountingAccountRoles,
    )
    from simpleob.domain.accounting_control_accounts import (
        AccountingControlAccounts,
    )
    from simpleob.domain.vat_accounts import VatAccounts

    Session, company = postgres_chart_of_accounts_data

    control_accounts = AccountingControlAccounts(
        opening_balance_account="9000",
        income_summary_account="8990",
        profit_account="8020",
        loss_account="8021",
        profit_loss_carryforward_account="2970",
        statutory_reserve_account="0846",
        other_revenue_reserves_account="0855",
        distribution_liability_account="0755",
        depreciation_expense_account="4830",
        fixed_asset_disposal_gain_account="8500",
        fixed_asset_disposal_loss_account="4900",
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

    with Session() as session_a, Session() as session_b:
        ChartOfAccountsRepository(session_a)._lock_company(
            company.company_id
        )

        try:
            with pytest.raises(
                DatabaseLockError,
                match="Kontenverwaltung momentan gesperrt",
            ):
                ChartOfAccountsRepository(
                    session_b
                ).save_account_configuration(
                    company_id=company.company_id,
                    control_accounts=control_accounts,
                    vat_accounts=vat_accounts,
                    account_roles=account_roles,
                )

        finally:
            session_a.rollback()

        # Nach Freigabe muss die fachliche Prüfung
        # tatsächlich erreicht werden.
        with pytest.raises(
            ValueError,
            match="nicht vorhanden",
        ):
            ChartOfAccountsRepository(
                session_b
            ).save_account_configuration(
                company_id=company.company_id,
                control_accounts=control_accounts,
                vat_accounts=vat_accounts,
                account_roles=account_roles,
            )


def test_single_taxonomy_mapping_lock_conflict_and_retry(
    postgres_chart_of_accounts_data,
) -> None:
    """Sperrkonflikt verhindert Änderungen; Wiederholung gelingt."""

    from simpleob.domain.account import Account
    from simpleob.domain.account_type import AccountType
    from simpleob.domain.template_account import TemplateAccount

    Session, company = postgres_chart_of_accounts_data

    with Session() as session:
        repository = ChartOfAccountsRepository(session)

        repository.add_account(
            company_id=company.company_id,
            account=Account(
                template=TemplateAccount(
                    account_number="1400",
                    name="Forderungen",
                    account_type=AccountType.ASSET,
                )
            ),
            mapping_rule=None,
        )

    with Session() as session_a, Session() as session_b:
        repository_a = ChartOfAccountsRepository(session_a)
        repository_b = ChartOfAccountsRepository(session_b)

        repository_a.lock_company(company.company_id)

        try:
            with pytest.raises(
                DatabaseLockError,
                match="Kontenverwaltung momentan gesperrt",
            ):
                repository_b.save_single_account_taxonomy_concept(
                    company_id=company.company_id,
                    taxonomy_version="6.9",
                    account_number="1400",
                    concept_name="concept.receivable",
                )

        finally:
            session_a.rollback()

        # Dieselbe Session muss nach dem Sperrfehler erneut nutzbar sein.
        repository_b.save_single_account_taxonomy_concept(
            company_id=company.company_id,
            taxonomy_version="6.9",
            account_number="1400",
            concept_name="concept.receivable",
        )

    with Session() as session:
        repository = ChartOfAccountsRepository(session)

        assert repository.load_account_taxonomy_concepts(
            company.company_id,
            taxonomy_version="6.9",
        ) == {
            "1400": "concept.receivable",
        }

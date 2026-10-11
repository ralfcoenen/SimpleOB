"""PostgreSQL-Konkurrenztest für die Gesellschafterverwaltung."""

import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from openbilanz.database.company_repository import CompanyRepository
from openbilanz.database.lock_error import DatabaseLockError
from openbilanz.database.models import Gesellschafter, Mandant
from openbilanz.database.shareholder_repository import ShareholderRepository
from openbilanz.domain.company import Company
from openbilanz.domain.shareholder import Shareholder


@pytest.fixture
def postgres_shareholder_data():
    """Erzeugt einen temporären Mandanten in der PostgreSQL-Testdatenbank."""

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
            "Der Test darf ausschließlich auf der lokalen "
            "PostgreSQL-Testdatenbank simpleob_migration_test laufen."
        )

    engine = create_engine(database_url)
    Session = sessionmaker(bind=engine)

    company = Company(
        company_id=uuid4(),
        name="PostgreSQL Gesellschaftersperre Test",
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
                    session.delete(company_model)
                    session.commit()
        finally:
            engine.dispose()


def test_add_shareholder_lock_conflict_and_retry(
    postgres_shareholder_data,
):
    """Sperrkonflikt verhindert das Anlegen; danach gelingt es."""

    Session, company = postgres_shareholder_data

    shareholder = Shareholder(
        company_id=company.company_id,
        shareholder_number="1",
        name="Muster",
        first_name="Max",
        legal_status="NPP",
        share_numerator="1",
        share_denominator="2",
        tax_number="",
        tax_id="",
        wid="",
    )

    with Session() as session_a, Session() as session_b:
        repository_a = ShareholderRepository(session_a)
        repository_b = ShareholderRepository(session_b)

        repository_a._lock_company(company.company_id)

        try:
            with pytest.raises(
                DatabaseLockError,
                match="Gesellschafterverwaltung momentan gesperrt",
            ):
                repository_b.add(
                    shareholder=shareholder,
                )
        finally:
            session_a.rollback()

        with Session() as check_session:
            existing = check_session.scalar(
                select(Gesellschafter).where(
                    Gesellschafter.shareholder_id
                    == str(shareholder.shareholder_id)
                )
            )

            assert existing is None

        repository_b.add(
            shareholder=shareholder,
        )

        with Session() as check_session:
            loaded = ShareholderRepository(check_session).get(
                shareholder.shareholder_id
            )

            assert loaded == shareholder


def test_delete_shareholder_lock_conflict_and_retry(
    postgres_shareholder_data,
):
    """Löschen scheitert an der Sperre und gelingt nach Freigabe."""

    Session, company = postgres_shareholder_data

    shareholder = Shareholder(
        company_id=company.company_id,
        shareholder_number="1",
        name="Muster",
        first_name="Max",
        legal_status="NPP",
        share_numerator="1",
        share_denominator="2",
        tax_number="",
        tax_id="",
        wid="",
    )

    with Session() as setup_session:
        ShareholderRepository(setup_session).add(
            shareholder=shareholder
        )

    with Session() as session_a, Session() as session_b:
        repository_a = ShareholderRepository(session_a)
        repository_b = ShareholderRepository(session_b)

        # Der Gesellschafter ist in Sitzung B bereits geladen.
        assert repository_b.get(
            shareholder.shareholder_id
        ) == shareholder

        # Sitzung A hält die Mandantensperre.
        repository_a._lock_company(company.company_id)

        try:
            with pytest.raises(
                DatabaseLockError,
                match="Gesellschafterverwaltung momentan gesperrt",
            ):
                repository_b.delete(
                    shareholder_id=shareholder.shareholder_id
                )
        finally:
            session_a.rollback()

        # Der fehlgeschlagene Löschversuch darf
        # den Gesellschafter nicht entfernt haben.
        with Session() as check_session:
            assert ShareholderRepository(
                check_session
            ).get(shareholder.shareholder_id) == shareholder

        # Nach Freigabe muss das Löschen funktionieren.
        repository_b.delete(
            shareholder_id=shareholder.shareholder_id
        )

        with Session() as check_session:
            assert ShareholderRepository(
                check_session
            ).get(shareholder.shareholder_id) is None

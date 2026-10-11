"""PostgreSQL-Konkurrenztests für Unternehmensstammdaten."""

import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from openbilanz.database.company_repository import CompanyRepository
from openbilanz.database.lock_error import DatabaseLockError
from openbilanz.database.models import Mandant
from openbilanz.domain.company import Company
from openbilanz.domain.company_master_data import CompanyMasterData


@pytest.fixture
def postgres_company_master_data():
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
        name="PostgreSQL Stammdatenkonkurrenz Test",
    )

    original = CompanyMasterData(
        company=company,
        legal_form="UG (haftungsbeschränkt)",
        city="Musterstadt",
        country="DE",
    )

    try:
        with Session() as session:
            repository = CompanyRepository(session)
            repository.add(company)
            repository.save_master_data(original)

        yield Session, company, original

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


def test_master_data_lock_conflict_and_retry(
    postgres_company_master_data,
):
    """Eine fremde Zeilensperre verhindert das Speichern; danach gelingt es."""

    Session, company, original = postgres_company_master_data

    updated = CompanyMasterData(
        company=company,
        legal_form="UG (haftungsbeschränkt)",
        city="Berlin",
        country="DE",
    )

    with Session() as session_a, Session() as session_b:
        repository_b = CompanyRepository(session_b)

        # Sitzung A hält eine PostgreSQL-Zeilensperre.
        locked_company = session_a.scalar(
            select(Mandant)
            .where(Mandant.company_id == str(company.company_id))
            .with_for_update()
        )

        assert locked_company is not None

        try:
            with pytest.raises(
                DatabaseLockError,
                match="Unternehmensstammdaten momentan gesperrt",
            ):
                repository_b.save_master_data(
                    updated,
                    expected_master_data=original,
                )
        finally:
            session_a.rollback()

        # Nach dem Sperrfehler ist dieselbe Sitzung B wieder verwendbar.
        repository_b.save_master_data(
            updated,
            expected_master_data=original,
        )

    with Session() as check_session:
        loaded = CompanyRepository(
            check_session
        ).get_master_data(company.company_id)

        assert loaded == updated


def test_master_data_rejects_stale_snapshot(
    postgres_company_master_data,
):
    """Ein veralteter Dialogstand darf neuere Änderungen nicht überschreiben."""

    Session, company, original = postgres_company_master_data

    first_change = CompanyMasterData(
        company=company,
        legal_form="UG (haftungsbeschränkt)",
        city="Berlin",
        country="DE",
    )

    stale_change = CompanyMasterData(
        company=company,
        legal_form="UG (haftungsbeschränkt)",
        city="Hamburg",
        country="DE",
    )

    with Session() as session_a, Session() as session_b:
        repository_a = CompanyRepository(session_a)
        repository_b = CompanyRepository(session_b)

        # Beide Benutzer haben denselben ursprünglichen Stand geladen.
        assert repository_a.get_master_data(
            company.company_id
        ) == original

        assert repository_b.get_master_data(
            company.company_id
        ) == original

        # Benutzer A speichert seine Änderung.
        repository_a.save_master_data(
            first_change,
            expected_master_data=original,
        )

        # Benutzer B versucht mit dem veralteten Stand zu speichern.
        with pytest.raises(
            ValueError,
            match="zwischenzeitlich",
        ):
            repository_b.save_master_data(
                stale_change,
                expected_master_data=original,
            )

    with Session() as check_session:
        loaded = CompanyRepository(
            check_session
        ).get_master_data(company.company_id)

        assert loaded == first_change

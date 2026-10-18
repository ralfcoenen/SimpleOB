
"""PostgreSQL-Konkurrenztests für Bearbeitung und Löschung von Anlagegütern."""

import os
from dataclasses import replace
from datetime import date
from decimal import Decimal
from unittest.mock import Mock
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from simpleob.core.context import ApplicationContext
from simpleob.database.booking_repository import BookingRepository
from simpleob.database.company_repository import CompanyRepository
from simpleob.database.fixed_asset_depreciation_repository import (
    FixedAssetDepreciationRepository,
)
from simpleob.database.fixed_asset_movement_repository import (
    FixedAssetMovementRepository,
)
from simpleob.database.fixed_asset_repository import FixedAssetRepository
from simpleob.database.lock_error import DatabaseLockError
from simpleob.database.models import Mandant
from simpleob.domain.company import Company
from simpleob.domain.fiscal_year import FiscalYear
from simpleob.domain.fixed_asset import FixedAsset
from simpleob.services.fiscal_year_workspace import FiscalYearWorkspace


@pytest.fixture
def postgres_edit_delete_data():
    """Erzeugt isolierte Testdaten in der lokalen PostgreSQL-Testdatenbank."""

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
        name="PostgreSQL Anlagenbearbeitung Konkurrenztest",
    )
    fiscal_year = FiscalYear(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )
    asset = FixedAsset(
        company_id=company.company_id,
        asset_code="PG-EDIT-DELETE-0001",
        description="Testmaschine",
        position_code="HGB.266.AKTIVA.A.II.2",
        asset_account_number="0200",
        depreciation_expense_account_number="4830",
        acquisition_date=date(2026, 3, 15),
        acquisition_cost=Decimal("10000.00"),
        depreciation_start_date=date(2026, 3, 15),
        useful_life_months=60,
    )

    try:
        with Session() as session:
            company_repository = CompanyRepository(session)
            company_repository.add(company)
            company_repository.add_fiscal_year(
                company.company_id,
                fiscal_year,
            )
            FixedAssetRepository(session).add(fixed_asset=asset)

        yield Session, company, fiscal_year, asset

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


def _workspace(session, company, fiscal_year):
    """Erstellt einen Workspace mit gemeinsam genutzter Session."""

    return FiscalYearWorkspace(
        context=ApplicationContext(
            company=company,
            fiscal_year=fiscal_year,
        ),
        booking_repository=BookingRepository(session),
        company_repository=CompanyRepository(session),
        posting_service=Mock(),
        closing_workflow=Mock(),
        closing_consistency_service=Mock(),
        e_bilanz_preparation_service=Mock(),
        e_bilanz_service=Mock(),
        e_bilanz_account_detail_service=Mock(),
        e_bilanz_export_service=Mock(),
        taxonomy_management_service=Mock(),
        fixed_asset_repository=FixedAssetRepository(session),
        fixed_asset_movement_repository=FixedAssetMovementRepository(session),
        fixed_asset_depreciation_repository=(
            FixedAssetDepreciationRepository(session)
        ),
    )


def test_update_fixed_asset_lock_timeout_and_retry(
    postgres_edit_delete_data,
):
    """Eine gesperrte Bearbeitung verändert keine Stammdaten."""

    Session, company, fiscal_year, asset = postgres_edit_delete_data

    updated_asset = replace(
        asset,
        description="Geänderte Testmaschine",
        useful_life_months=48,
    )

    with Session() as session_a, Session() as session_b:
        CompanyRepository(session_a).lock_open_fiscal_year(
            company.company_id,
            fiscal_year,
        )

        workspace_b = _workspace(session_b, company, fiscal_year)

        try:
            with pytest.raises(DatabaseLockError):
                workspace_b.update_fixed_asset(updated_asset)

            with Session() as check_session:
                unchanged = FixedAssetRepository(check_session).get(
                    asset.fixed_asset_id
                )

                assert unchanged is not None
                assert unchanged.description == asset.description
                assert (
                    unchanged.useful_life_months
                    == asset.useful_life_months
                )

            session_a.commit()

            workspace_b.update_fixed_asset(updated_asset)

            with Session() as check_session:
                persisted = FixedAssetRepository(check_session).get(
                    asset.fixed_asset_id
                )

                assert persisted is not None
                assert persisted.description == updated_asset.description
                assert (
                    persisted.useful_life_months
                    == updated_asset.useful_life_months
                )

        finally:
            session_a.rollback()
            session_b.rollback()


def test_delete_fixed_asset_lock_timeout_and_retry(
    postgres_edit_delete_data,
):
    """Eine gesperrte Löschung entfernt kein Anlagegut."""

    Session, company, fiscal_year, asset = postgres_edit_delete_data

    with Session() as session_a, Session() as session_b:
        CompanyRepository(session_a).lock_open_fiscal_year(
            company.company_id,
            fiscal_year,
        )

        workspace_b = _workspace(session_b, company, fiscal_year)

        try:
            with pytest.raises(DatabaseLockError):
                workspace_b.delete_fixed_asset(asset.fixed_asset_id)

            with Session() as check_session:
                assert (
                    FixedAssetRepository(check_session).get(
                        asset.fixed_asset_id
                    )
                    is not None
                )

            session_a.commit()

            workspace_b.delete_fixed_asset(asset.fixed_asset_id)

            with Session() as check_session:
                assert (
                    FixedAssetRepository(check_session).get(
                        asset.fixed_asset_id
                    )
                    is None
                )

        finally:
            session_a.rollback()
            session_b.rollback()

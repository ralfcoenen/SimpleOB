
"""PostgreSQL-Konkurrenztest für die Anlagenabgangszuordnung."""

import os
from datetime import date
from decimal import Decimal
from unittest.mock import Mock
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, delete, select
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
from simpleob.database.models import (
    Anlagebewegung,
    Anlagegut,
    Mandant,
)
from simpleob.domain.booking import Booking
from simpleob.domain.booking_line import BookingLine
from simpleob.domain.company import Company
from simpleob.domain.entry_side import EntrySide
from simpleob.domain.fiscal_year import FiscalYear
from simpleob.domain.fixed_asset import FixedAsset
from simpleob.domain.fixed_asset_movement import FixedAssetMovement
from simpleob.domain.fixed_asset_movement_type import (
    FixedAssetMovementType,
)
from simpleob.domain.fixed_asset_status import FixedAssetStatus
from simpleob.services.fiscal_year_workspace import FiscalYearWorkspace


@pytest.fixture
def postgres_asset_data():
    """Bereitet isolierte Anlagen-Testdaten in PostgreSQL vor."""

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
        name="PostgreSQL Anlagenabgang Konkurrenztest",
    )
    fiscal_year = FiscalYear(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )
    asset = FixedAsset(
        company_id=company.company_id,
        asset_code="PG-ABGANG-0001",
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
            booking_repository = BookingRepository(session)

            company_repository.add(company)
            company_repository.add_fiscal_year(
                company.company_id,
                fiscal_year,
            )
            FixedAssetRepository(session).add(fixed_asset=asset)

            acquisition_booking = Booking(
                booking_date=date(2026, 3, 15),
                description="Anschaffung Testmaschine",
                lines=(
                    BookingLine(
                        account_number="0200",
                        side=EntrySide.DEBIT,
                        amount=Decimal("10000.00"),
                    ),
                    BookingLine(
                        account_number="1600",
                        side=EntrySide.CREDIT,
                        amount=Decimal("10000.00"),
                    ),
                ),
            )
            booking_repository.add(
                company_id=company.company_id,
                fiscal_year=fiscal_year,
                booking=acquisition_booking,
            )

            FixedAssetMovementRepository(session).add(
                movement=FixedAssetMovement(
                    fixed_asset_id=asset.fixed_asset_id,
                    fiscal_year_end=fiscal_year.end_date,
                    movement_date=date(2026, 3, 15),
                    amount=Decimal("10000.00"),
                    booking_id=acquisition_booking.booking_id,
                    movement_type=FixedAssetMovementType.ACQUISITION,
                ),
                booking_line_position=0,
            )

            disposal_booking = Booking(
                booking_date=date(2026, 8, 15),
                description="Abgang Testmaschine",
                lines=(
                    BookingLine(
                        account_number="4840",
                        side=EntrySide.DEBIT,
                        amount=Decimal("10000.00"),
                    ),
                    BookingLine(
                        account_number="0200",
                        side=EntrySide.CREDIT,
                        amount=Decimal("10000.00"),
                    ),
                ),
            )
            booking_repository.add(
                company_id=company.company_id,
                fiscal_year=fiscal_year,
                booking=disposal_booking,
            )

        yield Session, company, fiscal_year, asset, disposal_booking

    finally:
        try:
            with Session() as session:
                company_model = session.scalar(
                    select(Mandant).where(
                        Mandant.company_id == str(company.company_id)
                    )
                )

                if company_model is not None:
                    asset_ids = select(Anlagegut.id).where(
                        Anlagegut.mandant_id == company_model.id
                    )

                    session.execute(
                        delete(Anlagebewegung).where(
                            Anlagebewegung.anlagegut_id.in_(asset_ids)
                        )
                    )

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


def test_disposal_link_lock_timeout_and_retry(postgres_asset_data):
    """Sperrkonflikt verhindert Abgang; Wiederholung gelingt."""

    Session, company, fiscal_year, asset, disposal_booking = (
        postgres_asset_data
    )

    with Session() as session_a, Session() as session_b:
        CompanyRepository(session_a).lock_open_fiscal_year(
            company.company_id,
            fiscal_year,
        )

        workspace_b = _workspace(session_b, company, fiscal_year)

        try:
            with pytest.raises(DatabaseLockError) as error:
                workspace_b.link_fixed_asset_disposal(
                    fixed_asset_id=asset.fixed_asset_id,
                    booking_id=disposal_booking.booking_id,
                    booking_line_position=1,
                )

            assert "Geschäftsjahr momentan gesperrt" in str(
                error.value
            )

            with Session() as check_session:
                loaded = FixedAssetRepository(check_session).get(
                    asset.fixed_asset_id
                )
                assert loaded is not None
                assert loaded.status is FixedAssetStatus.ACTIVE

                movements = FixedAssetMovementRepository(
                    check_session
                ).list_for_fixed_asset(asset.fixed_asset_id)

                assert not any(
                    movement.movement_type
                    is FixedAssetMovementType.DISPOSAL
                    for movement in movements
                )

            session_a.commit()

            movement = workspace_b.link_fixed_asset_disposal(
                fixed_asset_id=asset.fixed_asset_id,
                booking_id=disposal_booking.booking_id,
                booking_line_position=1,
            )

            assert movement.movement_type is FixedAssetMovementType.DISPOSAL

            with Session() as check_session:
                loaded = FixedAssetRepository(check_session).get(
                    asset.fixed_asset_id
                )
                assert loaded is not None
                assert loaded.status is FixedAssetStatus.DISPOSED
                assert loaded.disposal_date == date(2026, 8, 15)

                movements = FixedAssetMovementRepository(
                    check_session
                ).list_for_fixed_asset(asset.fixed_asset_id)

                assert sum(
                    movement.movement_type
                    is FixedAssetMovementType.DISPOSAL
                    for movement in movements
                ) == 1

            with pytest.raises(
                ValueError,
                match="bereits abgegangen",
            ):
                workspace_b.link_fixed_asset_disposal(
                    fixed_asset_id=asset.fixed_asset_id,
                    booking_id=disposal_booking.booking_id,
                    booking_line_position=1,
                )

        finally:
            session_a.rollback()
            session_b.rollback()

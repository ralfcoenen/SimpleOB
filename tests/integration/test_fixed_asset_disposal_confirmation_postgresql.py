
"""PostgreSQL-Konkurrenztest für die Bestätigung eines Anlagenverkaufs."""

import os
from datetime import date
from decimal import Decimal
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, delete, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from simpleob.core.context import ApplicationContext
from simpleob.database.booking_repository import BookingRepository
from simpleob.database.company_repository import CompanyRepository
from simpleob.database.fixed_asset_repository import FixedAssetRepository
from simpleob.database.fixed_asset_movement_repository import (
    FixedAssetMovementRepository,
)
from simpleob.database.lock_error import DatabaseLockError
from simpleob.database.models import Anlagebewegung, Anlagegut, Mandant
from simpleob.domain.booking import Booking
from simpleob.domain.booking_line import BookingLine
from simpleob.domain.company import Company
from simpleob.domain.entry_side import EntrySide
from simpleob.domain.fiscal_year import FiscalYear
from simpleob.domain.fixed_asset import FixedAsset
from simpleob.domain.fixed_asset_disposal_calculation import (
    FixedAssetDisposalCalculation,
)
from simpleob.domain.fixed_asset_disposal_preview import (
    FixedAssetDisposalPreview,
)
from simpleob.domain.fixed_asset_movement import FixedAssetMovement
from simpleob.domain.fixed_asset_movement_type import (
    FixedAssetMovementType,
)
from simpleob.domain.fixed_asset_status import FixedAssetStatus
from simpleob.services.fiscal_year_workspace import FiscalYearWorkspace
from simpleob.services.fixed_asset_disposal_workflow import (
    FixedAssetDisposalWorkflow,
)


@pytest.fixture
def postgres_disposal_confirmation_data():
    """Erzeugt isolierte Daten ausschließlich in der Testdatenbank."""

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
        name="PostgreSQL Anlagenverkauf Bestätigungstest",
    )
    fiscal_year = FiscalYear(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )
    asset = FixedAsset(
        company_id=company.company_id,
        asset_code="PG-VERKAUF-0001",
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
    """Erstellt den Workspace und Workflow mit derselben Session."""

    booking_repository = BookingRepository(session)
    fixed_asset_repository = FixedAssetRepository(session)
    movement_repository = FixedAssetMovementRepository(session)

    workflow = FixedAssetDisposalWorkflow(
        session=session,
        booking_repository=booking_repository,
        movement_repository=movement_repository,
        fixed_asset_repository=fixed_asset_repository,
    )

    return FiscalYearWorkspace(
        context=ApplicationContext(
            company=company,
            fiscal_year=fiscal_year,
        ),
        booking_repository=booking_repository,
        company_repository=CompanyRepository(session),
        posting_service=Mock(),
        closing_workflow=Mock(),
        closing_consistency_service=Mock(),
        e_bilanz_preparation_service=Mock(),
        e_bilanz_service=Mock(),
        e_bilanz_account_detail_service=Mock(),
        e_bilanz_export_service=Mock(),
        taxonomy_management_service=Mock(),
        fixed_asset_repository=fixed_asset_repository,
        fixed_asset_movement_repository=movement_repository,
        fixed_asset_disposal_workflow=workflow,
    )


def test_disposal_confirmation_lock_timeout_and_retry(
    postgres_disposal_confirmation_data,
):
    """Sperrkonflikt verhindert den Verkauf; danach gelingt er."""

    Session, company, fiscal_year, asset = (
        postgres_disposal_confirmation_data
    )

    disposal_date = date(2026, 8, 15)

    booking = Booking(
        booking_date=disposal_date,
        voucher_no="PG-V-001",
        description="Verkauf Testmaschine",
        lines=(
            BookingLine(
                account_number="1200",
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

    calculation = FixedAssetDisposalCalculation(
        acquisition_cost=Decimal("10000.00"),
        accumulated_depreciation=Decimal("0.00"),
        carrying_amount=Decimal("10000.00"),
        gross_proceeds=Decimal("10000.00"),
        net_proceeds=Decimal("10000.00"),
        tax_amount=Decimal("0.00"),
        gain=Decimal("0.00"),
        loss=Decimal("0.00"),
        booking=booking,
    )

    preview = FixedAssetDisposalPreview(
        fixed_asset=asset,
        previous_depreciation=Decimal("0.00"),
        depreciation_proposal=None,
        accumulated_depreciation=Decimal("0.00"),
        disposal_calculation=calculation,
        tax_rate=0,
        counter_account_number="1200",
    )

    with Session() as session_a, Session() as session_b:
        CompanyRepository(session_a).lock_open_fiscal_year(
            company.company_id,
            fiscal_year,
        )

        workspace_b = _workspace(
            session_b,
            company,
            fiscal_year,
        )

        with patch.object(
            workspace_b,
            "build_fixed_asset_disposal_preview",
            return_value=preview,
        ):
            try:
                with pytest.raises(DatabaseLockError):
                    workspace_b.confirm_fixed_asset_disposal(preview)

                with Session() as check_session:
                    unchanged = FixedAssetRepository(
                        check_session
                    ).get(asset.fixed_asset_id)

                    assert unchanged is not None
                    assert unchanged.status is FixedAssetStatus.ACTIVE

                    bookings = BookingRepository(
                        check_session
                    ).list_for_fiscal_year(
                        company_id=company.company_id,
                        fiscal_year=fiscal_year,
                    )

                    assert all(
                        existing.booking_id != booking.booking_id
                        for existing in bookings
                    )

                    movements = FixedAssetMovementRepository(
                        check_session
                    ).list_for_fixed_asset(asset.fixed_asset_id)

                    assert not any(
                        movement.movement_type
                        is FixedAssetMovementType.DISPOSAL
                        for movement in movements
                    )

                session_a.commit()

                movement = workspace_b.confirm_fixed_asset_disposal(
                    preview
                )

                assert (
                    movement.movement_type
                    is FixedAssetMovementType.DISPOSAL
                )
                assert movement.booking_id == booking.booking_id

                with Session() as check_session:
                    persisted_asset = FixedAssetRepository(
                        check_session
                    ).get(asset.fixed_asset_id)

                    assert persisted_asset is not None
                    assert (
                        persisted_asset.status
                        is FixedAssetStatus.DISPOSED
                    )
                    assert persisted_asset.disposal_date == disposal_date

                    bookings = BookingRepository(
                        check_session
                    ).list_for_fiscal_year(
                        company_id=company.company_id,
                        fiscal_year=fiscal_year,
                    )

                    assert sum(
                        existing.booking_id == booking.booking_id
                        for existing in bookings
                    ) == 1

                    movements = FixedAssetMovementRepository(
                        check_session
                    ).list_for_fixed_asset(asset.fixed_asset_id)

                    assert sum(
                        existing.movement_type
                        is FixedAssetMovementType.DISPOSAL
                        for existing in movements
                    ) == 1

            finally:
                session_a.rollback()
                session_b.rollback()

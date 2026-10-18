
"""PostgreSQL-Konkurrenztest für die Abschreibungsbestätigung."""

import os
from datetime import date
from dataclasses import replace
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, delete, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

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
    Anlageabschreibung,
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
from simpleob.services.depreciation_booking_service import (
    DepreciationBookingService,
)
from simpleob.services.depreciation_service import DepreciationService
from simpleob.services.fixed_asset_depreciation_workflow import (
    FixedAssetDepreciationWorkflow,
)


@pytest.fixture
def postgres_depreciation_data():
    """Erstellt isolierte Testdaten in der lokalen PostgreSQL-Testdatenbank."""

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
        name="PostgreSQL Abschreibung Konkurrenztest",
    )
    fiscal_year = FiscalYear(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )
    asset = FixedAsset(
        company_id=company.company_id,
        asset_code="PG-AFA-0001",
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
                booking_date=asset.acquisition_date,
                description="Anschaffung Testmaschine",
                lines=(
                    BookingLine(
                        account_number=asset.asset_account_number,
                        side=EntrySide.DEBIT,
                        amount=asset.acquisition_cost,
                    ),
                    BookingLine(
                        account_number="1600",
                        side=EntrySide.CREDIT,
                        amount=asset.acquisition_cost,
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
                    movement_date=asset.acquisition_date,
                    amount=asset.acquisition_cost,
                    booking_id=acquisition_booking.booking_id,
                    movement_type=FixedAssetMovementType.ACQUISITION,
                ),
                booking_line_position=0,
            )

            proposal = DepreciationService().build_proposal(
                fixed_asset=asset,
                fiscal_year=fiscal_year,
                previous_depreciation=Decimal("0.00"),
                expense_account_number=(
                    asset.depreciation_expense_account_number
                ),
                asset_account_number=asset.asset_account_number,
            )
            assert proposal is not None

        yield (
            Session,
            company,
            fiscal_year,
            asset,
            acquisition_booking,
            proposal,
        )

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
                        delete(Anlageabschreibung).where(
                            Anlageabschreibung.anlagegut_id.in_(asset_ids)
                        )
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


def _workflow(session):
    """Erstellt den Workflow mit einer gemeinsamen Session."""

    return FixedAssetDepreciationWorkflow(
        session=session,
        booking_repository=BookingRepository(session),
        depreciation_repository=FixedAssetDepreciationRepository(session),
        booking_service=DepreciationBookingService(),
        company_repository=CompanyRepository(session),
        fixed_asset_repository=FixedAssetRepository(session),
        movement_repository=FixedAssetMovementRepository(session),
        depreciation_service=DepreciationService(),
    )


def test_depreciation_lock_timeout_and_retry(
    postgres_depreciation_data,
):
    """Sperrkonflikt verhindert Abschreibung; Wiederholung gelingt."""

    (
        Session,
        company,
        fiscal_year,
        asset,
        acquisition_booking,
        proposal,
    ) = postgres_depreciation_data

    with Session() as session_a, Session() as session_b:
        CompanyRepository(session_a).lock_open_fiscal_year(
            company.company_id,
            fiscal_year,
        )

        workflow_b = _workflow(session_b)

        try:
            with pytest.raises(DatabaseLockError) as error:
                workflow_b.confirm(
                    company_id=company.company_id,
                    fiscal_year=fiscal_year,
                    proposal=proposal,
                    asset_code=asset.asset_code,
                    asset_description=asset.description,
                )

            assert "Geschäftsjahr momentan gesperrt" in str(
                error.value
            )

            # Der fehlgeschlagene Versuch darf weder eine
            # Abschreibungsbuchung noch einen AfA-Datensatz erzeugen.
            with Session() as check_session:
                bookings = BookingRepository(
                    check_session
                ).list_for_fiscal_year(
                    company_id=company.company_id,
                    fiscal_year=fiscal_year,
                )
                depreciations = (
                    FixedAssetDepreciationRepository(
                        check_session
                    ).list_for_fixed_asset(asset.fixed_asset_id)
                )

                assert len(bookings) == 1
                assert (
                    bookings[0].booking_id
                    == acquisition_booking.booking_id
                )
                assert depreciations == ()

            # Nach Freigabe der Sperre muss dieselbe Session B
            # den Vorschlag erfolgreich bestätigen können.
            session_a.commit()

            result = workflow_b.confirm(
                company_id=company.company_id,
                fiscal_year=fiscal_year,
                proposal=proposal,
                asset_code=asset.asset_code,
                asset_description=asset.description,
            )

            assert result.fixed_asset_id == asset.fixed_asset_id
            assert result.amount == proposal.amount

            with Session() as check_session:
                bookings = BookingRepository(
                    check_session
                ).list_for_fiscal_year(
                    company_id=company.company_id,
                    fiscal_year=fiscal_year,
                )
                depreciations = (
                    FixedAssetDepreciationRepository(
                        check_session
                    ).list_for_fixed_asset(asset.fixed_asset_id)
                )

                assert len(bookings) == 2
                assert len(depreciations) == 1
                assert depreciations[0] == result
                assert result.booking_id in {
                    booking.booking_id for booking in bookings
                }
                assert (
                    result.booking_id
                    != acquisition_booking.booking_id
                )

            # Eine erneute Bestätigung muss abgelehnt werden.
            with pytest.raises(
                ValueError,
                match="bereits eine Abschreibung bestätigt",
            ):
                workflow_b.confirm(
                    company_id=company.company_id,
                    fiscal_year=fiscal_year,
                    proposal=proposal,
                    asset_code=asset.asset_code,
                    asset_description=asset.description,
                )

        finally:
            session_a.rollback()
            session_b.rollback()


def test_rejects_proposal_after_concurrent_asset_update(
    postgres_depreciation_data,
):
    """Eine zwischenzeitliche Anlagenänderung macht den Vorschlag ungültig."""

    (
        Session,
        company,
        fiscal_year,
        asset,
        acquisition_booking,
        proposal,
    ) = postgres_depreciation_data

    with Session() as session_a, Session() as session_b:
        asset_repository_b = FixedAssetRepository(session_b)

        # Session B lädt die Anlage vor der Änderung durch A.
        loaded_asset_b = asset_repository_b.get(asset.fixed_asset_id)
        assert loaded_asset_b is not None
        assert loaded_asset_b.useful_life_months == 60

        # Session A verändert die Nutzungsdauer und speichert sie.
        updated_asset = replace(
            asset,
            useful_life_months=48,
        )

        FixedAssetRepository(session_a).update(
            fixed_asset=updated_asset,
        )

        # Session B versucht, ihren alten Vorschlag zu bestätigen.
        workflow_b = _workflow(session_b)

        with pytest.raises(
            ValueError,
            match="nicht mehr aktuell",
        ):
            workflow_b.confirm(
                company_id=company.company_id,
                fiscal_year=fiscal_year,
                proposal=proposal,
                asset_code=asset.asset_code,
                asset_description=asset.description,
            )

    # Der fehlgeschlagene Versuch darf nichts gebucht haben.
    with Session() as check_session:
        bookings = BookingRepository(
            check_session
        ).list_for_fiscal_year(
            company_id=company.company_id,
            fiscal_year=fiscal_year,
        )

        depreciations = (
            FixedAssetDepreciationRepository(
                check_session
            ).list_for_fixed_asset(asset.fixed_asset_id)
        )

        assert len(bookings) == 1
        assert bookings[0].booking_id == acquisition_booking.booking_id
        assert depreciations == ()

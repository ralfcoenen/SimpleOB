
"""PostgreSQL-Konkurrenztest für steuerliche AfA-Abweichungen."""

import os
from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, delete, select, text
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
    SteuerlicheAfaAbweichung,
)
from simpleob.database.tax_depreciation_adjustment_repository import (
    TaxDepreciationAdjustmentRepository,
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
def postgres_tax_adjustment_data():
    """Erstellt eine bestätigte Abschreibung in der lokalen Testdatenbank."""

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
            "Nur die lokale PostgreSQL-Testdatenbank "
            "'simpleob_migration_test' ist zulässig."
        )

    engine = create_engine(database_url)
    Session = sessionmaker(bind=engine)

    company = Company(
        company_id=uuid4(),
        name="PostgreSQL steuerliche AfA Konkurrenztest",
    )

    fiscal_year = FiscalYear(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )

    asset = FixedAsset(
        company_id=company.company_id,
        asset_code="PG-TAX-AFA-0001",
        description="Testanlage",
        position_code="HGB.266.AKTIVA.A.II.3",
        asset_account_number="0690",
        depreciation_expense_account_number="4830",
        acquisition_date=date(2026, 3, 15),
        acquisition_cost=Decimal("2400.00"),
        depreciation_start_date=date(2026, 4, 1),
        useful_life_months=36,
    )

    try:
        with Session() as session:
            company_repository = CompanyRepository(session)
            booking_repository = BookingRepository(session)
            asset_repository = FixedAssetRepository(session)
            depreciation_repository = FixedAssetDepreciationRepository(
                session
            )
            movement_repository = FixedAssetMovementRepository(session)
            depreciation_service = DepreciationService()

            company_repository.add(company)
            company_repository.add_fiscal_year(
                company.company_id,
                fiscal_year,
            )
            asset_repository.add(fixed_asset=asset)

            acquisition_booking = Booking(
                booking_date=asset.acquisition_date,
                description="Anschaffung Testanlage",
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

            movement_repository.add(
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

            proposal = depreciation_service.build_proposal(
                fixed_asset=asset,
                fiscal_year=fiscal_year,
                previous_depreciation=Decimal("0.00"),
                expense_account_number=(
                    asset.depreciation_expense_account_number
                ),
                asset_account_number=asset.asset_account_number,
            )

            assert proposal is not None
            assert proposal.amount == Decimal("600.00")

            workflow = FixedAssetDepreciationWorkflow(
                session=session,
                booking_repository=booking_repository,
                depreciation_repository=depreciation_repository,
                booking_service=DepreciationBookingService(),
                company_repository=company_repository,
                fixed_asset_repository=asset_repository,
                movement_repository=movement_repository,
                depreciation_service=depreciation_service,
            )

            depreciation = workflow.confirm(
                company_id=company.company_id,
                fiscal_year=fiscal_year,
                proposal=proposal,
                asset_code=asset.asset_code,
                asset_description=asset.description,
            )

        yield Session, company, depreciation

    finally:
        try:
            with Session() as session:
                company_model = session.scalar(
                    select(Mandant).where(
                        Mandant.company_id == str(company.company_id)
                    )
                )

                if company_model is not None:
                    depreciation_ids = select(
                        Anlageabschreibung.id
                    ).join(
                        Anlagegut,
                        Anlageabschreibung.anlagegut_id == Anlagegut.id,
                    ).where(
                        Anlagegut.mandant_id == company_model.id
                    )

                    session.execute(
                        delete(SteuerlicheAfaAbweichung).where(
                            SteuerlicheAfaAbweichung.anlageabschreibung_id.in_(
                                depreciation_ids
                            )
                        )
                    )

                    session.execute(
                        delete(Anlageabschreibung).where(
                            Anlageabschreibung.id.in_(depreciation_ids)
                        )
                    )

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


def test_tax_adjustment_lock_conflict_and_retry(
    postgres_tax_adjustment_data,
):
    """Ein Sperrkonflikt verhindert das Speichern; danach gelingt es."""

    Session, company, depreciation = postgres_tax_adjustment_data

    depreciation_id = depreciation.depreciation_id
    tax_amount = Decimal("550.00")

    with Session() as session_a, Session() as session_b:
        repository_b = TaxDepreciationAdjustmentRepository(session_b)

        # Sitzung A hält die Sperre auf der Abschreibung.
        session_a.execute(
            text("SELECT set_config('lock_timeout', '3000ms', true)")
        )
        locked = session_a.scalar(
            select(Anlageabschreibung)
            .where(
                Anlageabschreibung.depreciation_id
                == str(depreciation_id)
            )
            .with_for_update()
        )
        assert locked is not None

        try:
            with pytest.raises(
                DatabaseLockError,
                match="Steuerliche AfA-Anpassung momentan gesperrt",
            ):
                repository_b.save(
                    depreciation_id=depreciation_id,
                    tax_amount=tax_amount,
                )
        finally:
            session_a.rollback()

        # Der fehlgeschlagene Versuch darf nichts gespeichert haben.
        with Session() as check_session:
            assert TaxDepreciationAdjustmentRepository(
                check_session
            ).get_for_depreciation(depreciation_id) is None

        # Dieselbe Sitzung B muss nach dem Rollback wieder nutzbar sein.
        result = repository_b.save(
            depreciation_id=depreciation_id,
            tax_amount=tax_amount,
        )

        assert result is not None
        assert result.commercial_amount == Decimal("600.00")
        assert result.tax_amount == tax_amount

        with Session() as check_session:
            saved = TaxDepreciationAdjustmentRepository(
                check_session
            ).get_for_depreciation(depreciation_id)

            assert saved is not None
            assert saved.tax_amount == tax_amount

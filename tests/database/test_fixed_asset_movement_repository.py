"""Tests für die Persistenz von Anlagenbewegungen."""

from datetime import date
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from simpleob.database.booking_repository import (
    BookingRepository,
)
from simpleob.database.company_repository import (
    CompanyRepository,
)
from simpleob.database.database import Base
from simpleob.database.fixed_asset_movement_repository import (
    FixedAssetMovementRepository,
)
from simpleob.database.fixed_asset_repository import (
    FixedAssetRepository,
)
from simpleob.domain.booking import Booking
from simpleob.domain.booking_line import BookingLine
from simpleob.domain.company import Company
from simpleob.domain.entry_side import EntrySide
from simpleob.domain.fiscal_year import FiscalYear
from simpleob.domain.fixed_asset import FixedAsset
from simpleob.domain.fixed_asset_movement import (
    FixedAssetMovement,
)
from simpleob.domain.fixed_asset_movement_type import (
    FixedAssetMovementType,
)


def _prepare_database():
    """Erzeugt die gemeinsame Testgrundlage."""

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

    fiscal_year = FiscalYear(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )

    asset = FixedAsset(
        company_id=company.company_id,
        asset_code="A-0001",
        description="Maschine",
        position_code="HGB.266.AKTIVA.A.II.2",
        asset_account_number="0200",
        depreciation_expense_account_number="4830",
        acquisition_date=date(2026, 3, 15),
        acquisition_cost=Decimal("10000.00"),
        depreciation_start_date=date(2026, 3, 15),
        useful_life_months=60,
    )

    return Session, company, fiscal_year, asset


def _add_master_data(
    *,
    session,
    company,
    fiscal_year,
    asset,
) -> None:
    """Persistiert Mandant, Geschäftsjahr und Anlagegut."""

    company_repository = CompanyRepository(
        session
    )

    company_repository.add(
        company
    )

    company_repository.add_fiscal_year(
        company.company_id,
        fiscal_year,
    )

    FixedAssetRepository(
        session
    ).add(
        fixed_asset=asset
    )


def _add_booking(
    *,
    session,
    company,
    fiscal_year,
    booking_date,
    amount,
) -> Booking:
    """Erzeugt und persistiert eine Testbuchung."""

    booking = Booking(
        booking_date=booking_date,
        description="Anlagenbewegung",
        lines=(
            BookingLine(
                account_number="0200",
                side=EntrySide.DEBIT,
                amount=amount,
            ),
            BookingLine(
                account_number="1600",
                side=EntrySide.CREDIT,
                amount=amount,
            ),
        ),
    )

    BookingRepository(
        session
    ).add(
        company_id=company.company_id,
        fiscal_year=fiscal_year,
        booking=booking,
    )

    return booking


def test_adds_and_loads_acquisition_movement() -> None:
    Session, company, fiscal_year, asset = (
        _prepare_database()
    )

    with Session() as session:
        _add_master_data(
            session=session,
            company=company,
            fiscal_year=fiscal_year,
            asset=asset,
        )

        booking = _add_booking(
            session=session,
            company=company,
            fiscal_year=fiscal_year,
            booking_date=date(2026, 3, 15),
            amount=Decimal("10000.00"),
        )

        movement = FixedAssetMovement(
            fixed_asset_id=asset.fixed_asset_id,
            fiscal_year_end=fiscal_year.end_date,
            movement_date=date(2026, 3, 15),
            amount=Decimal("10000.00"),
            booking_id=booking.booking_id,
            movement_type=(
                FixedAssetMovementType.ACQUISITION
            ),
        )

        repository = FixedAssetMovementRepository(
            session
        )

        repository.add(
            movement=movement,
            booking_line_position=0,
        )

        loaded = repository.get(
            movement.movement_id
        )

    assert loaded == movement


def test_lists_movements_for_fixed_asset_chronologically() -> None:
    Session, company, fiscal_year, asset = (
        _prepare_database()
    )

    with Session() as session:
        _add_master_data(
            session=session,
            company=company,
            fiscal_year=fiscal_year,
            asset=asset,
        )

        later_booking = _add_booking(
            session=session,
            company=company,
            fiscal_year=fiscal_year,
            booking_date=date(2026, 10, 1),
            amount=Decimal("5000.00"),
        )

        earlier_booking = _add_booking(
            session=session,
            company=company,
            fiscal_year=fiscal_year,
            booking_date=date(2026, 3, 15),
            amount=Decimal("10000.00"),
        )

        later_movement = FixedAssetMovement(
            fixed_asset_id=asset.fixed_asset_id,
            fiscal_year_end=fiscal_year.end_date,
            movement_date=date(2026, 10, 1),
            amount=Decimal("5000.00"),
            booking_id=later_booking.booking_id,
            movement_type=(
                FixedAssetMovementType.DISPOSAL
            ),
        )

        earlier_movement = FixedAssetMovement(
            fixed_asset_id=asset.fixed_asset_id,
            fiscal_year_end=fiscal_year.end_date,
            movement_date=date(2026, 3, 15),
            amount=Decimal("10000.00"),
            booking_id=earlier_booking.booking_id,
            movement_type=(
                FixedAssetMovementType.ACQUISITION
            ),
        )

        repository = FixedAssetMovementRepository(
            session
        )

        repository.add(
            movement=later_movement,
            booking_line_position=0,
        )

        repository.add(
            movement=earlier_movement,
            booking_line_position=0,
        )

        loaded = repository.list_for_fixed_asset(
            asset.fixed_asset_id
        )

    assert loaded == (
        earlier_movement,
        later_movement,
    )


def test_lists_movements_for_fixed_asset_with_booking_line_positions() -> None:
    Session, company, fiscal_year, asset = (
        _prepare_database()
    )

    with Session() as session:
        _add_master_data(
            session=session,
            company=company,
            fiscal_year=fiscal_year,
            asset=asset,
        )

        booking = _add_booking(
            session=session,
            company=company,
            fiscal_year=fiscal_year,
            booking_date=date(2026, 3, 15),
            amount=Decimal("10000.00"),
        )

        movement = FixedAssetMovement(
            fixed_asset_id=asset.fixed_asset_id,
            fiscal_year_end=fiscal_year.end_date,
            movement_date=date(2026, 3, 15),
            amount=Decimal("10000.00"),
            booking_id=booking.booking_id,
            movement_type=(
                FixedAssetMovementType.ACQUISITION
            ),
        )

        repository = FixedAssetMovementRepository(
            session
        )

        repository.add(
            movement=movement,
            booking_line_position=1,
        )

        loaded = (
            repository.list_with_positions_for_fixed_asset(
                asset.fixed_asset_id
            )
        )

    assert loaded == (
        (movement, 1),
    )


def test_preserves_disposal_reversal_with_different_amount() -> None:
    Session, company, fiscal_year, asset = (
        _prepare_database()
    )

    with Session() as session:
        _add_master_data(
            session=session,
            company=company,
            fiscal_year=fiscal_year,
            asset=asset,
        )

        disposal_booking = _add_booking(
            session=session,
            company=company,
            fiscal_year=fiscal_year,
            booking_date=date(2026, 10, 1),
            amount=Decimal("7500.00"),
        )

        reversal_booking = _add_booking(
            session=session,
            company=company,
            fiscal_year=fiscal_year,
            booking_date=date(2026, 10, 2),
            amount=Decimal("7500.00"),
        )

        disposal = FixedAssetMovement(
            fixed_asset_id=asset.fixed_asset_id,
            fiscal_year_end=fiscal_year.end_date,
            movement_date=date(2026, 10, 1),
            amount=Decimal("10000.00"),
            booking_id=disposal_booking.booking_id,
            movement_type=(
                FixedAssetMovementType.DISPOSAL
            ),
        )

        reversal = FixedAssetMovement(
            fixed_asset_id=asset.fixed_asset_id,
            fiscal_year_end=fiscal_year.end_date,
            movement_date=date(2026, 10, 2),
            amount=Decimal("10000.00"),
            booking_id=reversal_booking.booking_id,
            movement_type=(
                FixedAssetMovementType.REVERSAL
            ),
            reversed_movement_id=(
                disposal.movement_id
            ),
        )

        repository = FixedAssetMovementRepository(
            session
        )

        repository.add(
            movement=disposal,
            booking_line_position=0,
        )

        repository.add(
            movement=reversal,
            booking_line_position=0,
        )

        loaded_disposal = repository.get(
            disposal.movement_id
        )
        loaded_reversal = repository.get(
            reversal.movement_id
        )

    assert loaded_disposal == disposal
    assert loaded_reversal == reversal
    assert (
        loaded_reversal.reversed_movement_id
        == disposal.movement_id
    )

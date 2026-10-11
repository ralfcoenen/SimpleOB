
"""Tests für die atomare Bestätigung von Anlagenabschreibungen."""

from dataclasses import replace
from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from openbilanz.database.booking_repository import BookingRepository
from openbilanz.database.company_repository import CompanyRepository
from openbilanz.database.database import Base
from openbilanz.database.fixed_asset_depreciation_repository import (
    FixedAssetDepreciationRepository,
)
from openbilanz.database.fixed_asset_movement_repository import (
    FixedAssetMovementRepository,
)
from openbilanz.database.fixed_asset_repository import FixedAssetRepository
from openbilanz.domain.booking import Booking
from openbilanz.domain.booking_line import BookingLine
from openbilanz.domain.company import Company
from openbilanz.domain.depreciation_kind import DepreciationKind
from openbilanz.domain.depreciation_proposal import DepreciationProposal
from openbilanz.domain.depreciation_source import DepreciationSource
from openbilanz.domain.entry_side import EntrySide
from openbilanz.domain.fiscal_year import FiscalYear
from openbilanz.domain.fixed_asset import FixedAsset
from openbilanz.domain.fixed_asset_movement import FixedAssetMovement
from openbilanz.domain.fixed_asset_movement_type import (
    FixedAssetMovementType,
)
from openbilanz.services.depreciation_booking_service import (
    DepreciationBookingService,
)
from openbilanz.services.depreciation_service import DepreciationService
from openbilanz.services.fixed_asset_depreciation_workflow import (
    FixedAssetDepreciationWorkflow,
)


def _fiscal_year() -> FiscalYear:
    return FiscalYear(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )


def _fixed_asset(*, company_id) -> FixedAsset:
    return FixedAsset(
        company_id=company_id,
        asset_code="A-0001",
        description="MacBook Pro",
        position_code="HGB.266.AKTIVA.A.II.3",
        asset_account_number="0690",
        depreciation_expense_account_number="4830",
        acquisition_date=date(2026, 3, 15),
        acquisition_cost=Decimal("2400.00"),
        depreciation_start_date=date(2026, 3, 15),
        useful_life_months=36,
    )


def _proposal(*, fixed_asset_id) -> DepreciationProposal:
    return DepreciationProposal(
        fixed_asset_id=fixed_asset_id,
        depreciation_date=date(2026, 12, 31),
        amount=Decimal("600.00"),
        expense_account_number="4830",
        asset_account_number="0690",
    )


def _workflow(session: Session) -> FixedAssetDepreciationWorkflow:
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


@pytest.fixture
def prepared_asset():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionFactory = sessionmaker(bind=engine)

    company = Company(
        company_id=uuid4(),
        name="Muster UG",
    )
    fiscal_year = _fiscal_year()
    asset = _fixed_asset(company_id=company.company_id)

    try:
        with SessionFactory() as session:
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
                description="Anschaffung MacBook Pro",
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
            SessionFactory,
            company,
            fiscal_year,
            asset,
            acquisition_booking,
            proposal,
        )
    finally:
        engine.dispose()


def test_confirms_depreciation_atomically(prepared_asset) -> None:
    (
        SessionFactory,
        company,
        fiscal_year,
        asset,
        acquisition_booking,
        proposal,
    ) = prepared_asset

    with SessionFactory() as session:
        workflow = _workflow(session)

        result = workflow.confirm(
            company_id=company.company_id,
            fiscal_year=fiscal_year,
            proposal=proposal,
            asset_code=asset.asset_code,
            asset_description=asset.description,
        )

        bookings = BookingRepository(session).list_for_fiscal_year(
            company_id=company.company_id,
            fiscal_year=fiscal_year,
        )
        depreciations = (
            FixedAssetDepreciationRepository(session).list_for_fixed_asset(
                asset.fixed_asset_id
            )
        )

    assert len(bookings) == 2
    assert len(depreciations) == 1
    assert result == depreciations[0]
    assert result.booking_id != acquisition_booking.booking_id
    assert result.booking_id in {
        booking.booking_id for booking in bookings
    }
    assert result.fixed_asset_id == asset.fixed_asset_id
    assert result.amount == proposal.amount
    assert result.kind is DepreciationKind.LINEAR
    assert result.source is DepreciationSource.CALCULATED


def test_rejects_duplicate_depreciation(prepared_asset) -> None:
    (
        SessionFactory,
        company,
        fiscal_year,
        asset,
        _,
        proposal,
    ) = prepared_asset

    with SessionFactory() as session:
        workflow = _workflow(session)

        workflow.confirm(
            company_id=company.company_id,
            fiscal_year=fiscal_year,
            proposal=proposal,
            asset_code=asset.asset_code,
            asset_description=asset.description,
        )

        with pytest.raises(
            ValueError,
            match="bereits eine Abschreibung bestätigt",
        ):
            workflow.confirm(
                company_id=company.company_id,
                fiscal_year=fiscal_year,
                proposal=proposal,
                asset_code=asset.asset_code,
                asset_description=asset.description,
            )

    with SessionFactory() as session:
        bookings = BookingRepository(session).list_for_fiscal_year(
            company_id=company.company_id,
            fiscal_year=fiscal_year,
        )
        depreciations = (
            FixedAssetDepreciationRepository(session).list_for_fixed_asset(
                asset.fixed_asset_id
            )
        )

    assert len(bookings) == 2
    assert len(depreciations) == 1


def test_rejects_stale_depreciation_proposal(prepared_asset) -> None:
    (
        SessionFactory,
        company,
        fiscal_year,
        asset,
        acquisition_booking,
        proposal,
    ) = prepared_asset

    stale_proposal = replace(
        proposal,
        amount=proposal.amount + Decimal("1.00"),
    )

    with SessionFactory() as session:
        workflow = _workflow(session)

        with pytest.raises(
            ValueError,
            match="nicht mehr aktuell",
        ):
            workflow.confirm(
                company_id=company.company_id,
                fiscal_year=fiscal_year,
                proposal=stale_proposal,
                asset_code=asset.asset_code,
                asset_description=asset.description,
            )

    with SessionFactory() as session:
        bookings = BookingRepository(session).list_for_fiscal_year(
            company_id=company.company_id,
            fiscal_year=fiscal_year,
        )
        depreciations = (
            FixedAssetDepreciationRepository(session).list_for_fixed_asset(
                asset.fixed_asset_id
            )
        )

    assert len(bookings) == 1
    assert bookings[0].booking_id == acquisition_booking.booking_id
    assert depreciations == ()


def test_rolls_back_booking_when_depreciation_fails() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionFactory = sessionmaker(bind=engine)

    company = Company(
        company_id=uuid4(),
        name="Muster UG",
    )
    fiscal_year = _fiscal_year()
    unknown_fixed_asset_id = uuid4()

    try:
        with SessionFactory() as session:
            company_repository = CompanyRepository(session)
            company_repository.add(company)
            company_repository.add_fiscal_year(
                company.company_id,
                fiscal_year,
            )

            workflow = _workflow(session)

            with pytest.raises(
                ValueError,
                match="Anlagegut ist nicht vorhanden",
            ):
                workflow.confirm(
                    company_id=company.company_id,
                    fiscal_year=fiscal_year,
                    proposal=_proposal(
                        fixed_asset_id=unknown_fixed_asset_id
                    ),
                    asset_code="A-9999",
                    asset_description="Unbekanntes Anlagegut",
                )

        with SessionFactory() as session:
            bookings = BookingRepository(session).list_for_fiscal_year(
                company_id=company.company_id,
                fiscal_year=fiscal_year,
            )

        assert bookings == ()
    finally:
        engine.dispose()

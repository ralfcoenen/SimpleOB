"""Tests für die atomare Bestätigung von Anlagenabschreibungen."""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from openbilanz.database.booking_repository import (
    BookingRepository,
)
from openbilanz.database.company_repository import (
    CompanyRepository,
)
from openbilanz.database.database import Base
from openbilanz.database.fixed_asset_depreciation_repository import (
    FixedAssetDepreciationRepository,
)
from openbilanz.database.fixed_asset_repository import (
    FixedAssetRepository,
)
from openbilanz.domain.company import Company
from openbilanz.domain.depreciation_kind import (
    DepreciationKind,
)
from openbilanz.domain.depreciation_proposal import (
    DepreciationProposal,
)
from openbilanz.domain.depreciation_source import (
    DepreciationSource,
)
from openbilanz.domain.fiscal_year import FiscalYear
from openbilanz.domain.fixed_asset import FixedAsset
from openbilanz.services.depreciation_booking_service import (
    DepreciationBookingService,
)
from openbilanz.services.fixed_asset_depreciation_workflow import (
    FixedAssetDepreciationWorkflow,
)


def _fiscal_year() -> FiscalYear:
    return FiscalYear(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )


def _fixed_asset(
    *,
    company_id,
) -> FixedAsset:
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


def _proposal(
    *,
    fixed_asset_id,
) -> DepreciationProposal:
    return DepreciationProposal(
        fixed_asset_id=fixed_asset_id,
        depreciation_date=date(2026, 12, 31),
        amount=Decimal("600.00"),
        expense_account_number="4830",
        asset_account_number="0690",
    )


def test_confirms_depreciation_atomically() -> None:
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
    fiscal_year = _fiscal_year()

    asset = _fixed_asset(
        company_id=company.company_id
    )

    with Session() as session:
        company_repository = CompanyRepository(
            session
        )
        booking_repository = BookingRepository(
            session
        )
        asset_repository = FixedAssetRepository(
            session
        )
        depreciation_repository = (
            FixedAssetDepreciationRepository(
                session
            )
        )

        company_repository.add(
            company
        )
        company_repository.add_fiscal_year(
            company.company_id,
            fiscal_year,
        )
        asset_repository.add(
            fixed_asset=asset
        )

        workflow = FixedAssetDepreciationWorkflow(
            session=session,
            booking_repository=booking_repository,
            depreciation_repository=(
                depreciation_repository
            ),
            booking_service=(
                DepreciationBookingService()
            ),
        )

        result = workflow.confirm(
            company_id=company.company_id,
            fiscal_year=fiscal_year,
            proposal=_proposal(
                fixed_asset_id=asset.fixed_asset_id
            ),
            asset_code=asset.asset_code,
        )

        bookings = (
            booking_repository.list_for_fiscal_year(
                company_id=company.company_id,
                fiscal_year=fiscal_year,
            )
        )

        depreciations = (
            depreciation_repository.list_for_fixed_asset(
                asset.fixed_asset_id
            )
        )

    assert len(bookings) == 1
    assert len(depreciations) == 1

    assert result == depreciations[0]
    assert result.booking_id == bookings[0].booking_id
    assert result.fixed_asset_id == asset.fixed_asset_id
    assert result.amount == Decimal("600.00")
    assert result.kind is DepreciationKind.LINEAR
    assert result.source is DepreciationSource.CALCULATED


def test_rolls_back_booking_when_depreciation_fails() -> None:
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
    fiscal_year = _fiscal_year()

    unknown_fixed_asset_id = uuid4()

    with Session() as session:
        company_repository = CompanyRepository(
            session
        )
        booking_repository = BookingRepository(
            session
        )
        depreciation_repository = (
            FixedAssetDepreciationRepository(
                session
            )
        )

        company_repository.add(
            company
        )
        company_repository.add_fiscal_year(
            company.company_id,
            fiscal_year,
        )

        workflow = FixedAssetDepreciationWorkflow(
            session=session,
            booking_repository=booking_repository,
            depreciation_repository=(
                depreciation_repository
            ),
            booking_service=(
                DepreciationBookingService()
            ),
        )

        with pytest.raises(
            ValueError,
            match="Anlagegut ist nicht vorhanden",
        ):
            workflow.confirm(
                company_id=company.company_id,
                fiscal_year=fiscal_year,
                proposal=_proposal(
                    fixed_asset_id=(
                        unknown_fixed_asset_id
                    )
                ),
                asset_code="A-0001",
            )

    # Neue Session: Der vorher bereits vorgemerkte Booking-Datensatz
    # darf durch den Rollback nicht erhalten geblieben sein.
    with Session() as session:
        booking_repository = BookingRepository(
            session
        )

        bookings = (
            booking_repository.list_for_fiscal_year(
                company_id=company.company_id,
                fiscal_year=fiscal_year,
            )
        )

    assert bookings == ()

"""Tests für steuerliche AfA-Abweichungen."""

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
from openbilanz.database.tax_depreciation_adjustment_repository import (
    TaxDepreciationAdjustmentRepository,
)
from openbilanz.domain.company import Company
from openbilanz.domain.depreciation_proposal import (
    DepreciationProposal,
)
from openbilanz.domain.fiscal_year import FiscalYear
from openbilanz.domain.fixed_asset import FixedAsset
from openbilanz.services.depreciation_booking_service import (
    DepreciationBookingService,
)
from openbilanz.services.fixed_asset_depreciation_workflow import (
    FixedAssetDepreciationWorkflow,
)


def _create_confirmed_depreciation(
    session,
):
    """Erzeugt eine echte bestätigte Anlagenabschreibung."""

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
        description="MacBook Pro",
        position_code="HGB.266.AKTIVA.A.II.3",
        asset_account_number="0690",
        depreciation_expense_account_number="4830",
        acquisition_date=date(2026, 3, 15),
        acquisition_cost=Decimal("2400.00"),
        depreciation_start_date=date(2026, 3, 15),
        useful_life_months=36,
    )

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

    proposal = DepreciationProposal(
        fixed_asset_id=asset.fixed_asset_id,
        depreciation_date=date(2026, 12, 31),
        amount=Decimal("600.00"),
        expense_account_number="4830",
        asset_account_number="0690",
    )

    return workflow.confirm(
        company_id=company.company_id,
        fiscal_year=fiscal_year,
        proposal=proposal,
    )


@pytest.fixture
def session():
    """Erzeugt eine leere Testdatenbank."""

    engine = create_engine(
        "sqlite:///:memory:"
    )
    Base.metadata.create_all(engine)

    Session = sessionmaker(
        bind=engine
    )

    with Session() as session:
        yield session

    engine.dispose()


def test_saves_and_loads_tax_depreciation_adjustment(
    session,
) -> None:
    depreciation = _create_confirmed_depreciation(
        session
    )

    repository = TaxDepreciationAdjustmentRepository(
        session
    )

    result = repository.save(
        depreciation_id=depreciation.depreciation_id,
        tax_amount=Decimal("650.00"),
    )

    loaded = repository.get_for_depreciation(
        depreciation.depreciation_id
    )

    assert result is not None
    assert loaded is not None
    assert loaded.depreciation_id == depreciation.depreciation_id
    assert loaded.commercial_amount == Decimal("600.00")
    assert loaded.tax_amount == Decimal("650.00")
    assert loaded.difference == Decimal("50.00")


def test_updates_existing_tax_depreciation_adjustment(
    session,
) -> None:
    depreciation = _create_confirmed_depreciation(
        session
    )

    repository = TaxDepreciationAdjustmentRepository(
        session
    )

    repository.save(
        depreciation_id=depreciation.depreciation_id,
        tax_amount=Decimal("650.00"),
    )

    repository.save(
        depreciation_id=depreciation.depreciation_id,
        tax_amount=Decimal("675.00"),
    )

    loaded = repository.get_for_depreciation(
        depreciation.depreciation_id
    )

    assert loaded is not None
    assert loaded.commercial_amount == Decimal("600.00")
    assert loaded.tax_amount == Decimal("675.00")
    assert loaded.difference == Decimal("75.00")


def test_equal_tax_amount_removes_existing_adjustment(
    session,
) -> None:
    depreciation = _create_confirmed_depreciation(
        session
    )

    repository = TaxDepreciationAdjustmentRepository(
        session
    )

    repository.save(
        depreciation_id=depreciation.depreciation_id,
        tax_amount=Decimal("650.00"),
    )

    result = repository.save(
        depreciation_id=depreciation.depreciation_id,
        tax_amount=Decimal("600.00"),
    )

    loaded = repository.get_for_depreciation(
        depreciation.depreciation_id
    )

    assert result is None
    assert loaded is None


def test_rejects_unknown_depreciation(
    session,
) -> None:
    repository = TaxDepreciationAdjustmentRepository(
        session
    )

    with pytest.raises(
        ValueError,
        match="Anlagenabschreibung ist nicht vorhanden",
    ):
        repository.save(
            depreciation_id=uuid4(),
            tax_amount=Decimal("650.00"),
        )

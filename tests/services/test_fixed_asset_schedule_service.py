"""Tests für den aggregierten Anlagenspiegel."""

from datetime import date
from decimal import Decimal
from unittest.mock import Mock
from uuid import uuid4

from openbilanz.domain.depreciation_kind import DepreciationKind
from openbilanz.domain.depreciation_source import DepreciationSource
from openbilanz.domain.fixed_asset import FixedAsset
from openbilanz.domain.fixed_asset_depreciation import (
    FixedAssetDepreciation,
)
from openbilanz.domain.fixed_asset_movement import (
    FixedAssetMovement,
)
from openbilanz.domain.fixed_asset_movement_type import (
    FixedAssetMovementType,
)
from openbilanz.services.fixed_asset_schedule_service import (
    FixedAssetScheduleService,
)


def _fixed_asset(
    *,
    acquisition_date: date = date(2025, 1, 1),
) -> FixedAsset:
    return FixedAsset(
        company_id=uuid4(),
        asset_code="A-0001",
        description="Betriebs- und Geschäftsausstattung",
        position_code="HGB.266.AKTIVA.A.II.3",
        asset_account_number="0400",
        depreciation_expense_account_number="4830",
        acquisition_date=acquisition_date,
        acquisition_cost=Decimal("12000.00"),
        depreciation_start_date=acquisition_date,
        useful_life_months=60,
    )


def _acquisition(
    fixed_asset: FixedAsset,
    *,
    movement_date: date,
) -> FixedAssetMovement:
    return FixedAssetMovement(
        fixed_asset_id=fixed_asset.fixed_asset_id,
        fiscal_year_end=date(2026, 12, 31),
        movement_date=movement_date,
        amount=fixed_asset.acquisition_cost,
        booking_id=uuid4(),
        movement_type=FixedAssetMovementType.ACQUISITION,
    )


def test_reports_previous_year_acquisition_as_opening_cost() -> None:
    """Vorjahreszugänge werden als Anfangsbestand ausgewiesen."""

    asset_repository = Mock()
    depreciation_repository = Mock()
    movement_repository = Mock()

    fixed_asset = _fixed_asset()
    acquisition = _acquisition(
        fixed_asset,
        movement_date=date(2025, 1, 1),
    )

    asset_repository.list_for_company.return_value = (
        fixed_asset,
    )
    depreciation_repository.list_for_fixed_asset.return_value = ()
    movement_repository.list_for_fixed_asset.return_value = (
        acquisition,
    )

    service = FixedAssetScheduleService(
        fixed_asset_repository=asset_repository,
        depreciation_repository=depreciation_repository,
        movement_repository=movement_repository,
    )

    schedule = service.schedule_for_company(
        company_id=fixed_asset.company_id,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )

    assert len(schedule.rows) == 1

    row = schedule.rows[0]

    assert row.position_code == "HGB.266.AKTIVA.A.II.3"
    assert row.opening_cost == Decimal("12000.00")
    assert row.additions == Decimal("0.00")
    assert row.disposals == Decimal("0.00")
    assert row.closing_book_value == Decimal("12000.00")


def test_reports_current_year_acquisition_as_addition() -> None:
    """Anschaffungen des Geschäftsjahres werden als Zugang ausgewiesen."""

    asset_repository = Mock()
    depreciation_repository = Mock()
    movement_repository = Mock()

    fixed_asset = _fixed_asset(
        acquisition_date=date(2026, 3, 15),
    )
    acquisition = _acquisition(
        fixed_asset,
        movement_date=date(2026, 3, 15),
    )

    asset_repository.list_for_company.return_value = (
        fixed_asset,
    )
    depreciation_repository.list_for_fixed_asset.return_value = ()
    movement_repository.list_for_fixed_asset.return_value = (
        acquisition,
    )

    service = FixedAssetScheduleService(
        fixed_asset_repository=asset_repository,
        depreciation_repository=depreciation_repository,
        movement_repository=movement_repository,
    )

    schedule = service.schedule_for_company(
        company_id=fixed_asset.company_id,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )

    row = schedule.rows[0]

    assert row.opening_cost == Decimal("0.00")
    assert row.additions == Decimal("12000.00")
    assert row.disposals == Decimal("0.00")
    assert row.closing_book_value == Decimal("12000.00")


def test_ignores_reversed_disposal() -> None:
    """Ein stornierter Anlagenabgang bleibt ohne Wirkung."""

    asset_repository = Mock()
    depreciation_repository = Mock()
    movement_repository = Mock()

    fixed_asset = _fixed_asset()

    acquisition = _acquisition(
        fixed_asset,
        movement_date=date(2025, 1, 1),
    )

    disposal = FixedAssetMovement(
        fixed_asset_id=fixed_asset.fixed_asset_id,
        fiscal_year_end=date(2026, 12, 31),
        movement_date=date(2026, 8, 15),
        amount=Decimal("12000.00"),
        booking_id=uuid4(),
        movement_type=FixedAssetMovementType.DISPOSAL,
    )

    reversal = FixedAssetMovement(
        fixed_asset_id=fixed_asset.fixed_asset_id,
        fiscal_year_end=date(2026, 12, 31),
        movement_date=date(2026, 8, 16),
        amount=Decimal("12000.00"),
        booking_id=uuid4(),
        movement_type=FixedAssetMovementType.REVERSAL,
        reversed_movement_id=disposal.movement_id,
    )

    asset_repository.list_for_company.return_value = (
        fixed_asset,
    )
    depreciation_repository.list_for_fixed_asset.return_value = ()
    movement_repository.list_for_fixed_asset.return_value = (
        acquisition,
        disposal,
        reversal,
    )

    service = FixedAssetScheduleService(
        fixed_asset_repository=asset_repository,
        depreciation_repository=depreciation_repository,
        movement_repository=movement_repository,
    )

    schedule = service.schedule_for_company(
        company_id=fixed_asset.company_id,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )

    row = schedule.rows[0]

    assert row.opening_cost == Decimal("12000.00")
    assert row.additions == Decimal("0.00")
    assert row.disposals == Decimal("0.00")
    assert row.closing_book_value == Decimal("12000.00")

def test_reports_current_and_accumulated_depreciation() -> None:
    """Der Anlagenspiegel berücksichtigt laufende und kumulierte AfA."""

    asset_repository = Mock()
    depreciation_repository = Mock()
    movement_repository = Mock()

    fixed_asset = _fixed_asset()

    acquisition = _acquisition(
        fixed_asset,
        movement_date=date(2025, 1, 1),
    )

    previous_depreciation = FixedAssetDepreciation(
        fixed_asset_id=fixed_asset.fixed_asset_id,
        fiscal_year_end=date(2025, 12, 31),
        depreciation_date=date(2025, 12, 31),
        amount=Decimal("2400.00"),
        booking_id=uuid4(),
        kind=DepreciationKind.LINEAR,
        source=DepreciationSource.CALCULATED,
    )

    current_depreciation = FixedAssetDepreciation(
        fixed_asset_id=fixed_asset.fixed_asset_id,
        fiscal_year_end=date(2026, 12, 31),
        depreciation_date=date(2026, 12, 31),
        amount=Decimal("2400.00"),
        booking_id=uuid4(),
        kind=DepreciationKind.LINEAR,
        source=DepreciationSource.CALCULATED,
    )

    asset_repository.list_for_company.return_value = (
        fixed_asset,
    )
    depreciation_repository.list_for_fixed_asset.return_value = (
        previous_depreciation,
        current_depreciation,
    )
    movement_repository.list_for_fixed_asset.return_value = (
        acquisition,
    )

    service = FixedAssetScheduleService(
        fixed_asset_repository=asset_repository,
        depreciation_repository=depreciation_repository,
        movement_repository=movement_repository,
    )

    schedule = service.schedule_for_company(
        company_id=fixed_asset.company_id,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )

    row = schedule.rows[0]

    assert row.opening_cost == Decimal("12000.00")
    assert row.additions == Decimal("0.00")
    assert row.disposals == Decimal("0.00")

    assert row.current_depreciation == Decimal("2400.00")
    assert row.accumulated_depreciation == Decimal("4800.00")
    assert row.closing_book_value == Decimal("7200.00")

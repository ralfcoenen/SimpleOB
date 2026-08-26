"""Tests für den Anlagenbericht."""

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
from openbilanz.services.fixed_asset_reporting_service import (
    FixedAssetReportingService,
)


def _fixed_asset() -> FixedAsset:
    return FixedAsset(
        company_id=uuid4(),
        asset_code="A-0001",
        description="Betriebs- und Geschäftsausstattung",
        position_code="HGB.266.AKTIVA.A.II.3",
        asset_account_number="0400",
        depreciation_expense_account_number="4830",
        acquisition_date=date(2025, 1, 1),
        acquisition_cost=Decimal("12000.00"),
        depreciation_start_date=date(2025, 1, 1),
        useful_life_months=60,
    )


def test_reports_fixed_asset_without_depreciation() -> None:
    asset_repository = Mock()
    depreciation_repository = Mock()
    movement_repository = Mock()

    fixed_asset = _fixed_asset()

    asset_repository.list_for_company.return_value = (
        fixed_asset,
    )
    depreciation_repository.list_for_fixed_asset.return_value = ()
    movement_repository.list_for_fixed_asset.return_value = ()

    service = FixedAssetReportingService(
        fixed_asset_repository=asset_repository,
        depreciation_repository=depreciation_repository,
        movement_repository=movement_repository,
    )

    report = service.report_for_company(
        company_id=fixed_asset.company_id,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )

    assert len(report.rows) == 1

    row = report.rows[0]

    assert row.acquisition_cost == Decimal("12000.00")
    assert row.opening_depreciation == Decimal("0.00")
    assert row.current_depreciation == Decimal("0.00")
    assert row.accumulated_depreciation == Decimal("0.00")
    assert row.closing_book_value == Decimal("12000.00")
    assert row.disposal_date is None


def test_reports_opening_and_current_depreciation() -> None:
    asset_repository = Mock()
    depreciation_repository = Mock()
    movement_repository = Mock()

    fixed_asset = _fixed_asset()

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
    movement_repository.list_for_fixed_asset.return_value = ()

    service = FixedAssetReportingService(
        fixed_asset_repository=asset_repository,
        depreciation_repository=depreciation_repository,
        movement_repository=movement_repository,
    )

    report = service.report_for_company(
        company_id=fixed_asset.company_id,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )

    row = report.rows[0]

    assert row.opening_depreciation == Decimal("2400.00")
    assert row.current_depreciation == Decimal("2400.00")
    assert row.accumulated_depreciation == Decimal("4800.00")
    assert row.closing_book_value == Decimal("7200.00")


def test_reports_zero_book_value_after_disposal() -> None:
    asset_repository = Mock()
    depreciation_repository = Mock()
    movement_repository = Mock()

    fixed_asset = _fixed_asset()

    disposal = FixedAssetMovement(
        fixed_asset_id=fixed_asset.fixed_asset_id,
        fiscal_year_end=date(2026, 12, 31),
        movement_date=date(2026, 8, 15),
        amount=Decimal("9000.00"),
        booking_id=uuid4(),
        movement_type=FixedAssetMovementType.DISPOSAL,
    )

    asset_repository.list_for_company.return_value = (
        fixed_asset,
    )
    depreciation_repository.list_for_fixed_asset.return_value = ()
    movement_repository.list_for_fixed_asset.return_value = (
        disposal,
    )

    service = FixedAssetReportingService(
        fixed_asset_repository=asset_repository,
        depreciation_repository=depreciation_repository,
        movement_repository=movement_repository,
    )

    report = service.report_for_company(
        company_id=fixed_asset.company_id,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )

    row = report.rows[0]

    assert row.closing_book_value == Decimal("0.00")
    assert row.disposal_date == date(2026, 8, 15)


def test_reports_zero_book_value_after_loss() -> None:
    asset_repository = Mock()
    depreciation_repository = Mock()
    movement_repository = Mock()

    fixed_asset = _fixed_asset()

    loss = FixedAssetMovement(
        fixed_asset_id=fixed_asset.fixed_asset_id,
        fiscal_year_end=date(2026, 12, 31),
        movement_date=date(2026, 9, 30),
        amount=Decimal("8000.00"),
        booking_id=uuid4(),
        movement_type=FixedAssetMovementType.LOSS,
    )

    asset_repository.list_for_company.return_value = (
        fixed_asset,
    )
    depreciation_repository.list_for_fixed_asset.return_value = ()
    movement_repository.list_for_fixed_asset.return_value = (
        loss,
    )

    service = FixedAssetReportingService(
        fixed_asset_repository=asset_repository,
        depreciation_repository=depreciation_repository,
        movement_repository=movement_repository,
    )

    report = service.report_for_company(
        company_id=fixed_asset.company_id,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )

    row = report.rows[0]

    assert row.closing_book_value == Decimal("0.00")
    assert row.disposal_date == date(2026, 9, 30)

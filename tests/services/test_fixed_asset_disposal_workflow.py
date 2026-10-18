"""Tests für den Workflow bestätigter Anlagenverkäufe."""

from datetime import date
from decimal import Decimal
from unittest.mock import Mock
from uuid import uuid4

from simpleob.domain.booking import Booking
from simpleob.domain.booking_line import BookingLine
from simpleob.domain.entry_side import EntrySide
from simpleob.domain.fiscal_year import FiscalYear
from simpleob.domain.fixed_asset import FixedAsset
from simpleob.domain.fixed_asset_disposal_calculation import (
    FixedAssetDisposalCalculation,
)
from simpleob.domain.fixed_asset_movement_type import (
    FixedAssetMovementType,
)
from simpleob.domain.fixed_asset_status import (
    FixedAssetStatus,
)
from simpleob.services.fixed_asset_disposal_workflow import (
    FixedAssetDisposalWorkflow,
)


def test_confirms_fixed_asset_disposal_atomically() -> None:
    company_id = uuid4()

    fiscal_year = FiscalYear(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )

    fixed_asset = FixedAsset(
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

    booking = Booking(
        booking_date=date(2026, 8, 15),
        voucher_no="V-001",
        description="Verkauf MacBook Pro",
        lines=(
            BookingLine(
                account_number="1200",
                side=EntrySide.DEBIT,
                amount=Decimal("2380.00"),
            ),
            BookingLine(
                account_number="0690",
                side=EntrySide.CREDIT,
                amount=Decimal("2000.00"),
            ),
            BookingLine(
                account_number="8500",
                side=EntrySide.CREDIT,
                amount=Decimal("380.00"),
            ),
        ),
    )

    calculation = FixedAssetDisposalCalculation(
        acquisition_cost=Decimal("2400.00"),
        accumulated_depreciation=Decimal("400.00"),
        carrying_amount=Decimal("2000.00"),
        gross_proceeds=Decimal("2380.00"),
        net_proceeds=Decimal("2380.00"),
        tax_amount=Decimal("0.00"),
        gain=Decimal("380.00"),
        loss=Decimal("0.00"),
        booking=booking,
    )

    session = Mock()
    booking_repository = Mock()
    movement_repository = Mock()
    fixed_asset_repository = Mock()

    workflow = FixedAssetDisposalWorkflow(
        session=session,
        booking_repository=booking_repository,
        movement_repository=movement_repository,
        fixed_asset_repository=fixed_asset_repository,
    )

    movement = workflow.confirm(
        company_id=company_id,
        fiscal_year=fiscal_year,
        fixed_asset=fixed_asset,
        calculation=calculation,
    )

    assert movement.fixed_asset_id == fixed_asset.fixed_asset_id
    assert movement.fiscal_year_end == fiscal_year.end_date
    assert movement.movement_date == date(2026, 8, 15)
    assert movement.amount == Decimal("2400.00")
    assert (
        movement.movement_type
        is FixedAssetMovementType.DISPOSAL
    )
    assert movement.booking_id == booking.booking_id

    booking_repository.add.assert_called_once_with(
        company_id=company_id,
        fiscal_year=fiscal_year,
        booking=booking,
        commit=False,
    )

    movement_repository.add.assert_called_once_with(
        movement=movement,
        booking_line_position=1,
        commit=False,
    )

    fixed_asset_repository.update.assert_called_once()

    update_kwargs = (
        fixed_asset_repository.update.call_args.kwargs
    )
    disposed_fixed_asset = update_kwargs["fixed_asset"]

    assert update_kwargs["commit"] is False
    assert (
        disposed_fixed_asset.fixed_asset_id
        == fixed_asset.fixed_asset_id
    )
    assert (
        disposed_fixed_asset.status
        is FixedAssetStatus.DISPOSED
    )
    assert (
        disposed_fixed_asset.disposal_date
        == date(2026, 8, 15)
    )

    session.commit.assert_called_once_with()
    session.rollback.assert_not_called()

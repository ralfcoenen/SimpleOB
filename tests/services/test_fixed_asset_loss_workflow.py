"""Tests für den Totalverlust-Workflow von Anlagegütern."""

from datetime import date
from decimal import Decimal
from unittest.mock import Mock
from uuid import uuid4

import pytest

from openbilanz.domain.depreciation_proposal import DepreciationProposal
from openbilanz.domain.fiscal_year import FiscalYear
from openbilanz.domain.fixed_asset import FixedAsset
from openbilanz.domain.fixed_asset_movement_type import (
    FixedAssetMovementType,
)
from openbilanz.domain.fixed_asset_status import FixedAssetStatus
from openbilanz.services.fixed_asset_loss_workflow import (
    FixedAssetLossWorkflow,
)


def _asset():
    return FixedAsset(
        company_id=uuid4(),
        asset_code="A-0001",
        description="Maschine",
        position_code="HGB.266.AKTIVA.A.II.3",
        asset_account_number="0400",
        depreciation_expense_account_number="4830",
        acquisition_date=date(2026, 1, 1),
        acquisition_cost=Decimal("12000.00"),
        depreciation_start_date=date(2026, 1, 1),
        useful_life_months=120,
    )


def _fiscal_year():
    return FiscalYear(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )


def test_rejects_loss_when_depreciation_is_still_pending() -> None:
    asset = _asset()
    fiscal_year = _fiscal_year()

    session = Mock()
    fixed_asset_repository = Mock()
    depreciation_repository = Mock()
    movement_repository = Mock()
    booking_repository = Mock()
    depreciation_service = Mock()
    book_value_service = Mock()
    booking_service = Mock()

    fixed_asset_repository.get.return_value = asset
    depreciation_repository.list_for_fixed_asset.return_value = ()

    depreciation_service.build_proposal_until.return_value = (
        DepreciationProposal(
            fixed_asset_id=asset.fixed_asset_id,
            depreciation_date=date(2026, 8, 15),
            amount=Decimal("800.00"),
            expense_account_number="4830",
            asset_account_number="0400",
        )
    )

    workflow = FixedAssetLossWorkflow(
        session=session,
        fixed_asset_repository=fixed_asset_repository,
        depreciation_repository=depreciation_repository,
        movement_repository=movement_repository,
        booking_repository=booking_repository,
        depreciation_service=depreciation_service,
        book_value_service=book_value_service,
        booking_service=booking_service,
    )

    with pytest.raises(
        ValueError,
        match="Abschreibung bis zum Abgangsdatum",
    ):
        workflow.confirm_loss(
            company_id=asset.company_id,
            fiscal_year=fiscal_year,
            fixed_asset_id=asset.fixed_asset_id,
            loss_date=date(2026, 8, 15),
            loss_expense_account_number="4840",
        )

    booking_repository.add.assert_not_called()
    movement_repository.add.assert_not_called()
    fixed_asset_repository.update.assert_not_called()
    session.commit.assert_not_called()

def test_confirms_loss_atomically_after_depreciation() -> None:
    asset = _asset()
    fiscal_year = _fiscal_year()

    session = Mock()
    fixed_asset_repository = Mock()
    depreciation_repository = Mock()
    movement_repository = Mock()
    booking_repository = Mock()
    depreciation_service = Mock()
    book_value_service = Mock()
    booking_service = Mock()

    fixed_asset_repository.get.return_value = asset
    depreciation_repository.list_for_fixed_asset.return_value = ()

    depreciation_service.build_proposal_until.return_value = None
    book_value_service.book_value_at.return_value = (
        Decimal("10000.00")
    )

    booking = Mock()
    booking.booking_id = uuid4()

    booking_service.build_booking.return_value = booking

    workflow = FixedAssetLossWorkflow(
        session=session,
        fixed_asset_repository=fixed_asset_repository,
        depreciation_repository=depreciation_repository,
        movement_repository=movement_repository,
        booking_repository=booking_repository,
        depreciation_service=depreciation_service,
        book_value_service=book_value_service,
        booking_service=booking_service,
    )

    movement = workflow.confirm_loss(
        company_id=asset.company_id,
        fiscal_year=fiscal_year,
        fixed_asset_id=asset.fixed_asset_id,
        loss_date=date(2026, 8, 15),
        loss_expense_account_number="4840",
    )

    assert (
        movement.movement_type
        is FixedAssetMovementType.LOSS
    )
    assert movement.amount == Decimal("10000.00")
    assert movement.fixed_asset_id == asset.fixed_asset_id
    assert movement.booking_id == booking.booking_id

    booking_repository.add.assert_called_once_with(
        company_id=asset.company_id,
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

    updated_asset = (
        fixed_asset_repository.update.call_args.kwargs[
            "fixed_asset"
        ]
    )

    assert updated_asset.status is FixedAssetStatus.DISPOSED
    assert updated_asset.disposal_date == date(
        2026,
        8,
        15,
    )

    assert (
        fixed_asset_repository.update
        .call_args.kwargs["commit"]
        is False
    )

    session.commit.assert_called_once_with()
    session.rollback.assert_not_called()

def test_rolls_back_when_loss_persistence_fails() -> None:
    asset = _asset()
    fiscal_year = _fiscal_year()

    session = Mock()
    fixed_asset_repository = Mock()
    depreciation_repository = Mock()
    movement_repository = Mock()
    booking_repository = Mock()
    depreciation_service = Mock()
    book_value_service = Mock()
    booking_service = Mock()

    fixed_asset_repository.get.return_value = asset
    depreciation_repository.list_for_fixed_asset.return_value = ()

    depreciation_service.build_proposal_until.return_value = None
    book_value_service.book_value_at.return_value = Decimal("10000.00")

    booking = Mock()
    booking.booking_id = uuid4()

    booking_service.build_booking.return_value = booking

    movement_repository.add.side_effect = RuntimeError(
        "Persistenzfehler"
    )

    workflow = FixedAssetLossWorkflow(
        session=session,
        fixed_asset_repository=fixed_asset_repository,
        depreciation_repository=depreciation_repository,
        movement_repository=movement_repository,
        booking_repository=booking_repository,
        depreciation_service=depreciation_service,
        book_value_service=book_value_service,
        booking_service=booking_service,
    )

    with pytest.raises(
        RuntimeError,
        match="Persistenzfehler",
    ):
        workflow.confirm_loss(
            company_id=asset.company_id,
            fiscal_year=fiscal_year,
            fixed_asset_id=asset.fixed_asset_id,
            loss_date=date(2026, 8, 15),
            loss_expense_account_number="4840",
        )

    session.commit.assert_not_called()
    session.rollback.assert_called_once_with()

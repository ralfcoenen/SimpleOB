"""Tests für die fachliche Auswertung des Anlagenspiegels."""

from datetime import date
from decimal import Decimal
from unittest.mock import Mock
from uuid import uuid4

from openbilanz.domain.depreciation_kind import (
    DepreciationKind,
)
from openbilanz.domain.depreciation_source import (
    DepreciationSource,
)
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
from openbilanz.domain.fixed_asset_status import (
    FixedAssetStatus,
)
from openbilanz.services.fixed_asset_schedule_service import (
    FixedAssetScheduleService,
)


def test_builds_fixed_asset_schedule_for_existing_asset() -> None:
    """Bestandsanlage mit laufender AfA wird korrekt ausgewertet."""

    company_id = uuid4()
    fixed_asset_id = uuid4()

    fixed_asset = FixedAsset(
        company_id=company_id,
        fixed_asset_id=fixed_asset_id,
        asset_code="A-001",
        description="Maschine",
        position_code="HGB.266.AKTIVA.A.II.2",
        asset_account_number="0400",
        depreciation_expense_account_number="4830",
        acquisition_date=date(2025, 1, 1),
        acquisition_cost=Decimal("12000.00"),
        depreciation_start_date=date(2025, 1, 1),
        useful_life_months=60,
    )

    depreciation_2025 = FixedAssetDepreciation(
        fixed_asset_id=fixed_asset_id,
        fiscal_year_end=date(2025, 12, 31),
        depreciation_date=date(2025, 12, 31),
        amount=Decimal("2400.00"),
        booking_id=uuid4(),
        kind=DepreciationKind.LINEAR,
        source=DepreciationSource.CALCULATED,
    )

    depreciation_2026 = FixedAssetDepreciation(
        fixed_asset_id=fixed_asset_id,
        fiscal_year_end=date(2026, 12, 31),
        depreciation_date=date(2026, 12, 31),
        amount=Decimal("2400.00"),
        booking_id=uuid4(),
        kind=DepreciationKind.LINEAR,
        source=DepreciationSource.CALCULATED,
    )

    fixed_asset_repository = Mock()
    fixed_asset_repository.list_for_company.return_value = (
        fixed_asset,
    )

    fixed_asset_movement_repository = Mock()
    fixed_asset_movement_repository.list_for_fixed_asset.return_value = ()

    fixed_asset_depreciation_repository = Mock()
    fixed_asset_depreciation_repository.list_for_fixed_asset.return_value = (
        depreciation_2025,
        depreciation_2026,
    )

    service = FixedAssetScheduleService(
        fixed_asset_repository=fixed_asset_repository,
        fixed_asset_movement_repository=(
            fixed_asset_movement_repository
        ),
        fixed_asset_depreciation_repository=(
            fixed_asset_depreciation_repository
        ),
    )

    result = service.build(
        company_id=company_id,
        fiscal_year_start=date(2026, 1, 1),
        fiscal_year_end=date(2026, 12, 31),
    )

    assert len(result) == 1

    position = result[0]

    assert position.position_code == "HGB.266.AKTIVA.A.II.2"

    assert (
        position.acquisition_cost_beginning
        == Decimal("12000.00")
    )
    assert position.additions == Decimal("0.00")
    assert position.disposals == Decimal("0.00")
    assert (
        position.acquisition_cost_ending
        == Decimal("12000.00")
    )

    assert (
        position.accumulated_depreciation_beginning
        == Decimal("2400.00")
    )
    assert (
        position.depreciation_current_year
        == Decimal("2400.00")
    )
    assert (
        position.depreciation_disposals
        == Decimal("0.00")
    )
    assert (
        position.accumulated_depreciation_ending
        == Decimal("4800.00")
    )

    assert (
        position.carrying_amount_ending
        == Decimal("7200.00")
    )


def test_counts_only_confirmed_acquisition_as_addition() -> None:
    """Nur ein bestätigter Zugang fließt in den Anlagenspiegel ein."""

    company_id = uuid4()

    linked_asset_id = uuid4()
    unlinked_asset_id = uuid4()

    linked_asset = FixedAsset(
        company_id=company_id,
        fixed_asset_id=linked_asset_id,
        asset_code="A-001",
        description="Maschine",
        position_code="HGB.266.AKTIVA.A.II.2",
        asset_account_number="0400",
        depreciation_expense_account_number="4830",
        acquisition_date=date(2026, 3, 15),
        acquisition_cost=Decimal("12000.00"),
        depreciation_start_date=date(2026, 3, 15),
        useful_life_months=60,
    )

    unlinked_asset = FixedAsset(
        company_id=company_id,
        fixed_asset_id=unlinked_asset_id,
        asset_code="A-002",
        description="Noch nicht gebuchte Maschine",
        position_code="HGB.266.AKTIVA.A.II.2",
        asset_account_number="0400",
        depreciation_expense_account_number="4830",
        acquisition_date=date(2026, 4, 1),
        acquisition_cost=Decimal("5000.00"),
        depreciation_start_date=date(2026, 4, 1),
        useful_life_months=60,
    )

    acquisition_movement = FixedAssetMovement(
        fixed_asset_id=linked_asset_id,
        fiscal_year_end=date(2026, 12, 31),
        movement_date=date(2026, 3, 15),
        amount=Decimal("12000.00"),
        booking_id=uuid4(),
        movement_type=FixedAssetMovementType.ACQUISITION,
    )

    fixed_asset_repository = Mock()
    fixed_asset_repository.list_for_company.return_value = (
        linked_asset,
        unlinked_asset,
    )

    fixed_asset_movement_repository = Mock()

    def list_movements(fixed_asset_id):
        if fixed_asset_id == linked_asset_id:
            return (acquisition_movement,)
        return ()

    fixed_asset_movement_repository.list_for_fixed_asset.side_effect = (
        list_movements
    )

    fixed_asset_depreciation_repository = Mock()
    fixed_asset_depreciation_repository.list_for_fixed_asset.return_value = ()

    service = FixedAssetScheduleService(
        fixed_asset_repository=fixed_asset_repository,
        fixed_asset_movement_repository=(
            fixed_asset_movement_repository
        ),
        fixed_asset_depreciation_repository=(
            fixed_asset_depreciation_repository
        ),
    )

    result = service.build(
        company_id=company_id,
        fiscal_year_start=date(2026, 1, 1),
        fiscal_year_end=date(2026, 12, 31),
    )

    assert len(result) == 1

    position = result[0]

    assert position.position_code == "HGB.266.AKTIVA.A.II.2"

    assert (
        position.acquisition_cost_beginning
        == Decimal("0.00")
    )
    assert position.additions == Decimal("12000.00")
    assert position.disposals == Decimal("0.00")
    assert (
        position.acquisition_cost_ending
        == Decimal("12000.00")
    )
    assert (
        position.accumulated_depreciation_ending
        == Decimal("0.00")
    )
    assert (
        position.carrying_amount_ending
        == Decimal("12000.00")
    )

def test_builds_fixed_asset_schedule_for_disposed_asset() -> None:
    """Ein bestätigter vollständiger Abgang wird brutto ausgewertet."""

    company_id = uuid4()
    fixed_asset_id = uuid4()

    fixed_asset = FixedAsset(
        company_id=company_id,
        fixed_asset_id=fixed_asset_id,
        asset_code="A-001",
        description="Maschine",
        position_code="HGB.266.AKTIVA.A.II.2",
        asset_account_number="0400",
        depreciation_expense_account_number="4830",
        acquisition_date=date(2025, 1, 1),
        acquisition_cost=Decimal("12000.00"),
        depreciation_start_date=date(2025, 1, 1),
        useful_life_months=60,
        status=FixedAssetStatus.DISPOSED,
        disposal_date=date(2026, 8, 15),
    )

    acquisition_movement = FixedAssetMovement(
        fixed_asset_id=fixed_asset_id,
        fiscal_year_end=date(2025, 12, 31),
        movement_date=date(2025, 1, 1),
        amount=Decimal("12000.00"),
        booking_id=uuid4(),
        movement_type=FixedAssetMovementType.ACQUISITION,
    )

    disposal_movement = FixedAssetMovement(
        fixed_asset_id=fixed_asset_id,
        fiscal_year_end=date(2026, 12, 31),
        movement_date=date(2026, 8, 15),
        amount=Decimal("8000.00"),
        booking_id=uuid4(),
        movement_type=FixedAssetMovementType.DISPOSAL,
    )

    depreciation_2025 = FixedAssetDepreciation(
        fixed_asset_id=fixed_asset_id,
        fiscal_year_end=date(2025, 12, 31),
        depreciation_date=date(2025, 12, 31),
        amount=Decimal("2400.00"),
        booking_id=uuid4(),
        kind=DepreciationKind.LINEAR,
        source=DepreciationSource.CALCULATED,
    )

    depreciation_2026 = FixedAssetDepreciation(
        fixed_asset_id=fixed_asset_id,
        fiscal_year_end=date(2026, 12, 31),
        depreciation_date=date(2026, 8, 15),
        amount=Decimal("1600.00"),
        booking_id=uuid4(),
        kind=DepreciationKind.LINEAR,
        source=DepreciationSource.CALCULATED,
    )

    fixed_asset_repository = Mock()
    fixed_asset_repository.list_for_company.return_value = (
        fixed_asset,
    )

    fixed_asset_movement_repository = Mock()
    fixed_asset_movement_repository.list_for_fixed_asset.return_value = (
        acquisition_movement,
        disposal_movement,
    )

    fixed_asset_depreciation_repository = Mock()
    fixed_asset_depreciation_repository.list_for_fixed_asset.return_value = (
        depreciation_2025,
        depreciation_2026,
    )

    service = FixedAssetScheduleService(
        fixed_asset_repository=fixed_asset_repository,
        fixed_asset_movement_repository=(
            fixed_asset_movement_repository
        ),
        fixed_asset_depreciation_repository=(
            fixed_asset_depreciation_repository
        ),
    )

    result = service.build(
        company_id=company_id,
        fiscal_year_start=date(2026, 1, 1),
        fiscal_year_end=date(2026, 12, 31),
    )

    assert len(result) == 1

    position = result[0]

    assert (
        position.acquisition_cost_beginning
        == Decimal("12000.00")
    )
    assert position.additions == Decimal("0.00")

    assert position.disposals == Decimal("12000.00")

    assert (
        position.acquisition_cost_ending
        == Decimal("0.00")
    )

    assert (
        position.accumulated_depreciation_beginning
        == Decimal("2400.00")
    )

    assert (
        position.depreciation_current_year
        == Decimal("1600.00")
    )

    assert (
        position.depreciation_disposals
        == Decimal("4000.00")
    )

    assert (
        position.accumulated_depreciation_ending
        == Decimal("0.00")
    )

    assert (
        position.carrying_amount_ending
        == Decimal("0.00")
    )

def test_builds_fixed_asset_schedule_for_same_year_acquisition_and_disposal(
) -> None:
    """Zugang und vollständiger Abgang im selben Jahr werden ausgewertet."""

    company_id = uuid4()
    fixed_asset_id = uuid4()

    fixed_asset = FixedAsset(
        company_id=company_id,
        fixed_asset_id=fixed_asset_id,
        asset_code="A-001",
        description="Maschine",
        position_code="HGB.266.AKTIVA.A.II.2",
        asset_account_number="0400",
        depreciation_expense_account_number="4830",
        acquisition_date=date(2026, 2, 1),
        acquisition_cost=Decimal("12000.00"),
        depreciation_start_date=date(2026, 2, 1),
        useful_life_months=60,
        status=FixedAssetStatus.DISPOSED,
        disposal_date=date(2026, 7, 31),
    )

    acquisition_movement = FixedAssetMovement(
        fixed_asset_id=fixed_asset_id,
        fiscal_year_end=date(2026, 12, 31),
        movement_date=date(2026, 2, 1),
        amount=Decimal("12000.00"),
        booking_id=uuid4(),
        movement_type=FixedAssetMovementType.ACQUISITION,
    )

    disposal_movement = FixedAssetMovement(
        fixed_asset_id=fixed_asset_id,
        fiscal_year_end=date(2026, 12, 31),
        movement_date=date(2026, 7, 31),
        amount=Decimal("11000.00"),
        booking_id=uuid4(),
        movement_type=FixedAssetMovementType.DISPOSAL,
    )

    depreciation_2026 = FixedAssetDepreciation(
        fixed_asset_id=fixed_asset_id,
        fiscal_year_end=date(2026, 12, 31),
        depreciation_date=date(2026, 7, 31),
        amount=Decimal("1000.00"),
        booking_id=uuid4(),
        kind=DepreciationKind.LINEAR,
        source=DepreciationSource.CALCULATED,
    )

    fixed_asset_repository = Mock()
    fixed_asset_repository.list_for_company.return_value = (
        fixed_asset,
    )

    fixed_asset_movement_repository = Mock()
    fixed_asset_movement_repository.list_for_fixed_asset.return_value = (
        acquisition_movement,
        disposal_movement,
    )

    fixed_asset_depreciation_repository = Mock()
    fixed_asset_depreciation_repository.list_for_fixed_asset.return_value = (
        depreciation_2026,
    )

    service = FixedAssetScheduleService(
        fixed_asset_repository=fixed_asset_repository,
        fixed_asset_movement_repository=(
            fixed_asset_movement_repository
        ),
        fixed_asset_depreciation_repository=(
            fixed_asset_depreciation_repository
        ),
    )

    result = service.build(
        company_id=company_id,
        fiscal_year_start=date(2026, 1, 1),
        fiscal_year_end=date(2026, 12, 31),
    )

    assert len(result) == 1

    position = result[0]

    assert (
        position.acquisition_cost_beginning
        == Decimal("0.00")
    )
    assert position.additions == Decimal("12000.00")
    assert position.disposals == Decimal("12000.00")
    assert (
        position.acquisition_cost_ending
        == Decimal("0.00")
    )

    assert (
        position.accumulated_depreciation_beginning
        == Decimal("0.00")
    )
    assert (
        position.depreciation_current_year
        == Decimal("1000.00")
    )
    assert (
        position.depreciation_disposals
        == Decimal("1000.00")
    )
    assert (
        position.accumulated_depreciation_ending
        == Decimal("0.00")
    )
    assert (
        position.carrying_amount_ending
        == Decimal("0.00")
    )

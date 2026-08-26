"""Tests für die lineare Anlagenabschreibung."""
from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from openbilanz.domain.fiscal_year import FiscalYear
from openbilanz.domain.fixed_asset import FixedAsset
from openbilanz.services.depreciation_service import (
        DepreciationService,
)


def _fixed_asset(
        *,
        acquisition_date: date = date(2025, 1, 1),
        acquisition_cost: Decimal = Decimal("1200.00"),
        useful_life_months: int = 36,
    ) -> FixedAsset:

        """Erzeugt ein Anlagegut für die Service-Tests."""
        return FixedAsset(
            company_id=uuid4(),
            asset_code="A-0001",
            description="Testanlagegut",
            position_code="HGB.266.AKTIVA.A.II.3",
            asset_account_number="0690",
            depreciation_expense_account_number="4830",
            acquisition_date=acquisition_date,
            acquisition_cost=acquisition_cost,
            depreciation_start_date=acquisition_date,
            useful_life_months=useful_life_months,
        )

def _fiscal_year(
    year: int,
) -> FiscalYear:
    return FiscalYear(
        start_date=date(year, 1, 1),
        end_date=date(year, 12, 31),
    )


def test_build_proposal_calculates_full_annual_depreciation() -> None:
    asset = _fixed_asset(
        acquisition_date=date(2025, 1, 1),
        acquisition_cost=Decimal("1200.00"),
        useful_life_months=36,
    )

    proposal = DepreciationService().build_proposal(
        fixed_asset=asset,
        fiscal_year=_fiscal_year(2026),
        previous_depreciation=Decimal("400.00"),
        expense_account_number="4830",
        asset_account_number="0690",
    )

    assert proposal is not None
    assert proposal.amount == Decimal("400.00")
    assert proposal.depreciation_date == date(2026, 12, 31)
    assert proposal.fixed_asset_id == asset.fixed_asset_id
    assert proposal.expense_account_number == "4830"
    assert proposal.asset_account_number == "0690"


def test_build_proposal_prorates_acquisition_year_by_month() -> None:
    asset = _fixed_asset(
        acquisition_date=date(2025, 4, 15),
        acquisition_cost=Decimal("1200.00"),
        useful_life_months=36,
    )

    proposal = DepreciationService().build_proposal(
        fixed_asset=asset,
        fiscal_year=_fiscal_year(2025),
        previous_depreciation=Decimal("0.00"),
        expense_account_number="4830",
        asset_account_number="0690",
    )

    assert proposal is not None

    # Jahres-AfA 400,00 EUR; April bis Dezember = 9 Monate.
    assert proposal.amount == Decimal("300.00")


def test_build_proposal_preserves_memory_value() -> None:
    asset = _fixed_asset(
        acquisition_cost=Decimal("1200.00"),
        useful_life_months=36,
    )

    proposal = DepreciationService().build_proposal(
        fixed_asset=asset,
        fiscal_year=_fiscal_year(2027),
        previous_depreciation=Decimal("1000.00"),
        expense_account_number="4830",
        asset_account_number="0690",
    )

    assert proposal is not None
    assert proposal.amount == Decimal("199.00")


def test_build_proposal_returns_none_at_memory_value() -> None:
    asset = _fixed_asset(
        acquisition_cost=Decimal("1200.00"),
        useful_life_months=36,
    )

    proposal = DepreciationService().build_proposal(
        fixed_asset=asset,
        fiscal_year=_fiscal_year(2028),
        previous_depreciation=Decimal("1199.00"),
        expense_account_number="4830",
        asset_account_number="0690",
    )

    assert proposal is None


def test_build_proposal_returns_none_before_acquisition() -> None:
    asset = _fixed_asset(
        acquisition_date=date(2026, 1, 1),
    )

    proposal = DepreciationService().build_proposal(
        fixed_asset=asset,
        fiscal_year=_fiscal_year(2025),
        previous_depreciation=Decimal("0.00"),
        expense_account_number="4830",
        asset_account_number="0690",
    )

    assert proposal is None

def test_build_proposal_uses_depreciation_start_date() -> None:
    asset = FixedAsset(
        company_id=uuid4(),
        asset_code="A-0001",
        description="Testanlagegut",
        position_code="HGB.266.AKTIVA.A.II.3",
        asset_account_number="0690",
        depreciation_expense_account_number="4830",
        acquisition_date=date(2025, 1, 15),
        acquisition_cost=Decimal("1200.00"),
        depreciation_start_date=date(2025, 4, 1),
        useful_life_months=36,
    )

    proposal = DepreciationService().build_proposal(
        fixed_asset=asset,
        fiscal_year=_fiscal_year(2025),
        previous_depreciation=Decimal("0.00"),
        expense_account_number="4830",
        asset_account_number="0690",
    )

    assert proposal is not None
    assert proposal.amount == Decimal("300.00")

def test_builds_depreciation_proposal_until_disposal_date() -> None:
    service = DepreciationService()

    asset = FixedAsset(
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

    fiscal_year = FiscalYear(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )

    proposal = service.build_proposal_until(
        fixed_asset=asset,
        fiscal_year=fiscal_year,
        previous_depreciation=Decimal("0.00"),
        expense_account_number="4830",
        asset_account_number="0400",
        depreciation_date=date(2026, 8, 15),
    )

    assert proposal is not None
    assert proposal.amount == Decimal("800.00")
    assert proposal.depreciation_date == date(
        2026,
        8,
        15,
    )

def test_rejects_depreciation_date_outside_fiscal_year() -> None:
    service = DepreciationService()

    asset = FixedAsset(
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

    fiscal_year = FiscalYear(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )

    with pytest.raises(
        ValueError,
        match="within the fiscal year",
    ):
        service.build_proposal_until(
            fixed_asset=asset,
            fiscal_year=fiscal_year,
            previous_depreciation=Decimal("0.00"),
            expense_account_number="4830",
            asset_account_number="0400",
            depreciation_date=date(2027, 1, 1),
        )

def test_builds_depreciation_until_disposal_after_acquisition() -> None:
    service = DepreciationService()

    asset = FixedAsset(
        company_id=uuid4(),
        asset_code="A-0001",
        description="Maschine",
        position_code="HGB.266.AKTIVA.A.II.3",
        asset_account_number="0400",
        depreciation_expense_account_number="4830",
        acquisition_date=date(2026, 3, 15),
        acquisition_cost=Decimal("12000.00"),
        depreciation_start_date=date(2026, 3, 15),
        useful_life_months=120,
    )

    fiscal_year = FiscalYear(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )

    proposal = service.build_proposal_until(
        fixed_asset=asset,
        fiscal_year=fiscal_year,
        previous_depreciation=Decimal("0.00"),
        expense_account_number="4830",
        asset_account_number="0400",
        depreciation_date=date(2026, 8, 15),
    )

    assert proposal is not None
    assert proposal.amount == Decimal("600.00")

def test_no_proposal_when_depreciation_until_date_is_already_booked() -> None:
    service = DepreciationService()

    asset = FixedAsset(
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

    fiscal_year = FiscalYear(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )

    proposal = service.build_proposal_until(
        fixed_asset=asset,
        fiscal_year=fiscal_year,
        previous_depreciation=Decimal("800.00"),
        current_fiscal_year_depreciation=Decimal("800.00"),
        expense_account_number="4830",
        asset_account_number="0400",
        depreciation_date=date(2026, 8, 15),
    )

    assert proposal is None

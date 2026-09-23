"""Tests für FiscalYearWorkspace."""

from datetime import date
from decimal import Decimal
from pathlib import Path
from unittest.mock import ANY, Mock, patch
from uuid import uuid4

import pytest

from openbilanz.accounting.account_balance import AccountBalance
from openbilanz.accounting.balance_sheet import BalanceSheet
from openbilanz.accounting.income_statement import IncomeStatement
from openbilanz.accounting.ledger import Ledger
from openbilanz.accounting.mapper import AccountMapper
from openbilanz.core.context import ApplicationContext
from openbilanz.domain.accounting_account_roles import (
    AccountingAccountRoles,
)
from openbilanz.domain.accounting_control_accounts import (
    AccountingControlAccounts,
)
from openbilanz.domain.booking import Booking
from openbilanz.domain.booking_line import BookingLine
from openbilanz.domain.booking_type import BookingType
from openbilanz.domain.chart_of_accounts_template import (
    ChartOfAccountsTemplate,
)
from openbilanz.domain.closing_consistency_result import (
    ClosingConsistencyResult,
)
from openbilanz.domain.company import Company
from openbilanz.domain.company_master_data import (
    CompanyMasterData,
)
from openbilanz.domain.depreciation_kind import (
    DepreciationKind,
)
from openbilanz.domain.depreciation_proposal import (
    DepreciationProposal,
)
from openbilanz.domain.depreciation_source import (
    DepreciationSource,
)
from openbilanz.domain.entry_side import EntrySide
from openbilanz.domain.fiscal_year import FiscalYear
from openbilanz.domain.fiscal_year_status import FiscalYearStatus
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
from openbilanz.domain.journal import Journal
from openbilanz.domain.managed_fiscal_year import ManagedFiscalYear
from openbilanz.domain.shareholder import Shareholder
from openbilanz.domain.tax_depreciation_adjustment import (
    TaxDepreciationAdjustment,
)
from openbilanz.domain.vat_accounts import VatAccounts
from openbilanz.domain.bvv_annual_data import BvvAnnualData
from openbilanz.services.closing_result import ClosingResult
from openbilanz.services.e_bilanz_export_service import (
    EBilanzExportService,
)
from openbilanz.services.fiscal_year_workspace import FiscalYearWorkspace
from openbilanz.services.posting_service import PostingService
from openbilanz.services.taxonomy_management_service import (
    TaxonomyManagementService,
    TaxonomyStatus,
)
from openbilanz.taxonomy.arelle_adapter import (
    ArelleValidationResult,
)
from openbilanz.taxonomy.e_bilanz_builder import (
    EBilanzDocument,
)
from openbilanz.taxonomy.taxonomy import TaxonomyVersion


@pytest.fixture
def company() -> Company:
    return Company(
        company_id=uuid4(),
        name="Test UG",
    )


@pytest.fixture
def fiscal_year() -> FiscalYear:
    return FiscalYear(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )


@pytest.fixture
def context(
    company: Company,
    fiscal_year: FiscalYear,
) -> ApplicationContext:
    return ApplicationContext(
        company=company,
        fiscal_year=fiscal_year,
    )


def test_reconstructs_empty_workspace(
    context: ApplicationContext,
) -> None:
    booking_repository = Mock()
    company_repository = Mock()
    posting_service = Mock()
    closing_workflow = Mock()

    booking_repository.list_for_fiscal_year.return_value = ()

    workspace = FiscalYearWorkspace(
        context=context,
        booking_repository=booking_repository,
        company_repository=company_repository,
        posting_service=posting_service,
        closing_workflow=closing_workflow,
        closing_consistency_service=Mock(),
        e_bilanz_preparation_service=Mock(),
        e_bilanz_service=Mock(),
        e_bilanz_account_detail_service=Mock(),
        taxonomy_management_service=Mock(),
        e_bilanz_export_service=Mock(),
    )

    assert isinstance(workspace.journal, Journal)
    assert isinstance(workspace.ledger, Ledger)
    assert isinstance(
        workspace.pre_closing_ledger,
        Ledger,
    )
    assert len(workspace.journal) == 0

    booking_repository.list_for_fiscal_year.assert_called_once_with(
        company_id=context.company.company_id,
        fiscal_year=context.fiscal_year,
    )


def test_reports_open_fiscal_year(
    context: ApplicationContext,
) -> None:
    booking_repository = Mock()
    company_repository = Mock()
    posting_service = Mock()
    closing_workflow = Mock()

    booking_repository.list_for_fiscal_year.return_value = ()

    company_repository.get_managed_fiscal_years.return_value = (
        ManagedFiscalYear(
            fiscal_year=context.fiscal_year,
            status=FiscalYearStatus.OPEN,
            opening_source=None,
        ),
    )

    workspace = FiscalYearWorkspace(
        context=context,
        booking_repository=booking_repository,
        company_repository=company_repository,
        posting_service=posting_service,
        closing_workflow=closing_workflow,
        closing_consistency_service=Mock(),
        e_bilanz_preparation_service=Mock(),
        e_bilanz_service=Mock(),
        e_bilanz_account_detail_service=Mock(),
        taxonomy_management_service=Mock(),
        e_bilanz_export_service=Mock(),
    )

    assert workspace.is_open is True
    assert workspace.is_closed is False


def test_reports_closed_fiscal_year(
    context: ApplicationContext,
) -> None:
    booking_repository = Mock()
    company_repository = Mock()
    posting_service = Mock()
    closing_workflow = Mock()

    booking_repository.list_for_fiscal_year.return_value = ()

    company_repository.get_managed_fiscal_years.return_value = (
        ManagedFiscalYear(
            fiscal_year=context.fiscal_year,
            status=FiscalYearStatus.CLOSED,
            opening_source=None,
        ),
    )

    workspace = FiscalYearWorkspace(
        context=context,
        booking_repository=booking_repository,
        company_repository=company_repository,
        posting_service=posting_service,
        closing_workflow=closing_workflow,
        closing_consistency_service=Mock(),
        e_bilanz_preparation_service=Mock(),
        e_bilanz_service=Mock(),
        e_bilanz_account_detail_service=Mock(),
        taxonomy_management_service=Mock(),
        e_bilanz_export_service=Mock(),
    )

    assert workspace.is_open is False
    assert workspace.is_closed is True

def test_reports_taxonomy_status_for_opened_fiscal_year(
    context: ApplicationContext,
) -> None:
    booking_repository = Mock()
    company_repository = Mock()
    taxonomy_management_service = Mock(
        spec=TaxonomyManagementService
    )

    booking_repository.list_for_fiscal_year.return_value = ()

    expected_status = TaxonomyStatus(
        required_version=TaxonomyVersion.V6_9,
        installed=True,
        complete=True,
    )

    taxonomy_management_service.status_for.return_value = (
        expected_status
    )

    workspace = FiscalYearWorkspace(
        context=context,
        booking_repository=booking_repository,
        company_repository=company_repository,
        posting_service=Mock(),
        closing_workflow=Mock(),
        closing_consistency_service=Mock(),
        e_bilanz_preparation_service=Mock(),
        e_bilanz_service=Mock(),
        e_bilanz_account_detail_service=Mock(),
        taxonomy_management_service=(
            taxonomy_management_service
        ),
        e_bilanz_export_service=Mock(),
    )

    status = workspace.taxonomy_status

    assert status is expected_status

    taxonomy_management_service.status_for.assert_called_once_with(
        context.fiscal_year
    )

def test_raises_when_managed_fiscal_year_is_missing(
    context: ApplicationContext,
) -> None:
    booking_repository = Mock()
    company_repository = Mock()
    posting_service = Mock()
    closing_workflow = Mock()

    booking_repository.list_for_fiscal_year.return_value = ()
    company_repository.get_managed_fiscal_years.return_value = ()

    workspace = FiscalYearWorkspace(
        context=context,
        booking_repository=booking_repository,
        company_repository=company_repository,
        posting_service=posting_service,
        closing_workflow=closing_workflow,
        closing_consistency_service=Mock(),
        e_bilanz_preparation_service=Mock(),
        e_bilanz_service=Mock(),
        e_bilanz_account_detail_service=Mock(),
        taxonomy_management_service=Mock(),
        e_bilanz_export_service=Mock(),
    )

    with pytest.raises(
        ValueError,
        match="Das geöffnete Geschäftsjahr wurde nicht gefunden.",
    ):
        _ = workspace.managed_fiscal_year


def test_post_booking_persists_and_reloads_workspace(
    context: ApplicationContext,
) -> None:
    booking_repository = Mock()
    company_repository = Mock()
    closing_workflow = Mock()

    posting_service = PostingService()

    booking = Booking(
        booking_date=date(2026, 3, 15),
        voucher_no="B-001",
        description="Testbuchung",
        lines=(
            BookingLine(
                account_number="1200",
                side=EntrySide.DEBIT,
                amount=Decimal("100.00"),
            ),
            BookingLine(
                account_number="1800",
                side=EntrySide.CREDIT,
                amount=Decimal("100.00"),
            ),
        ),
    )

    booking_repository.list_for_fiscal_year.side_effect = (
        (),
        (booking,),
    )

    workspace = FiscalYearWorkspace(
        context=context,
        booking_repository=booking_repository,
        company_repository=company_repository,
        posting_service=posting_service,
        closing_workflow=closing_workflow,
        closing_consistency_service=Mock(),
        e_bilanz_preparation_service=Mock(),
        e_bilanz_service=Mock(),
        e_bilanz_account_detail_service=Mock(),
        taxonomy_management_service=Mock(),
        e_bilanz_export_service=Mock(),
    )

    assert len(workspace.journal) == 0

    workspace.post_booking(booking)

    booking_repository.add.assert_called_once_with(
        company_id=context.company.company_id,
        fiscal_year=context.fiscal_year,
        booking=booking,
    )

    assert len(workspace.journal) == 1
    assert tuple(workspace.journal) == (booking,)

    account = workspace.ledger.get_account("1200")

    assert account.debit == Decimal("100.00")
    assert account.credit == Decimal("0.00")


def test_post_booking_does_not_change_workspace_when_persistence_fails(
    context: ApplicationContext,
) -> None:
    booking_repository = Mock()
    company_repository = Mock()
    closing_workflow = Mock()

    posting_service = PostingService()

    booking_repository.list_for_fiscal_year.return_value = ()
    booking_repository.add.side_effect = ValueError(
        "Das Geschäftsjahr ist abgeschlossen."
    )

    booking = Booking(
        booking_date=date(2026, 3, 15),
        voucher_no="B-002",
        description="Nicht zulässige Buchung",
        lines=(
            BookingLine(
                account_number="1200",
                side=EntrySide.DEBIT,
                amount=Decimal("50.00"),
            ),
            BookingLine(
                account_number="1800",
                side=EntrySide.CREDIT,
                amount=Decimal("50.00"),
            ),
        ),
    )

    workspace = FiscalYearWorkspace(
        context=context,
        booking_repository=booking_repository,
        company_repository=company_repository,
        posting_service=posting_service,
        closing_workflow=closing_workflow,
        closing_consistency_service=Mock(),
        e_bilanz_preparation_service=Mock(),
        e_bilanz_service=Mock(),
        e_bilanz_account_detail_service=Mock(),
        taxonomy_management_service=Mock(),
        e_bilanz_export_service=Mock(),
    )

    with pytest.raises(
        ValueError,
        match="Das Geschäftsjahr ist abgeschlossen.",
    ):
        workspace.post_booking(booking)

    assert len(workspace.journal) == 0

    with pytest.raises(KeyError):
        workspace.ledger.get_account("1200")

    booking_repository.list_for_fiscal_year.assert_called_once_with(
        company_id=context.company.company_id,
        fiscal_year=context.fiscal_year,
    )

def test_create_reversal_booking_mirrors_original_booking(
    context: ApplicationContext,
) -> None:
    """Erzeugt eine vollständige Stornobuchung ohne Persistenz."""

    booking_repository = Mock()
    company_repository = Mock()

    original_booking = Booking(
        booking_date=date(2026, 8, 8),
        voucher_no="RE-001",
        description="Ausgangsrechnung",
        lines=(
            BookingLine(
                account_number="1200",
                side=EntrySide.DEBIT,
                amount=Decimal("119.00"),
            ),
            BookingLine(
                account_number="8400",
                side=EntrySide.CREDIT,
                amount=Decimal("100.00"),
            ),
            BookingLine(
                account_number="1776",
                side=EntrySide.CREDIT,
                amount=Decimal("19.00"),
            ),
        ),
    )

    booking_repository.list_for_fiscal_year.return_value = (
        original_booking,
    )

    company_repository.get_managed_fiscal_years.return_value = (
        ManagedFiscalYear(
            fiscal_year=context.fiscal_year,
            status=FiscalYearStatus.OPEN,
            opening_source=None,
        ),
    )

    workspace = FiscalYearWorkspace(
        context=context,
        booking_repository=booking_repository,
        company_repository=company_repository,
        posting_service=PostingService(),
        closing_workflow=Mock(),
        closing_consistency_service=Mock(),
        e_bilanz_preparation_service=Mock(),
        e_bilanz_service=Mock(),
        e_bilanz_account_detail_service=Mock(),
        taxonomy_management_service=Mock(),
        e_bilanz_export_service=Mock(),
    )

    reversal_booking = workspace.create_reversal_booking(
        booking_id=original_booking.booking_id,
        reversal_date=date(2026, 8, 9),
    )

    assert (
        reversal_booking.booking_type
        is BookingType.REVERSAL
    )
    assert (
        reversal_booking.reversal_of_booking_id
        == original_booking.booking_id
    )
    assert reversal_booking.booking_date == date(
        2026,
        8,
        9,
    )
    assert reversal_booking.voucher_no is None
    assert reversal_booking.description == (
        "Storno zu Buchung RE-001: Ausgangsrechnung"
    )

    assert reversal_booking.lines == (
        BookingLine(
            account_number="1200",
            side=EntrySide.CREDIT,
            amount=Decimal("119.00"),
        ),
        BookingLine(
            account_number="8400",
            side=EntrySide.DEBIT,
            amount=Decimal("100.00"),
        ),
        BookingLine(
            account_number="1776",
            side=EntrySide.DEBIT,
            amount=Decimal("19.00"),
        ),
    )

    booking_repository.add.assert_not_called()

@pytest.mark.parametrize(
    "booking_type",
    (
        BookingType.OPENING,
        BookingType.CLOSING,
        BookingType.REVERSAL,
    ),
)
def test_create_reversal_booking_rejects_non_regular_booking(
    context: ApplicationContext,
    booking_type: BookingType,
) -> None:
    """Nur reguläre Buchungen dürfen über das Journal storniert werden."""

    booking_repository = Mock()
    company_repository = Mock()

    original_booking = Booking(
        booking_date=date(2026, 8, 8),
        description="Nicht reguläre Buchung",
        booking_type=booking_type,
        reversal_of_booking_id=(
            uuid4()
            if booking_type is BookingType.REVERSAL
            else None
        ),
        lines=(
            BookingLine(
                account_number="1200",
                side=EntrySide.DEBIT,
                amount=Decimal("100.00"),
            ),
            BookingLine(
                account_number="1800",
                side=EntrySide.CREDIT,
                amount=Decimal("100.00"),
            ),
        ),
    )

    booking_repository.list_for_fiscal_year.return_value = (
        original_booking,
    )

    company_repository.get_managed_fiscal_years.return_value = (
        ManagedFiscalYear(
            fiscal_year=context.fiscal_year,
            status=FiscalYearStatus.OPEN,
            opening_source=None,
        ),
    )

    workspace = FiscalYearWorkspace(
        context=context,
        booking_repository=booking_repository,
        company_repository=company_repository,
        posting_service=PostingService(),
        closing_workflow=Mock(),
        closing_consistency_service=Mock(),
        e_bilanz_preparation_service=Mock(),
        e_bilanz_service=Mock(),
        e_bilanz_account_detail_service=Mock(),
        taxonomy_management_service=Mock(),
        e_bilanz_export_service=Mock(),
    )

    with pytest.raises(
        ValueError,
        match="Nur reguläre Buchungen",
    ):
        workspace.create_reversal_booking(
            booking_id=original_booking.booking_id,
            reversal_date=date(2026, 8, 9),
        )

    booking_repository.add.assert_not_called()

def test_create_reversal_booking_rejects_already_reversed_booking(
    context: ApplicationContext,
) -> None:
    """Eine bereits stornierte Buchung darf nicht erneut storniert werden."""

    booking_repository = Mock()
    company_repository = Mock()

    original_booking = Booking(
        booking_date=date(2026, 8, 8),
        voucher_no="RE-002",
        description="Ausgangsrechnung",
        lines=(
            BookingLine(
                account_number="1200",
                side=EntrySide.DEBIT,
                amount=Decimal("119.00"),
            ),
            BookingLine(
                account_number="8400",
                side=EntrySide.CREDIT,
                amount=Decimal("100.00"),
            ),
            BookingLine(
                account_number="1776",
                side=EntrySide.CREDIT,
                amount=Decimal("19.00"),
            ),
        ),
    )

    existing_reversal = Booking(
        booking_date=date(2026, 8, 9),
        description="Storno zu Buchung RE-002",
        booking_type=BookingType.REVERSAL,
        reversal_of_booking_id=original_booking.booking_id,
        lines=(
            BookingLine(
                account_number="1200",
                side=EntrySide.CREDIT,
                amount=Decimal("119.00"),
            ),
            BookingLine(
                account_number="8400",
                side=EntrySide.DEBIT,
                amount=Decimal("100.00"),
            ),
            BookingLine(
                account_number="1776",
                side=EntrySide.DEBIT,
                amount=Decimal("19.00"),
            ),
        ),
    )

    booking_repository.list_for_fiscal_year.return_value = (
        original_booking,
        existing_reversal,
    )

    company_repository.get_managed_fiscal_years.return_value = (
        ManagedFiscalYear(
            fiscal_year=context.fiscal_year,
            status=FiscalYearStatus.OPEN,
            opening_source=None,
        ),
    )

    workspace = FiscalYearWorkspace(
        context=context,
        booking_repository=booking_repository,
        company_repository=company_repository,
        posting_service=PostingService(),
        closing_workflow=Mock(),
        closing_consistency_service=Mock(),
        e_bilanz_preparation_service=Mock(),
        e_bilanz_service=Mock(),
        e_bilanz_account_detail_service=Mock(),
        taxonomy_management_service=Mock(),
        e_bilanz_export_service=Mock(),
    )

    with pytest.raises(
        ValueError,
        match="bereits storniert",
    ):
        workspace.create_reversal_booking(
            booking_id=original_booking.booking_id,
            reversal_date=date(2026, 8, 10),
        )

    booking_repository.add.assert_not_called()

def test_lists_confirmed_depreciations_for_open_fiscal_year(
    context: ApplicationContext,
) -> None:
    booking_repository = Mock()
    company_repository = Mock()
    fixed_asset_repository = Mock()
    depreciation_repository = Mock()

    booking_repository.list_for_fiscal_year.return_value = ()

    asset = FixedAsset(
        company_id=context.company.company_id,
        asset_code="A-0001",
        description="MacBook Pro",
        position_code="HGB.266.AKTIVA.A.II.3",
        asset_account_number="0690",
        depreciation_expense_account_number="4830",
        acquisition_date=date(2025, 3, 15),
        acquisition_cost=Decimal("2400.00"),
        depreciation_start_date=date(2025, 3, 15),
        useful_life_months=36,
    )

    previous_depreciation = FixedAssetDepreciation(
        fixed_asset_id=asset.fixed_asset_id,
        fiscal_year_end=date(2025, 12, 31),
        depreciation_date=date(2025, 12, 31),
        amount=Decimal("600.00"),
        booking_id=uuid4(),
        kind=DepreciationKind.LINEAR,
        source=DepreciationSource.CALCULATED,
    )

    current_depreciation = FixedAssetDepreciation(
        fixed_asset_id=asset.fixed_asset_id,
        fiscal_year_end=context.fiscal_year.end_date,
        depreciation_date=context.fiscal_year.end_date,
        amount=Decimal("800.00"),
        booking_id=uuid4(),
        kind=DepreciationKind.LINEAR,
        source=DepreciationSource.CALCULATED,
    )

    fixed_asset_repository.list_for_company.return_value = (
        asset,
    )
    fixed_asset_repository.get.return_value = asset

    depreciation_repository.list_for_fixed_asset.return_value = (
        previous_depreciation,
        current_depreciation,
    )

    workspace = FiscalYearWorkspace(
        context=context,
        booking_repository=booking_repository,
        company_repository=company_repository,
        posting_service=Mock(),
        closing_workflow=Mock(),
        closing_consistency_service=Mock(),
        e_bilanz_preparation_service=Mock(),
        e_bilanz_service=Mock(),
        e_bilanz_account_detail_service=Mock(),
        e_bilanz_export_service=Mock(),
        taxonomy_management_service=Mock(),
        fixed_asset_repository=(
            fixed_asset_repository
        ),
        fixed_asset_depreciation_repository=(
            depreciation_repository
        ),
    )

    result = workspace.list_confirmed_depreciations()

    assert result == (
        current_depreciation,
    )

    fixed_asset_repository.list_for_company.assert_called_once_with(
        context.company.company_id
    )

    depreciation_repository.list_for_fixed_asset.assert_called_once_with(
        asset.fixed_asset_id
    )


def test_list_confirmed_depreciations_requires_fixed_asset_configuration(
    context: ApplicationContext,
) -> None:
    booking_repository = Mock()

    booking_repository.list_for_fiscal_year.return_value = ()

    workspace = FiscalYearWorkspace(
        context=context,
        booking_repository=booking_repository,
        company_repository=Mock(),
        posting_service=Mock(),
        closing_workflow=Mock(),
        closing_consistency_service=Mock(),
        e_bilanz_preparation_service=Mock(),
        e_bilanz_service=Mock(),
        e_bilanz_account_detail_service=Mock(),
        e_bilanz_export_service=Mock(),
        taxonomy_management_service=Mock(),
    )

    with pytest.raises(
        RuntimeError,
        match="Die Anlagenbuchhaltung ist nicht konfiguriert.",
    ):
        workspace.list_confirmed_depreciations()


def test_aggregates_tax_depreciation_difference_for_bga(
    context: ApplicationContext,
) -> None:
    booking_repository = Mock()
    company_repository = Mock()
    fixed_asset_repository = Mock()
    depreciation_repository = Mock()
    adjustment_repository = Mock()

    booking_repository.list_for_fiscal_year.return_value = ()

    bga_asset = FixedAsset(
        company_id=context.company.company_id,
        asset_code="BGA-001",
        description="MacBook Pro",
        position_code="HGB.266.AKTIVA.A.II.3",
        asset_account_number="0690",
        depreciation_expense_account_number="4830",
        acquisition_date=date(2026, 1, 1),
        acquisition_cost=Decimal("2400.00"),
        depreciation_start_date=date(2026, 1, 1),
        useful_life_months=36,
    )

    other_asset = FixedAsset(
        company_id=context.company.company_id,
        asset_code="MAS-001",
        description="Maschine",
        position_code="HGB.266.AKTIVA.A.II.2",
        asset_account_number="0400",
        depreciation_expense_account_number="4830",
        acquisition_date=date(2026, 1, 1),
        acquisition_cost=Decimal("12000.00"),
        depreciation_start_date=date(2026, 1, 1),
        useful_life_months=60,
    )

    first_bga_depreciation = FixedAssetDepreciation(
        fixed_asset_id=bga_asset.fixed_asset_id,
        fiscal_year_end=context.fiscal_year.end_date,
        depreciation_date=context.fiscal_year.end_date,
        amount=Decimal("600.00"),
        booking_id=uuid4(),
        kind=DepreciationKind.LINEAR,
        source=DepreciationSource.CALCULATED,
    )

    second_bga_depreciation = FixedAssetDepreciation(
        fixed_asset_id=bga_asset.fixed_asset_id,
        fiscal_year_end=context.fiscal_year.end_date,
        depreciation_date=context.fiscal_year.end_date,
        amount=Decimal("200.00"),
        booking_id=uuid4(),
        kind=DepreciationKind.LINEAR,
        source=DepreciationSource.CALCULATED,
    )

    other_depreciation = FixedAssetDepreciation(
        fixed_asset_id=other_asset.fixed_asset_id,
        fiscal_year_end=context.fiscal_year.end_date,
        depreciation_date=context.fiscal_year.end_date,
        amount=Decimal("1000.00"),
        booking_id=uuid4(),
        kind=DepreciationKind.LINEAR,
        source=DepreciationSource.CALCULATED,
    )

    fixed_asset_repository.list_for_company.return_value = (
        bga_asset,
        other_asset,
    )

    depreciation_repository.list_for_fixed_asset.side_effect = (
        lambda fixed_asset_id: {
            bga_asset.fixed_asset_id: (
                first_bga_depreciation,
                second_bga_depreciation,
            ),
            other_asset.fixed_asset_id: (
                other_depreciation,
            ),
        }[fixed_asset_id]
    )

    adjustments = {
        first_bga_depreciation.depreciation_id: (
            TaxDepreciationAdjustment(
                depreciation_id=(
                    first_bga_depreciation.depreciation_id
                ),
                commercial_amount=Decimal("600.00"),
                tax_amount=Decimal("620.00"),
            )
        ),
        second_bga_depreciation.depreciation_id: (
            TaxDepreciationAdjustment(
                depreciation_id=(
                    second_bga_depreciation.depreciation_id
                ),
                commercial_amount=Decimal("200.00"),
                tax_amount=Decimal("195.00"),
            )
        ),
        other_depreciation.depreciation_id: (
            TaxDepreciationAdjustment(
                depreciation_id=other_depreciation.depreciation_id,
                commercial_amount=Decimal("1000.00"),
                tax_amount=Decimal("1100.00"),
            )
        ),
    }

    adjustment_repository.get_for_depreciation.side_effect = (
        lambda depreciation_id: adjustments.get(depreciation_id)
    )

    workspace = FiscalYearWorkspace(
        context=context,
        booking_repository=booking_repository,
        company_repository=company_repository,
        posting_service=Mock(),
        closing_workflow=Mock(),
        closing_consistency_service=Mock(),
        e_bilanz_preparation_service=Mock(),
        e_bilanz_service=Mock(),
        e_bilanz_account_detail_service=Mock(),
        e_bilanz_export_service=Mock(),
        taxonomy_management_service=Mock(),
        fixed_asset_repository=fixed_asset_repository,
        fixed_asset_depreciation_repository=(
            depreciation_repository
        ),
        tax_depreciation_adjustment_repository=(
            adjustment_repository
        ),
    )

    result = workspace.tax_depreciation_difference_for_bga()

    assert result == Decimal("15.00")

    assert (
        adjustment_repository.get_for_depreciation.call_count
        == 2
    )

    adjustment_repository.get_for_depreciation.assert_any_call(
        first_bga_depreciation.depreciation_id
    )
    adjustment_repository.get_for_depreciation.assert_any_call(
        second_bga_depreciation.depreciation_id
    )

def test_aggregates_current_and_previous_tax_depreciation_differences_for_bga(
    context: ApplicationContext,
) -> None:
    booking_repository = Mock()
    company_repository = Mock()
    fixed_asset_repository = Mock()
    depreciation_repository = Mock()
    adjustment_repository = Mock()

    booking_repository.list_for_fiscal_year.return_value = ()

    bga_asset = FixedAsset(
        company_id=context.company.company_id,
        asset_code="BGA-001",
        description="Maschine 1",
        position_code="HGB.266.AKTIVA.A.II.3",
        asset_account_number="0400",
        depreciation_expense_account_number="4830",
        acquisition_date=date(2025, 1, 1),
        acquisition_cost=Decimal("1000.00"),
        depreciation_start_date=date(2025, 1, 1),
        useful_life_months=36,
    )

    other_asset = FixedAsset(
        company_id=context.company.company_id,
        asset_code="MAS-001",
        description="Andere Maschine",
        position_code="HGB.266.AKTIVA.A.II.2",
        asset_account_number="0500",
        depreciation_expense_account_number="4830",
        acquisition_date=date(2025, 1, 1),
        acquisition_cost=Decimal("2000.00"),
        depreciation_start_date=date(2025, 1, 1),
        useful_life_months=60,
    )

    previous_depreciation = FixedAssetDepreciation(
        fixed_asset_id=bga_asset.fixed_asset_id,
        fiscal_year_end=date(2025, 12, 31),
        depreciation_date=date(2025, 12, 31),
        amount=Decimal("333.33"),
        booking_id=uuid4(),
        kind=DepreciationKind.LINEAR,
        source=DepreciationSource.CALCULATED,
    )

    current_depreciation = FixedAssetDepreciation(
        fixed_asset_id=bga_asset.fixed_asset_id,
        fiscal_year_end=context.fiscal_year.end_date,
        depreciation_date=context.fiscal_year.end_date,
        amount=Decimal("333.33"),
        booking_id=uuid4(),
        kind=DepreciationKind.LINEAR,
        source=DepreciationSource.CALCULATED,
    )

    other_depreciation = FixedAssetDepreciation(
        fixed_asset_id=other_asset.fixed_asset_id,
        fiscal_year_end=context.fiscal_year.end_date,
        depreciation_date=context.fiscal_year.end_date,
        amount=Decimal("400.00"),
        booking_id=uuid4(),
        kind=DepreciationKind.LINEAR,
        source=DepreciationSource.CALCULATED,
    )

    fixed_asset_repository.list_for_company.return_value = (
        bga_asset,
        other_asset,
    )

    depreciation_repository.list_for_fixed_asset.side_effect = (
        lambda fixed_asset_id: {
            bga_asset.fixed_asset_id: (
                previous_depreciation,
                current_depreciation,
            ),
            other_asset.fixed_asset_id: (
                other_depreciation,
            ),
        }[fixed_asset_id]
    )

    adjustments = {
        previous_depreciation.depreciation_id: (
            TaxDepreciationAdjustment(
                depreciation_id=(
                    previous_depreciation.depreciation_id
                ),
                commercial_amount=Decimal("333.33"),
                tax_amount=Decimal("250.00"),
            )
        ),
        current_depreciation.depreciation_id: (
            TaxDepreciationAdjustment(
                depreciation_id=(
                    current_depreciation.depreciation_id
                ),
                commercial_amount=Decimal("333.33"),
                tax_amount=Decimal("250.00"),
            )
        ),
        other_depreciation.depreciation_id: (
            TaxDepreciationAdjustment(
                depreciation_id=(
                    other_depreciation.depreciation_id
                ),
                commercial_amount=Decimal("400.00"),
                tax_amount=Decimal("300.00"),
            )
        ),
    }

    adjustment_repository.get_for_depreciation.side_effect = (
        lambda depreciation_id: adjustments.get(
            depreciation_id
        )
    )

    workspace = FiscalYearWorkspace(
        context=context,
        booking_repository=booking_repository,
        company_repository=company_repository,
        posting_service=Mock(),
        closing_workflow=Mock(),
        closing_consistency_service=Mock(),
        e_bilanz_preparation_service=Mock(),
        e_bilanz_service=Mock(),
        e_bilanz_account_detail_service=Mock(),
        e_bilanz_export_service=Mock(),
        taxonomy_management_service=Mock(),
        fixed_asset_repository=fixed_asset_repository,
        fixed_asset_depreciation_repository=(
            depreciation_repository
        ),
        tax_depreciation_adjustment_repository=(
            adjustment_repository
        ),
    )

    (
        current_difference,
        previous_difference,
    ) = workspace.tax_depreciation_differences_for_bga()

    assert current_difference == Decimal("-83.33")
    assert previous_difference == Decimal("-83.33")

    depreciation_repository.list_for_fixed_asset.assert_called_once_with(
        bga_asset.fixed_asset_id
    )

    assert (
        adjustment_repository.get_for_depreciation.call_count
        == 2
    )

    adjustment_repository.get_for_depreciation.assert_any_call(
        previous_depreciation.depreciation_id
    )
    adjustment_repository.get_for_depreciation.assert_any_call(
        current_depreciation.depreciation_id
    )

def test_calculates_opening_hgb_equity_from_trial_balance_mappings(
    context: ApplicationContext,
) -> None:
    booking_repository = Mock()
    company_repository = Mock()

    booking_repository.list_for_fiscal_year.return_value = ()

    workspace = FiscalYearWorkspace(
        context=context,
        booking_repository=booking_repository,
        company_repository=company_repository,
        posting_service=Mock(),
        closing_workflow=Mock(),
        closing_consistency_service=Mock(),
        e_bilanz_preparation_service=Mock(),
        e_bilanz_service=Mock(),
        e_bilanz_account_detail_service=Mock(),
        e_bilanz_export_service=Mock(),
        taxonomy_management_service=Mock(),
    )

    control_accounts = Mock(
        opening_balance_account="9000",
    )

    workspace.load_account_configuration = Mock(
        return_value=(
            control_accounts,
            Mock(),
            Mock(),
        )
    )

    report = Mock()
    report.rows = (
        Mock(
            account_number="0800",
            opening_debit=Decimal("0.00"),
            opening_credit=Decimal("10000.00"),
        ),
        Mock(
            account_number="2970",
            opening_debit=Decimal("0.00"),
            opening_credit=Decimal("3868.35"),
        ),
        Mock(
            account_number="1200",
            opening_debit=Decimal("8810.00"),
            opening_credit=Decimal("0.00"),
        ),
    )

    workspace.build_trial_balance_report = Mock(
        return_value=report
    )

    capital_position = Mock(
        code="HGB.266.PASSIVA.A.I"
    )
    retained_earnings_position = Mock(
        code="HGB.266.PASSIVA.A.IV"
    )
    bank_position = Mock(
        code="HGB.266.AKTIVA.B.IV"
    )

    capital_rule = Mock(
        account_number="0800",
        debit_position=capital_position,
        credit_position=capital_position,
    )
    retained_earnings_rule = Mock(
        account_number="2970",
        debit_position=retained_earnings_position,
        credit_position=retained_earnings_position,
    )
    bank_rule = Mock(
        account_number="1200",
        debit_position=bank_position,
        credit_position=bank_position,
    )

    chart_of_accounts = Mock()
    chart_of_accounts.account_mapping_rules = (
        capital_rule,
        retained_earnings_rule,
        bank_rule,
    )

    result = workspace.opening_hgb_equity(
        chart_of_accounts=chart_of_accounts,
    )

    assert result == Decimal("13868.35")

    workspace.build_trial_balance_report.assert_called_once_with(
        start_date=context.fiscal_year.start_date,
        end_date=context.fiscal_year.end_date,
        opening_balance_account_number="9000",
    )

def test_builds_open_depreciation_proposal(
    context: ApplicationContext,
) -> None:
    booking_repository = Mock()
    company_repository = Mock()
    fixed_asset_repository = Mock()
    fixed_asset_movement_repository = Mock()
    depreciation_repository = Mock()
    depreciation_service = Mock()

    booking_repository.list_for_fiscal_year.return_value = ()

    company_repository.get_managed_fiscal_years.return_value = (
        ManagedFiscalYear(
            fiscal_year=context.fiscal_year,
            status=FiscalYearStatus.OPEN,
            opening_source=None,
        ),
    )

    asset = FixedAsset(
        company_id=context.company.company_id,
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

    acquisition_movement = FixedAssetMovement(
        fixed_asset_id=asset.fixed_asset_id,
        fiscal_year_end=context.fiscal_year.end_date,
        movement_date=asset.acquisition_date,
        amount=asset.acquisition_cost,
        booking_id=uuid4(),
        movement_type=FixedAssetMovementType.ACQUISITION,
    )

    proposal = DepreciationProposal(
        fixed_asset_id=asset.fixed_asset_id,
        depreciation_date=context.fiscal_year.end_date,
        amount=Decimal("600.00"),
        expense_account_number="4830",
        asset_account_number="0690",
    )

    fixed_asset_repository.list_for_company.return_value = (
        asset,
    )

    fixed_asset_movement_repository.list_for_fixed_asset.return_value = (
        acquisition_movement,
    )

    depreciation_repository.list_for_fixed_asset.return_value = ()

    depreciation_service.build_proposal.return_value = (
        proposal
    )

    workspace = FiscalYearWorkspace(
        context=context,
        booking_repository=booking_repository,
        company_repository=company_repository,
        posting_service=Mock(),
        closing_workflow=Mock(),
        closing_consistency_service=Mock(),
        e_bilanz_preparation_service=Mock(),
        e_bilanz_service=Mock(),
        e_bilanz_account_detail_service=Mock(),
        e_bilanz_export_service=Mock(),
        taxonomy_management_service=Mock(),
        fixed_asset_repository=(
            fixed_asset_repository
        ),
        fixed_asset_movement_repository=(
            fixed_asset_movement_repository
        ),
        fixed_asset_depreciation_repository=(
            depreciation_repository
        ),
        depreciation_service=(
            depreciation_service
        ),
        fixed_asset_depreciation_workflow=Mock(),
    )

    proposals = (
        workspace.build_depreciation_proposals()
    )

    assert proposals == (proposal,)

    fixed_asset_movement_repository.list_for_fixed_asset.assert_called_once_with(
        asset.fixed_asset_id
    )

    depreciation_service.build_proposal.assert_called_once_with(
        fixed_asset=asset,
        fiscal_year=context.fiscal_year,
        previous_depreciation=Decimal("0.00"),
        expense_account_number="4830",
        asset_account_number="0690",
        depreciation_end_date=None,
    )

def test_builds_fixed_asset_disposal_preview(
    context: ApplicationContext,
) -> None:
    booking_repository = Mock()
    company_repository = Mock()
    chart_of_accounts_repository = Mock()
    fixed_asset_repository = Mock()
    fixed_asset_movement_repository = Mock()
    depreciation_repository = Mock()
    depreciation_service = Mock()
    disposal_service = Mock()

    company_repository.get_managed_fiscal_years.return_value = (
        ManagedFiscalYear(
            fiscal_year=context.fiscal_year,
            status=FiscalYearStatus.OPEN,
            opening_source=None,
        ),
    )

    asset = FixedAsset(
        company_id=context.company.company_id,
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

    acquisition_movement = FixedAssetMovement(
        fixed_asset_id=asset.fixed_asset_id,
        fiscal_year_end=context.fiscal_year.end_date,
        movement_date=asset.acquisition_date,
        amount=asset.acquisition_cost,
        booking_id=uuid4(),
        movement_type=FixedAssetMovementType.ACQUISITION,
    )

    proposal = DepreciationProposal(
        fixed_asset_id=asset.fixed_asset_id,
        depreciation_date=date(2026, 8, 15),
        amount=Decimal("400.00"),
        expense_account_number="4830",
        asset_account_number="0690",
    )

    control_accounts = Mock(
        spec=AccountingControlAccounts
    )
    vat_accounts = Mock(
        spec=VatAccounts
    )
    account_roles = Mock(
        spec=AccountingAccountRoles
    )
    disposal_calculation = Mock()

    fixed_asset_repository.get.return_value = asset

    (
        fixed_asset_movement_repository
        .list_for_fixed_asset
        .return_value
    ) = (
        acquisition_movement,
    )

    depreciation_repository.list_for_fixed_asset.return_value = ()

    depreciation_service.build_proposal.return_value = (
        proposal
    )

    (
        chart_of_accounts_repository
        .load_control_accounts
        .return_value
    ) = control_accounts
    (
        chart_of_accounts_repository
        .load_vat_accounts
        .return_value
    ) = vat_accounts
    (
        chart_of_accounts_repository
        .load_account_roles
        .return_value
    ) = account_roles

    disposal_service.calculate.return_value = (
        disposal_calculation
    )

    booking_repository.list_for_fiscal_year.return_value = ()

    workspace = FiscalYearWorkspace(
        context=context,
        booking_repository=booking_repository,
        company_repository=company_repository,
        chart_of_accounts_repository=(
            chart_of_accounts_repository
        ),
        posting_service=Mock(),
        closing_workflow=Mock(),
        closing_consistency_service=Mock(),
        e_bilanz_preparation_service=Mock(),
        e_bilanz_service=Mock(),
        e_bilanz_account_detail_service=Mock(),
        e_bilanz_export_service=Mock(),
        taxonomy_management_service=Mock(),
        fixed_asset_repository=(
            fixed_asset_repository
        ),
        fixed_asset_movement_repository=(
            fixed_asset_movement_repository
        ),
        fixed_asset_depreciation_repository=(
            depreciation_repository
        ),
        depreciation_service=(
            depreciation_service
        ),
        fixed_asset_depreciation_workflow=Mock(),
        fixed_asset_disposal_service=(
            disposal_service
        ),
    )

    preview = workspace.build_fixed_asset_disposal_preview(
        fixed_asset_id=asset.fixed_asset_id,
        disposal_date=date(2026, 8, 15),
        gross_proceeds=Decimal("2380.00"),
        tax_rate=19,
        counter_account_number="1200",
        voucher_no="V-001",
        description="Verkauf MacBook Pro",
    )

    assert preview.fixed_asset == asset
    assert (
        preview.previous_depreciation
        == Decimal("0.00")
    )
    assert preview.depreciation_proposal == proposal
    assert (
        preview.accumulated_depreciation
        == Decimal("400.00")
    )
    assert (
        preview.disposal_calculation
        is disposal_calculation
    )

    depreciation_service.build_proposal.assert_called_once_with(
        fixed_asset=asset,
        fiscal_year=context.fiscal_year,
        previous_depreciation=Decimal("0.00"),
        expense_account_number="4830",
        asset_account_number="0690",
        depreciation_end_date=date(2026, 8, 15),
    )

    disposal_service.calculate.assert_called_once_with(
        booking_date=date(2026, 8, 15),
        acquisition_cost=Decimal("2400.00"),
        accumulated_depreciation=Decimal("400.00"),
        gross_proceeds=Decimal("2380.00"),
        tax_rate=19,
        asset_account_number="0690",
        counter_account_number="1200",
        control_accounts=control_accounts,
        vat_accounts=vat_accounts,
        voucher_no="V-001",
        description="Verkauf MacBook Pro",
    )

def test_confirmed_depreciation_is_not_proposed_again(
    context: ApplicationContext,
) -> None:
    booking_repository = Mock()
    company_repository = Mock()
    fixed_asset_repository = Mock()
    fixed_asset_movement_repository = Mock()
    depreciation_repository = Mock()
    depreciation_service = Mock()
    depreciation_workflow = Mock()

    company_repository.get_managed_fiscal_years.return_value = (
        ManagedFiscalYear(
            fiscal_year=context.fiscal_year,
            status=FiscalYearStatus.OPEN,
            opening_source=None,
        ),
    )

    asset = FixedAsset(
        company_id=context.company.company_id,
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

    acquisition_movement = FixedAssetMovement(
        fixed_asset_id=asset.fixed_asset_id,
        fiscal_year_end=context.fiscal_year.end_date,
        movement_date=asset.acquisition_date,
        amount=asset.acquisition_cost,
        booking_id=uuid4(),
        movement_type=FixedAssetMovementType.ACQUISITION,
    )

    proposal = DepreciationProposal(
        fixed_asset_id=asset.fixed_asset_id,
        depreciation_date=context.fiscal_year.end_date,
        amount=Decimal("600.00"),
        expense_account_number="4830",
        asset_account_number="0690",
    )

    confirmed = FixedAssetDepreciation(
        fixed_asset_id=asset.fixed_asset_id,
        fiscal_year_end=context.fiscal_year.end_date,
        depreciation_date=context.fiscal_year.end_date,
        amount=Decimal("600.00"),
        booking_id=uuid4(),
        kind=DepreciationKind.LINEAR,
        source=DepreciationSource.CALCULATED,
    )

    fixed_asset_repository.list_for_company.return_value = (
        asset,
    )
    fixed_asset_repository.get.return_value = asset

    fixed_asset_movement_repository.list_for_fixed_asset.return_value = (
        acquisition_movement,
    )

    depreciation_repository.list_for_fixed_asset.side_effect = (
        (),
        (confirmed,),
    )

    depreciation_service.build_proposal.return_value = (
        proposal
    )

    depreciation_workflow.confirm.return_value = (
        confirmed
    )

    booking_repository.list_for_fiscal_year.return_value = ()

    workspace = FiscalYearWorkspace(
        context=context,
        booking_repository=booking_repository,
        company_repository=company_repository,
        posting_service=Mock(),
        closing_workflow=Mock(),
        closing_consistency_service=Mock(),
        e_bilanz_preparation_service=Mock(),
        e_bilanz_service=Mock(),
        e_bilanz_account_detail_service=Mock(),
        e_bilanz_export_service=Mock(),
        taxonomy_management_service=Mock(),
        fixed_asset_repository=(
            fixed_asset_repository
        ),
        fixed_asset_movement_repository=(
            fixed_asset_movement_repository
        ),
        fixed_asset_depreciation_repository=(
            depreciation_repository
        ),
        depreciation_service=(
            depreciation_service
        ),
        fixed_asset_depreciation_workflow=(
            depreciation_workflow
        ),
    )

    first_proposals = (
        workspace.build_depreciation_proposals()
    )

    assert first_proposals == (proposal,)

    result = workspace.confirm_depreciation(
        proposal
    )

    assert result == confirmed

    second_proposals = (
        workspace.build_depreciation_proposals()
    )

    assert second_proposals == ()

    depreciation_workflow.confirm.assert_called_once_with(
        company_id=context.company.company_id,
        fiscal_year=context.fiscal_year,
        proposal=proposal,
        asset_code=asset.asset_code,
        asset_description=asset.description,
    )

def test_close_fiscal_year_uses_workflow_and_reloads_closed_bookings(
    context: ApplicationContext,
) -> None:
    booking_repository = Mock()
    company_repository = Mock()

    posting_service = PostingService()
    closing_workflow = Mock()

    original_booking = Booking(
        booking_date=date(2026, 6, 1),
        voucher_no="R-001",
        description="Erlös",
        lines=(
            BookingLine(
                account_number="1200",
                side=EntrySide.DEBIT,
                amount=Decimal("500.00"),
            ),
            BookingLine(
                account_number="8400",
                side=EntrySide.CREDIT,
                amount=Decimal("500.00"),
            ),
        ),
    )

    closing_booking = Booking(
        booking_date=date(2026, 12, 31),
        voucher_no=None,
        description="Abschluss des Erlöskontos 8400",
        lines=(
            BookingLine(
                account_number="8400",
                side=EntrySide.DEBIT,
                amount=Decimal("500.00"),
            ),
            BookingLine(
                account_number="8990",
                side=EntrySide.CREDIT,
                amount=Decimal("500.00"),
            ),
        ),
        booking_type=BookingType.CLOSING,
    )

    closing_result = ClosingResult(
        net_income=Decimal("500.00"),
        bookings=(closing_booking,),
    )

    closing_workflow.close.return_value = closing_result

    booking_repository.list_for_fiscal_year.side_effect = (
        (original_booking,),
        (
            original_booking,
            closing_booking,
        ),
    )

    workspace = FiscalYearWorkspace(
        context=context,
        booking_repository=booking_repository,
        company_repository=company_repository,
        posting_service=posting_service,
        closing_workflow=closing_workflow,
        closing_consistency_service=Mock(),
        e_bilanz_preparation_service=Mock(),
        e_bilanz_service=Mock(),
        e_bilanz_account_detail_service=Mock(),
        taxonomy_management_service=Mock(),
        e_bilanz_export_service=Mock(),
    )

    income_statement = Mock(
        spec=IncomeStatement
    )
    chart_of_accounts = Mock(
        spec=ChartOfAccountsTemplate
    )

    result = workspace.close_fiscal_year(
        income_statement=income_statement,
        chart_of_accounts=chart_of_accounts,
    )

    assert result is closing_result

    closing_workflow.close.assert_called_once_with(
        company_id=context.company.company_id,
        fiscal_year=context.fiscal_year,
        income_statement=income_statement,
        ledger=ANY,
        chart_of_accounts=chart_of_accounts,
        closing_date=context.fiscal_year.end_date,
    )

    assert len(workspace.journal) == 2
    assert tuple(workspace.journal) == (
        original_booking,
        closing_booking,
    )

    revenue_account = workspace.ledger.get_account(
        "8400"
    )

    assert revenue_account.debit == Decimal("500.00")
    assert revenue_account.credit == Decimal("500.00")

    closing_account = workspace.ledger.get_account(
        "8990"
    )


    assert closing_account.credit == Decimal("500.00")

    pre_closing_revenue_account = (
        workspace.pre_closing_ledger.get_account(
            "8400"
        )
    )

    assert (
        pre_closing_revenue_account.debit
        == Decimal("0.00")
    )
    assert (
        pre_closing_revenue_account.credit
        == Decimal("500.00")
    )

    with pytest.raises(KeyError):
        workspace.pre_closing_ledger.get_account(
            "8990"
        )


def test_validate_closing_delegates_to_consistency_service(
    context: ApplicationContext,
) -> None:
    booking_repository = Mock()
    company_repository = Mock()
    posting_service = PostingService()
    closing_workflow = Mock()
    closing_consistency_service = Mock()

    booking_repository.list_for_fiscal_year.return_value = ()

    expected_result = ClosingConsistencyResult(
        errors=()
    )

    closing_consistency_service.validate.return_value = (
        expected_result
    )

    workspace = FiscalYearWorkspace(
        context=context,
        booking_repository=booking_repository,
        company_repository=company_repository,
        posting_service=posting_service,
        closing_workflow=closing_workflow,
        closing_consistency_service=(
            closing_consistency_service
        ),
        e_bilanz_preparation_service=Mock(),
        e_bilanz_service=Mock(),
        e_bilanz_account_detail_service=Mock(),
        taxonomy_management_service=Mock(),
        e_bilanz_export_service=Mock(),
    )

    balance_sheet = Mock(
        spec=BalanceSheet
    )

    income_statement = Mock(
        spec=IncomeStatement
    )

    closing_result = ClosingResult(
        net_income=Decimal("100.00")
    )

    balances: tuple[AccountBalance, ...] = ()

    mapper = Mock(
        spec=AccountMapper
    )

    result = workspace.validate_closing(
        balance_sheet=balance_sheet,
        income_statement=income_statement,
        closing_result=closing_result,
        balances=balances,
        mapper=mapper,
    )

    assert result is expected_result

    closing_consistency_service.validate.assert_called_once()

    call_kwargs = (
        closing_consistency_service
        .validate
        .call_args
        .kwargs
    )

    assert call_kwargs["balance_sheet"] is balance_sheet
    assert call_kwargs["income_statement"] is income_statement
    assert call_kwargs["closing_result"] is closing_result
    assert call_kwargs["balances"] == balances
    assert call_kwargs["mapper"] is mapper
    assert call_kwargs["trial_balance"].ledger is workspace.ledger

def test_loads_company_master_data(
    context: ApplicationContext,
) -> None:
    """Die Stammdaten des geöffneten Unternehmens werden geladen."""

    booking_repository = Mock()
    company_repository = Mock()
    posting_service = PostingService()
    closing_workflow = Mock()

    booking_repository.list_for_fiscal_year.return_value = ()

    master_data = CompanyMasterData(
        company=context.company,
        legal_form="UG (haftungsbeschränkt)",
        tax_number="1234567890123",
        tax_office="Finanzamt Musterstadt",
        tax_id="12345678901",
        tax_economic_id="DE123456789",
        bf4="1234",
        street="Musterstraße",
        house_number="12a",
        postal_code="12345",
        city="Musterstadt",
        country="DE",
        business="Softwareentwicklung",
    )

    company_repository.get_master_data.return_value = (
        master_data
    )

    workspace = FiscalYearWorkspace(
        context=context,
        booking_repository=booking_repository,
        company_repository=company_repository,
        posting_service=posting_service,
        closing_workflow=closing_workflow,
        closing_consistency_service=Mock(),
        e_bilanz_preparation_service=Mock(),
        e_bilanz_service=Mock(),
        e_bilanz_account_detail_service=Mock(),
        taxonomy_management_service=Mock(),
        e_bilanz_export_service=Mock(),
    )

    result = workspace.load_company_master_data()

    assert result is master_data

    company_repository.get_master_data.assert_called_once_with(
        context.company.company_id
    )


def test_saves_company_master_data(
    context: ApplicationContext,
) -> None:
    """Die Stammdaten des geöffneten Unternehmens werden gespeichert."""

    booking_repository = Mock()
    company_repository = Mock()
    posting_service = PostingService()
    closing_workflow = Mock()

    booking_repository.list_for_fiscal_year.return_value = ()

    master_data = CompanyMasterData(
        company=context.company,
        legal_form="UG (haftungsbeschränkt)",
        tax_number="1234567890123",
        tax_office="Finanzamt Musterstadt",
        tax_id="12345678901",
        tax_economic_id="DE123456789",
        bf4="1234",
        street="Musterstraße",
        house_number="12a",
        postal_code="12345",
        city="Musterstadt",
        country="DE",
        business="Softwareentwicklung",
    )

    workspace = FiscalYearWorkspace(
        context=context,
        booking_repository=booking_repository,
        company_repository=company_repository,
        posting_service=posting_service,
        closing_workflow=closing_workflow,
        closing_consistency_service=Mock(),
        e_bilanz_preparation_service=Mock(),
        e_bilanz_service=Mock(),
        e_bilanz_account_detail_service=Mock(),
        taxonomy_management_service=Mock(),
        e_bilanz_export_service=Mock(),
    )

    workspace.save_company_master_data(
        master_data
    )

    company_repository.save_master_data.assert_called_once_with(
        master_data
    )

def test_prepares_e_bilanz_for_closed_fiscal_year(
    context: ApplicationContext,
) -> None:
    booking_repository = Mock()
    company_repository = Mock()
    posting_service = PostingService()
    closing_workflow = Mock()
    closing_consistency_service = Mock()
    preparation_service = Mock()
    e_bilanz_service = Mock()

    booking_repository.list_for_fiscal_year.return_value = ()

    company_repository.get_managed_fiscal_years.return_value = (
        ManagedFiscalYear(
            fiscal_year=context.fiscal_year,
            status=FiscalYearStatus.CLOSED,
            opening_source=None,
        ),
    )

    expected_result = Mock()

    preparation_service.prepare.return_value = (
        expected_result
    )

    workspace = FiscalYearWorkspace(
        context=context,
        booking_repository=booking_repository,
        company_repository=company_repository,
        posting_service=posting_service,
        closing_workflow=closing_workflow,
        closing_consistency_service=(
            closing_consistency_service
        ),
        e_bilanz_preparation_service=(
            preparation_service
        ),
        e_bilanz_service=e_bilanz_service,
        e_bilanz_account_detail_service=Mock(),
        taxonomy_management_service=Mock(),
        e_bilanz_export_service=Mock(),
    )

    income_statement = Mock(
        spec=IncomeStatement
    )

    result = workspace.prepare_e_bilanz(
        income_statement=income_statement,
    )

    assert result is expected_result

    preparation_service.prepare.assert_called_once_with(
        income_statement=income_statement,
        closed_ledger=workspace.ledger,
    )

def test_rejects_e_bilanz_preparation_for_open_fiscal_year(
    context: ApplicationContext,
) -> None:
    booking_repository = Mock()
    company_repository = Mock()

    booking_repository.list_for_fiscal_year.return_value = ()

    company_repository.get_managed_fiscal_years.return_value = (
        ManagedFiscalYear(
            fiscal_year=context.fiscal_year,
            status=FiscalYearStatus.OPEN,
            opening_source=None,
        ),
    )

    workspace = FiscalYearWorkspace(
        context=context,
        booking_repository=booking_repository,
        company_repository=company_repository,
        posting_service=PostingService(),
        closing_workflow=Mock(),
        closing_consistency_service=Mock(),
        e_bilanz_preparation_service=Mock(),
        e_bilanz_service=Mock(),
        e_bilanz_account_detail_service=Mock(),
        taxonomy_management_service=Mock(),
        e_bilanz_export_service=Mock(),
    )

    with pytest.raises(
        ValueError,
        match=(
            "Die E-Bilanz kann erst nach dem "
            "Jahresabschluss vorbereitet werden."
        ),
    ):
        workspace.prepare_e_bilanz(
            income_statement=Mock(
                spec=IncomeStatement
            ),
        )

def test_builds_e_bilanz_from_prepared_data(
    context: ApplicationContext,
) -> None:
    booking_repository = Mock()
    company_repository = Mock()
    bvv_repository = Mock()
    shareholder_repository = Mock()
    chart_of_accounts_repository = Mock()
    preparation_service = Mock()
    e_bilanz_service = Mock()
    account_detail_service = Mock()

    booking_repository.list_for_fiscal_year.return_value = ()

    bvv_annual_data = BvvAnnualData(
        previous_hgb_equity=Decimal("12345.67"),
        contribution=Decimal("0.00"),
        withdrawal_distribution=Decimal("0.00"),
    )

    bvv_repository.get_for_fiscal_year.return_value = (
        bvv_annual_data
    )

    previous_fiscal_year = FiscalYear(
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
    )

    company_repository.get_managed_fiscal_years.return_value = (
        ManagedFiscalYear(
            fiscal_year=previous_fiscal_year,
            status=FiscalYearStatus.CLOSED,
            opening_source=None,
        ),
        ManagedFiscalYear(
            fiscal_year=context.fiscal_year,
            status=FiscalYearStatus.CLOSED,
            opening_source=None,
        ),
    )

    master_data = CompanyMasterData(
        company=context.company,
        legal_form="UG (haftungsbeschränkt)",
        tax_number="1234567890123",
    )

    company_repository.get_master_data.return_value = (
        master_data
    )

    control_accounts = Mock(
        spec=AccountingControlAccounts
    )

    vat_accounts = Mock(
        spec=VatAccounts
    )

    account_roles = Mock(
        spec=AccountingAccountRoles
    )

    (
        chart_of_accounts_repository
        .load_control_accounts
        .return_value
    ) = control_accounts

    (
        chart_of_accounts_repository
        .load_vat_accounts
        .return_value
    ) = vat_accounts

    (
        chart_of_accounts_repository
        .load_account_roles
        .return_value
    ) = account_roles

    shareholders = (
        Mock(),
        Mock(),
    )

    shareholder_repository.list_for_company.return_value = (
        shareholders
    )

    preparation = Mock()
    preparation.amounts = {
        Mock(): Decimal("100.00"),
    }

    account_taxonomy_concepts = {}
    (
        chart_of_accounts_repository
        .load_account_taxonomy_concepts
        .return_value
    ) = account_taxonomy_concepts

    account_details = Mock()

    account_detail_service.build_for_e_bilanz.return_value = (
        account_details
    )

    expected_document = Mock()

    e_bilanz_service.build.return_value = (
        expected_document
    )

    workspace = FiscalYearWorkspace(
        context=context,
        booking_repository=booking_repository,
        company_repository=company_repository,
        bvv_annual_data_repository=bvv_repository,
        shareholder_repository=shareholder_repository,
        chart_of_accounts_repository=(
            chart_of_accounts_repository
        ),
        posting_service=PostingService(),
        closing_workflow=Mock(),
        closing_consistency_service=Mock(),
        e_bilanz_preparation_service=(
            preparation_service
        ),
        e_bilanz_service=e_bilanz_service,
        e_bilanz_account_detail_service=(
            account_detail_service
        ),
        taxonomy_management_service=Mock(),
        e_bilanz_export_service=Mock(),
    )

    chart_of_accounts = Mock(
        spec=ChartOfAccountsTemplate
    )

    result = workspace.build_e_bilanz(
        preparation=preparation,
        chart_of_accounts=chart_of_accounts,
    )

    assert result is expected_document

    account_detail_service.build_for_e_bilanz.assert_called_once_with(
        pre_closing_ledger=workspace.pre_closing_ledger,
        closed_ledger=workspace.ledger,
    )

    (
        chart_of_accounts_repository
        .load_control_accounts
        .assert_called_once_with(
            context.company.company_id
        )
    )

    (
        chart_of_accounts_repository
        .load_vat_accounts
        .assert_called_once_with(
            context.company.company_id
        )
    )

    (
        chart_of_accounts_repository
        .load_account_roles
        .assert_called_once_with(
            context.company.company_id
        )
    )

    shareholder_repository.list_for_company.assert_called_once_with(
        context.company.company_id
    )

    e_bilanz_service.build.assert_called_once_with(
        master_data=master_data,
        fiscal_year=context.fiscal_year,
        amounts=preparation.amounts,
        income_statement=preparation.income_statement,
        balance_sheet=preparation.balance_sheet,
        vat_accounts=vat_accounts,
        account_roles=account_roles,
        entity_identifier=str(
            context.company.company_id
        ),
        entity_scheme="urn:openbilanz:company-id",
        previous_fiscal_year=previous_fiscal_year,
        account_details=account_details,
        account_taxonomy_concepts=(
            account_taxonomy_concepts
        ),
        fixed_asset_schedule=(),
        fixed_asset_disposal_details=(),
        shareholders=shareholders,
        current_depreciation_difference=Decimal("0.00"),
        previous_depreciation_difference=Decimal("0.00"),
        previous_hgb_equity=Decimal("12345.67"),
        contribution=Decimal("0.00"),
        withdrawal_distribution=Decimal("0.00"),
    )

def test_rejects_e_bilanz_build_for_open_fiscal_year(
    context: ApplicationContext,
) -> None:
    booking_repository = Mock()
    company_repository = Mock()

    booking_repository.list_for_fiscal_year.return_value = ()

    company_repository.get_managed_fiscal_years.return_value = (
        ManagedFiscalYear(
            fiscal_year=context.fiscal_year,
            status=FiscalYearStatus.OPEN,
            opening_source=None,
        ),
    )

    workspace = FiscalYearWorkspace(
        context=context,
        booking_repository=booking_repository,
        company_repository=company_repository,
        posting_service=PostingService(),
        closing_workflow=Mock(),
        closing_consistency_service=Mock(),
        e_bilanz_preparation_service=Mock(),
        e_bilanz_service=Mock(),
        e_bilanz_account_detail_service=Mock(),
        taxonomy_management_service=Mock(),
        e_bilanz_export_service=Mock(),
    )

    chart_of_accounts = Mock(
        spec=ChartOfAccountsTemplate
    )

    with pytest.raises(
        ValueError,
        match=(
            "Die E-Bilanz kann erst nach dem "
            "Jahresabschluss erzeugt werden."
        ),
    ):
        workspace.build_e_bilanz(
            preparation=Mock(),
            chart_of_accounts=chart_of_accounts,
        )

def test_validates_e_bilanz_for_closed_fiscal_year(
    context: ApplicationContext,
) -> None:
    booking_repository = Mock()
    company_repository = Mock()
    posting_service = PostingService()
    closing_workflow = Mock()
    closing_consistency_service = Mock()
    preparation_service = Mock()
    e_bilanz_service = Mock()

    booking_repository.list_for_fiscal_year.return_value = ()

    company_repository.get_managed_fiscal_years.return_value = (
        ManagedFiscalYear(
            fiscal_year=context.fiscal_year,
            status=FiscalYearStatus.CLOSED,
            opening_source=None,
        ),
    )

    expected_result = ArelleValidationResult(
        is_valid=True,
        errors=(),
    )

    e_bilanz_service.validate.return_value = (
        expected_result
    )

    workspace = FiscalYearWorkspace(
        context=context,
        booking_repository=booking_repository,
        company_repository=company_repository,
        posting_service=posting_service,
        closing_workflow=closing_workflow,
        closing_consistency_service=(
            closing_consistency_service
        ),
        e_bilanz_preparation_service=(
            preparation_service
        ),
        e_bilanz_service=e_bilanz_service,
        e_bilanz_account_detail_service=Mock(),
        taxonomy_management_service=Mock(),
        e_bilanz_export_service=Mock(),
    )

    document = Mock(
        spec=EBilanzDocument
    )

    result = workspace.validate_e_bilanz(
        document
    )

    assert result is expected_result

    e_bilanz_service.validate.assert_called_once_with(
        document,
        fiscal_year=context.fiscal_year,
    )

def test_rejects_e_bilanz_validation_for_open_fiscal_year(
    context: ApplicationContext,
) -> None:
    booking_repository = Mock()
    company_repository = Mock()

    booking_repository.list_for_fiscal_year.return_value = ()

    company_repository.get_managed_fiscal_years.return_value = (
        ManagedFiscalYear(
            fiscal_year=context.fiscal_year,
            status=FiscalYearStatus.OPEN,
            opening_source=None,
        ),
    )

    workspace = FiscalYearWorkspace(
        context=context,
        booking_repository=booking_repository,
        company_repository=company_repository,
        posting_service=PostingService(),
        closing_workflow=Mock(),
        closing_consistency_service=Mock(),
        e_bilanz_preparation_service=Mock(),
        e_bilanz_service=Mock(),
        e_bilanz_account_detail_service=Mock(),
        taxonomy_management_service=Mock(),
        e_bilanz_export_service=Mock(),
    )

    document = Mock(
        spec=EBilanzDocument
    )

    with pytest.raises(
        ValueError,
        match=(
            "E-Bilanz kann erst nach dem "
            "Jahresabschluss validiert werden"
        ),
    ):
        workspace.validate_e_bilanz(
            document
        )

def test_installs_required_taxonomy_for_opened_fiscal_year(
    context: ApplicationContext,
) -> None:
    booking_repository = Mock()
    company_repository = Mock()
    taxonomy_management_service = Mock(
        spec=TaxonomyManagementService
    )

    booking_repository.list_for_fiscal_year.return_value = ()

    workspace = FiscalYearWorkspace(
        context=context,
        booking_repository=booking_repository,
        company_repository=company_repository,
        posting_service=Mock(),
        closing_workflow=Mock(),
        closing_consistency_service=Mock(),
        e_bilanz_preparation_service=Mock(),
        e_bilanz_service=Mock(),
        e_bilanz_account_detail_service=Mock(),
        taxonomy_management_service=(
            taxonomy_management_service
        ),
        e_bilanz_export_service=Mock(),
    )

    workspace.install_required_taxonomy()

    taxonomy_management_service.install_required_taxonomy.assert_called_once_with(
        context.fiscal_year
    )

def test_exports_successfully_validated_e_bilanz(
    context: ApplicationContext,
    tmp_path: Path,
) -> None:
    booking_repository = Mock()
    company_repository = Mock()
    e_bilanz_service = Mock()
    export_service = Mock(
        spec=EBilanzExportService
    )

    booking_repository.list_for_fiscal_year.return_value = ()

    company_repository.get_managed_fiscal_years.return_value = (
        ManagedFiscalYear(
            fiscal_year=context.fiscal_year,
            status=FiscalYearStatus.CLOSED,
            opening_source=None,
        ),
    )

    validation_result = ArelleValidationResult(
        is_valid=True,
        errors=(),
    )
    e_bilanz_service.validate.return_value = validation_result

    document = Mock(
        spec=EBilanzDocument
    )
    target = tmp_path / "e-bilanz.xbrl"

    export_service.export.return_value = target

    workspace = FiscalYearWorkspace(
        context=context,
        booking_repository=booking_repository,
        company_repository=company_repository,
        posting_service=PostingService(),
        closing_workflow=Mock(),
        closing_consistency_service=Mock(),
        e_bilanz_preparation_service=Mock(),
        e_bilanz_service=e_bilanz_service,
        e_bilanz_account_detail_service=Mock(),
        e_bilanz_export_service=export_service,
        taxonomy_management_service=Mock(),
    )

    workspace.validate_e_bilanz(
        document
    )

    result = workspace.export_e_bilanz(
        document=document,
        target=target,
    )

    assert result == target

    export_service.export.assert_called_once_with(
        document=document,
        target=target,
    )


def test_rejects_export_of_unvalidated_e_bilanz(
    context: ApplicationContext,
    tmp_path: Path,
) -> None:
    booking_repository = Mock()
    company_repository = Mock()

    booking_repository.list_for_fiscal_year.return_value = ()

    company_repository.get_managed_fiscal_years.return_value = (
        ManagedFiscalYear(
            fiscal_year=context.fiscal_year,
            status=FiscalYearStatus.CLOSED,
            opening_source=None,
        ),
    )

    export_service = Mock(
        spec=EBilanzExportService
    )

    workspace = FiscalYearWorkspace(
        context=context,
        booking_repository=booking_repository,
        company_repository=company_repository,
        posting_service=PostingService(),
        closing_workflow=Mock(),
        closing_consistency_service=Mock(),
        e_bilanz_preparation_service=Mock(),
        e_bilanz_service=Mock(),
        e_bilanz_account_detail_service=Mock(),
        e_bilanz_export_service=export_service,
        taxonomy_management_service=Mock(),
    )

    document = Mock(
        spec=EBilanzDocument
    )

    with pytest.raises(
        ValueError,
        match=(
            "E-Bilanz muss vor dem Export "
            "erfolgreich validiert werden"
        ),
    ):
        workspace.export_e_bilanz(
            document=document,
            target=tmp_path / "e-bilanz.xbrl",
        )

    export_service.export.assert_not_called()

def test_updates_account_via_chart_of_accounts_repository(
    context: ApplicationContext,
) -> None:
    """Kontenänderungen werden an das Kontenrahmen-Repository delegiert."""

    booking_repository = Mock()
    company_repository = Mock()
    chart_of_accounts_repository = Mock()

    booking_repository.list_for_fiscal_year.return_value = ()

    workspace = FiscalYearWorkspace(
        context=context,
        booking_repository=booking_repository,
        company_repository=company_repository,
        chart_of_accounts_repository=(
            chart_of_accounts_repository
        ),
        posting_service=Mock(),
        closing_workflow=Mock(),
        closing_consistency_service=Mock(),
        e_bilanz_preparation_service=Mock(),
        e_bilanz_service=Mock(),
        e_bilanz_account_detail_service=Mock(),
        taxonomy_management_service=Mock(),
        e_bilanz_export_service=Mock(),
    )

    account = Mock()
    mapping_rule = Mock()

    workspace.update_account(
        account=account,
        mapping_rule=mapping_rule,
    )

    chart_of_accounts_repository.update_account.assert_called_once_with(
        company_id=context.company.company_id,
        account=account,
        mapping_rule=mapping_rule,
    )


def test_loads_and_updates_account_configuration(
    context: ApplicationContext,
) -> None:
    """Kontenkonfiguration wird über den Workspace geladen und gespeichert."""

    booking_repository = Mock()
    company_repository = Mock()
    chart_of_accounts_repository = Mock()

    booking_repository.list_for_fiscal_year.return_value = ()

    company_repository.get_managed_fiscal_years.return_value = (
        ManagedFiscalYear(
            fiscal_year=context.fiscal_year,
            status=FiscalYearStatus.OPEN,
            opening_source=None,
        ),
    )

    control_accounts = AccountingControlAccounts(
        opening_balance_account="9000",
        income_summary_account="8990",
        profit_account="8020",
        loss_account="8021",
        profit_loss_carryforward_account="2970",
        depreciation_expense_account="4830",
        fixed_asset_disposal_gain_account="8500",
        fixed_asset_disposal_loss_account="4900",
    )

    vat_accounts = VatAccounts(
        input_tax_7="1571",
        input_tax_19="1576",
        output_tax_7="1771",
        output_tax_19="1776",
    )

    account_roles = AccountingAccountRoles(
        cash_accounts=frozenset({"1000"}),
        bank_accounts=frozenset({"1200"}),
        general_rate_sales_accounts=frozenset({"8400"}),
    )

    chart_of_accounts_repository.load_control_accounts.return_value = (
        control_accounts
    )
    chart_of_accounts_repository.load_vat_accounts.return_value = (
        vat_accounts
    )
    chart_of_accounts_repository.load_account_roles.return_value = (
        account_roles
    )

    workspace = FiscalYearWorkspace(
        context=context,
        booking_repository=booking_repository,
        company_repository=company_repository,
        chart_of_accounts_repository=(
            chart_of_accounts_repository
        ),
        posting_service=Mock(),
        closing_workflow=Mock(),
        closing_consistency_service=Mock(),
        e_bilanz_preparation_service=Mock(),
        e_bilanz_service=Mock(),
        e_bilanz_account_detail_service=Mock(),
        taxonomy_management_service=Mock(),
        e_bilanz_export_service=Mock(),
    )

    loaded = workspace.load_account_configuration()

    assert loaded == (
        control_accounts,
        vat_accounts,
        account_roles,
    )

    workspace.update_account_configuration(
        control_accounts=control_accounts,
        vat_accounts=vat_accounts,
        account_roles=account_roles,
    )

    company_id = context.company.company_id

    chart_of_accounts_repository.load_control_accounts.assert_called_once_with(
        company_id
    )
    chart_of_accounts_repository.load_vat_accounts.assert_called_once_with(
        company_id
    )
    chart_of_accounts_repository.load_account_roles.assert_called_once_with(
        company_id
    )

    chart_of_accounts_repository.save_account_configuration.assert_called_once_with(
        company_id=company_id,
        control_accounts=control_accounts,
        vat_accounts=vat_accounts,
        account_roles=account_roles,
    )


def test_links_fixed_asset_disposal_to_existing_booking(
    context: ApplicationContext,
) -> None:
    booking_repository = Mock()
    company_repository = Mock()
    fixed_asset_repository = Mock()
    movement_repository = Mock()
    depreciation_repository = Mock()

    booking_repository.list_for_fiscal_year.return_value = ()
    depreciation_repository.list_for_fixed_asset.return_value = ()

    company_repository.get_managed_fiscal_years.return_value = (
        ManagedFiscalYear(
            fiscal_year=context.fiscal_year,
            status=FiscalYearStatus.OPEN,
            opening_source=None,
        ),
    )

    fixed_asset = FixedAsset(
        company_id=context.company.company_id,
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

    disposal_booking = Booking(
        booking_date=date(2026, 8, 15),
        description="Abgang Maschine",
        lines=(
            BookingLine(
                account_number="4840",
                side=EntrySide.DEBIT,
                amount=Decimal("11200.00"),
            ),
            BookingLine(
                account_number="0400",
                side=EntrySide.CREDIT,
                amount=Decimal("11200.00"),
            ),
        ),
    )

    acquisition_movement = Mock()
    acquisition_movement.movement_type = (
        FixedAssetMovementType.ACQUISITION
    )

    fixed_asset_repository.get.return_value = fixed_asset
    booking_repository.get.return_value = disposal_booking

    movement_repository.list_for_fixed_asset.return_value = (
        acquisition_movement,
    )

    workspace = FiscalYearWorkspace(
        context=context,
        booking_repository=booking_repository,
        company_repository=company_repository,
        posting_service=Mock(),
        closing_workflow=Mock(),
        closing_consistency_service=Mock(),
        e_bilanz_preparation_service=Mock(),
        e_bilanz_service=Mock(),
        e_bilanz_account_detail_service=Mock(),
        e_bilanz_export_service=Mock(),
        taxonomy_management_service=Mock(),
        fixed_asset_repository=fixed_asset_repository,
        fixed_asset_movement_repository=movement_repository,
        fixed_asset_depreciation_repository=(
            depreciation_repository
        ),
    )

    movement = workspace.link_fixed_asset_disposal(
        fixed_asset_id=fixed_asset.fixed_asset_id,
        booking_id=disposal_booking.booking_id,
        booking_line_position=1,
    )

    assert (
        movement.movement_type
        is FixedAssetMovementType.DISPOSAL
    )
    assert movement.fixed_asset_id == fixed_asset.fixed_asset_id
    assert movement.booking_id == disposal_booking.booking_id
    assert movement.movement_date == date(2026, 8, 15)
    assert movement.amount == Decimal("11200.00")

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

    assert updated_asset.fixed_asset_id == fixed_asset.fixed_asset_id
    assert updated_asset.status is FixedAssetStatus.DISPOSED
    assert updated_asset.disposal_date == date(2026, 8, 15)

@pytest.mark.parametrize(
    (
        "booking_date",
        "booking_account_number",
        "booking_side",
        "existing_movement_types",
        "expected_message",
    ),
    (
        (
            date(2026, 8, 15),
            "0400",
            EntrySide.CREDIT,
            (),
            "Dem Anlagegut ist noch keine "
            "Anschaffungsbuchung zugeordnet.",
        ),
        (
            date(2026, 8, 15),
            "0500",
            EntrySide.CREDIT,
            (FixedAssetMovementType.ACQUISITION,),
            "Die Buchungszeile gehört nicht zum "
            "Anlagenkonto des Anlageguts.",
        ),
        (
            date(2026, 8, 15),
            "0400",
            EntrySide.DEBIT,
            (FixedAssetMovementType.ACQUISITION,),
            "Die Abgangsbuchung muss das Anlagenkonto "
            "im Haben buchen.",
        ),
        (
            date(2025, 12, 31),
            "0400",
            EntrySide.CREDIT,
            (FixedAssetMovementType.ACQUISITION,),
            "Die Buchung gehört nicht zum "
            "geöffneten Geschäftsjahr.",
        ),
        (
            date(2026, 8, 15),
            "0400",
            EntrySide.CREDIT,
            (
                FixedAssetMovementType.ACQUISITION,
                FixedAssetMovementType.DISPOSAL,
            ),
            "Dem Anlagegut ist bereits eine "
            "Abgangsbuchung zugeordnet.",
        ),
    ),
)
def test_rejects_invalid_fixed_asset_disposal_link(
    context: ApplicationContext,
    booking_date: date,
    booking_account_number: str,
    booking_side: EntrySide,
    existing_movement_types: tuple[
        FixedAssetMovementType,
        ...,
    ],
    expected_message: str,
) -> None:
    booking_repository = Mock()
    company_repository = Mock()
    fixed_asset_repository = Mock()
    movement_repository = Mock()

    booking_repository.list_for_fiscal_year.return_value = ()

    company_repository.get_managed_fiscal_years.return_value = (
        ManagedFiscalYear(
            fiscal_year=context.fiscal_year,
            status=FiscalYearStatus.OPEN,
            opening_source=None,
        ),
    )

    fixed_asset = FixedAsset(
        company_id=context.company.company_id,
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

    booking = Booking(
        booking_date=booking_date,
        description="Abgang Maschine",
        lines=(
            BookingLine(
                account_number="4840",
                side=(
                    EntrySide.DEBIT
                    if booking_side is EntrySide.CREDIT
                    else EntrySide.CREDIT
                ),
                amount=Decimal("11200.00"),
            ),
            BookingLine(
                account_number=booking_account_number,
                side=booking_side,
                amount=Decimal("11200.00"),
            ),
        ),
    )

    movements = []

    for movement_type in existing_movement_types:
        movement = Mock()
        movement.movement_type = movement_type
        movements.append(movement)

    fixed_asset_repository.get.return_value = fixed_asset
    booking_repository.get.return_value = booking

    movement_repository.list_for_fixed_asset.return_value = (
        tuple(movements)
    )

    workspace = FiscalYearWorkspace(
        context=context,
        booking_repository=booking_repository,
        company_repository=company_repository,
        posting_service=Mock(),
        closing_workflow=Mock(),
        closing_consistency_service=Mock(),
        e_bilanz_preparation_service=Mock(),
        e_bilanz_service=Mock(),
        e_bilanz_account_detail_service=Mock(),
        e_bilanz_export_service=Mock(),
        taxonomy_management_service=Mock(),
        fixed_asset_repository=fixed_asset_repository,
        fixed_asset_movement_repository=movement_repository,
    )

    with pytest.raises(
        ValueError,
        match=expected_message,
    ):
        workspace.link_fixed_asset_disposal(
            fixed_asset_id=fixed_asset.fixed_asset_id,
            booking_id=booking.booking_id,
            booking_line_position=1,
        )

    movement_repository.add.assert_not_called()
    fixed_asset_repository.update.assert_not_called()

def test_manages_shareholders_independent_of_fiscal_year_status(
    context: ApplicationContext,
) -> None:
    booking_repository = Mock()
    company_repository = Mock()
    shareholder_repository = Mock()

    booking_repository.list_for_fiscal_year.return_value = ()

    company_repository.get_managed_fiscal_years.return_value = (
        ManagedFiscalYear(
            fiscal_year=context.fiscal_year,
            status=FiscalYearStatus.CLOSED,
            opening_source=None,
        ),
    )

    shareholder = Shareholder(
        company_id=context.company.company_id,
        shareholder_number="1",
        name="Muster",
        first_name="Max",
        legal_status="NPP",
        share_numerator="1",
        share_denominator="2",
        tax_number="",
        tax_id="",
        wid="",
    )

    updated_shareholder = Shareholder(
        shareholder_id=shareholder.shareholder_id,
        company_id=context.company.company_id,
        shareholder_number="1",
        name="Muster",
        first_name="Maximilian",
        legal_status="NPP",
        share_numerator="1",
        share_denominator="2",
        tax_number="1234567890123",
        tax_id="",
        wid="",
    )

    shareholder_repository.list_for_company.return_value = (
        shareholder,
    )

    shareholder_repository.get.return_value = (
        updated_shareholder
    )

    workspace = FiscalYearWorkspace(
        context=context,
        booking_repository=booking_repository,
        company_repository=company_repository,
        shareholder_repository=shareholder_repository,
        posting_service=PostingService(),
        closing_workflow=Mock(),
        closing_consistency_service=Mock(),
        e_bilanz_preparation_service=Mock(),
        e_bilanz_service=Mock(),
        e_bilanz_account_detail_service=Mock(),
        taxonomy_management_service=Mock(),
        e_bilanz_export_service=Mock(),
    )

    assert workspace.list_shareholders() == (
        shareholder,
    )

    shareholder_repository.list_for_company.assert_called_once_with(
        context.company.company_id
    )

    workspace.add_shareholder(
        shareholder
    )

    shareholder_repository.add.assert_called_once_with(
        shareholder=shareholder
    )

    workspace.update_shareholder(
        updated_shareholder
    )

    shareholder_repository.update.assert_called_once_with(
        shareholder=updated_shareholder
    )

    workspace.delete_shareholder(
        updated_shareholder.shareholder_id
    )

    shareholder_repository.get.assert_called_once_with(
        updated_shareholder.shareholder_id
    )

    shareholder_repository.delete.assert_called_once_with(
        shareholder_id=(
            updated_shareholder.shareholder_id
        )
    )

def test_gets_tax_depreciation_adjustment(
    context: ApplicationContext,
) -> None:
    booking_repository = Mock()
    adjustment_repository = Mock()

    booking_repository.list_for_fiscal_year.return_value = ()

    depreciation_id = uuid4()

    adjustment = TaxDepreciationAdjustment(
        depreciation_id=depreciation_id,
        commercial_amount=Decimal("600.00"),
        tax_amount=Decimal("620.00"),
    )

    adjustment_repository.get_for_depreciation.return_value = (
        adjustment
    )

    workspace = FiscalYearWorkspace(
        context=context,
        booking_repository=booking_repository,
        company_repository=Mock(),
        posting_service=Mock(),
        closing_workflow=Mock(),
        closing_consistency_service=Mock(),
        e_bilanz_preparation_service=Mock(),
        e_bilanz_service=Mock(),
        e_bilanz_account_detail_service=Mock(),
        e_bilanz_export_service=Mock(),
        taxonomy_management_service=Mock(),
        tax_depreciation_adjustment_repository=(
            adjustment_repository
        ),
    )

    result = workspace.get_tax_depreciation_adjustment(
        depreciation_id
    )

    assert result == adjustment

    adjustment_repository.get_for_depreciation.assert_called_once_with(
        depreciation_id
    )


def test_saves_tax_depreciation_adjustment(
    context: ApplicationContext,
) -> None:
    booking_repository = Mock()
    adjustment_repository = Mock()

    booking_repository.list_for_fiscal_year.return_value = ()

    depreciation_id = uuid4()

    adjustment = TaxDepreciationAdjustment(
        depreciation_id=depreciation_id,
        commercial_amount=Decimal("600.00"),
        tax_amount=Decimal("620.00"),
    )

    adjustment_repository.save.return_value = adjustment

    workspace = FiscalYearWorkspace(
        context=context,
        booking_repository=booking_repository,
        company_repository=Mock(),
        posting_service=Mock(),
        closing_workflow=Mock(),
        closing_consistency_service=Mock(),
        e_bilanz_preparation_service=Mock(),
        e_bilanz_service=Mock(),
        e_bilanz_account_detail_service=Mock(),
        e_bilanz_export_service=Mock(),
        taxonomy_management_service=Mock(),
        tax_depreciation_adjustment_repository=(
            adjustment_repository
        ),
    )

    result = workspace.save_tax_depreciation_adjustment(
        depreciation_id=depreciation_id,
        tax_amount=Decimal("620.00"),
    )

    assert result == adjustment

    adjustment_repository.save.assert_called_once_with(
        depreciation_id=depreciation_id,
        tax_amount=Decimal("620.00"),
    )

def test_uses_explicit_previous_hgb_equity_for_bvv(
    context: ApplicationContext,
) -> None:
    """Explizites BVV-Vorjahreseigenkapital hat Vorrang."""

    booking_repository = Mock()
    company_repository = Mock()
    bvv_repository = Mock()

    booking_repository.list_for_fiscal_year.return_value = ()

    bvv_repository.get_for_fiscal_year.return_value = (
        BvvAnnualData(
            previous_hgb_equity=Decimal("12345.67"),
            contribution=Decimal("0.00"),
            withdrawal_distribution=Decimal("0.00"),
        )
    )

    workspace = FiscalYearWorkspace(
        context=context,
        booking_repository=booking_repository,
        company_repository=company_repository,
        bvv_annual_data_repository=bvv_repository,
        posting_service=Mock(),
        closing_workflow=Mock(),
        closing_consistency_service=Mock(),
        e_bilanz_preparation_service=Mock(),
        e_bilanz_service=Mock(),
        e_bilanz_account_detail_service=Mock(),
        e_bilanz_export_service=Mock(),
        taxonomy_management_service=Mock(),
    )

    chart_of_accounts = Mock(
        spec=ChartOfAccountsTemplate
    )

    result = workspace.effective_previous_hgb_equity(
        chart_of_accounts=chart_of_accounts,
    )

    assert result == Decimal("12345.67")

    bvv_repository.get_for_fiscal_year.assert_called_once_with(
        company_id=context.company.company_id,
        fiscal_year=context.fiscal_year,
    )

    company_repository.get_managed_fiscal_years.assert_not_called()


def test_derives_previous_hgb_equity_from_opening_source_for_bvv(
    context: ApplicationContext,
) -> None:
    """Vorjahreseigenkapital wird bei Saldovortrag aus der Eröffnung abgeleitet."""

    booking_repository = Mock()
    company_repository = Mock()
    bvv_repository = Mock()

    booking_repository.list_for_fiscal_year.return_value = ()

    bvv_repository.get_for_fiscal_year.return_value = (
        BvvAnnualData(
            previous_hgb_equity=None,
            contribution=Decimal("0.00"),
            withdrawal_distribution=Decimal("0.00"),
        )
    )

    previous_fiscal_year = FiscalYear(
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
    )

    company_repository.get_managed_fiscal_years.return_value = (
        ManagedFiscalYear(
            fiscal_year=previous_fiscal_year,
            status=FiscalYearStatus.CLOSED,
            opening_source=None,
        ),
        ManagedFiscalYear(
            fiscal_year=context.fiscal_year,
            status=FiscalYearStatus.OPEN,
            opening_source=previous_fiscal_year,
        ),
    )

    workspace = FiscalYearWorkspace(
        context=context,
        booking_repository=booking_repository,
        company_repository=company_repository,
        bvv_annual_data_repository=bvv_repository,
        posting_service=Mock(),
        closing_workflow=Mock(),
        closing_consistency_service=Mock(),
        e_bilanz_preparation_service=Mock(),
        e_bilanz_service=Mock(),
        e_bilanz_account_detail_service=Mock(),
        e_bilanz_export_service=Mock(),
        taxonomy_management_service=Mock(),
    )

    chart_of_accounts = Mock(
        spec=ChartOfAccountsTemplate
    )

    workspace.opening_hgb_equity = Mock(
        return_value=Decimal("13868.35")
    )

    result = workspace.effective_previous_hgb_equity(
        chart_of_accounts=chart_of_accounts,
    )

    assert result == Decimal("13868.35")

    workspace.opening_hgb_equity.assert_called_once_with(
        chart_of_accounts=chart_of_accounts,
    )


def test_does_not_infer_previous_hgb_equity_without_opening_source(
    context: ApplicationContext,
) -> None:
    """Ohne Vorjahresübernahme wird kein BVV-Vorjahreseigenkapital geraten."""

    booking_repository = Mock()
    company_repository = Mock()
    bvv_repository = Mock()

    booking_repository.list_for_fiscal_year.return_value = ()

    bvv_repository.get_for_fiscal_year.return_value = (
        BvvAnnualData(
            previous_hgb_equity=None,
            contribution=Decimal("10000.00"),
            withdrawal_distribution=Decimal("0.00"),
        )
    )

    company_repository.get_managed_fiscal_years.return_value = (
        ManagedFiscalYear(
            fiscal_year=context.fiscal_year,
            status=FiscalYearStatus.OPEN,
            opening_source=None,
        ),
    )

    workspace = FiscalYearWorkspace(
        context=context,
        booking_repository=booking_repository,
        company_repository=company_repository,
        bvv_annual_data_repository=bvv_repository,
        posting_service=Mock(),
        closing_workflow=Mock(),
        closing_consistency_service=Mock(),
        e_bilanz_preparation_service=Mock(),
        e_bilanz_service=Mock(),
        e_bilanz_account_detail_service=Mock(),
        e_bilanz_export_service=Mock(),
        taxonomy_management_service=Mock(),
    )

    chart_of_accounts = Mock(
        spec=ChartOfAccountsTemplate
    )

    workspace.opening_hgb_equity = Mock()

    result = workspace.effective_previous_hgb_equity(
        chart_of_accounts=chart_of_accounts,
    )

    assert result is None

    workspace.opening_hgb_equity.assert_not_called()


def test_previous_profit_loss_carryforward_uses_account_configuration(
    context: ApplicationContext,
) -> None:
    booking_repository = Mock()
    company_repository = Mock()
    chart_of_accounts_repository = Mock()
    profit_appropriation_service = Mock()

    booking_repository.list_for_fiscal_year.return_value = ()

    control_accounts = Mock(
        spec=AccountingControlAccounts
    )
    control_accounts.opening_balance_account = "9000"
    control_accounts.profit_loss_carryforward_account = "2970"

    vat_accounts = Mock(
        spec=VatAccounts
    )
    account_roles = Mock(
        spec=AccountingAccountRoles
    )

    (
        chart_of_accounts_repository
        .load_control_accounts
        .return_value
    ) = control_accounts
    (
        chart_of_accounts_repository
        .load_vat_accounts
        .return_value
    ) = vat_accounts
    (
        chart_of_accounts_repository
        .load_account_roles
        .return_value
    ) = account_roles

    profit_appropriation_service.previous_profit_loss_carryforward.return_value = (
        Decimal("1234.56")
    )

    workspace = FiscalYearWorkspace(
        context=context,
        booking_repository=booking_repository,
        company_repository=company_repository,
        chart_of_accounts_repository=(
            chart_of_accounts_repository
        ),
        profit_appropriation_service=(
            profit_appropriation_service
        ),
        posting_service=Mock(),
        closing_workflow=Mock(),
        closing_consistency_service=Mock(),
        e_bilanz_preparation_service=Mock(),
        e_bilanz_service=Mock(),
        e_bilanz_account_detail_service=Mock(),
        e_bilanz_export_service=Mock(),
        taxonomy_management_service=Mock(),
    )

    report = Mock()

    workspace.build_trial_balance_report = Mock(
        return_value=report
    )

    result = (
        workspace.previous_profit_loss_carryforward()
    )

    assert result == Decimal("1234.56")

    workspace.build_trial_balance_report.assert_called_once_with(
        start_date=context.fiscal_year.start_date,
        end_date=context.fiscal_year.end_date,
        opening_balance_account_number="9000",
    )

    (
        profit_appropriation_service
        .previous_profit_loss_carryforward
        .assert_called_once_with(
            trial_balance_report=report,
            profit_loss_carryforward_account="2970",
        )
    )


def test_build_e_bilanz_passes_bvv_data_for_hgbm(
    context: ApplicationContext,
) -> None:
    """Reicht bei HGBM die BVV-Jahresdaten an den E-Bilanz-Service weiter."""

    booking_repository = Mock()
    company_repository = Mock()
    chart_of_accounts_repository = Mock()
    preparation_service = Mock()
    e_bilanz_service = Mock()
    account_detail_service = Mock()

    fixed_asset_repository = Mock()
    fixed_asset_depreciation_repository = Mock()
    tax_depreciation_adjustment_repository = Mock()
    fixed_asset_schedule_service = Mock()

    booking_repository.list_for_fiscal_year.return_value = ()

    company_repository.get_managed_fiscal_years.return_value = (
        ManagedFiscalYear(
            fiscal_year=context.fiscal_year,
            status=FiscalYearStatus.CLOSED,
            opening_source=None,
        ),
    )

    master_data = CompanyMasterData(
        company=context.company,
        legal_form="UG (haftungsbeschränkt)",
        tax_number="1234567890123",
    )

    company_repository.get_master_data.return_value = (
        master_data
    )

    control_accounts = Mock(
        spec=AccountingControlAccounts
    )
    vat_accounts = Mock(
        spec=VatAccounts
    )
    account_roles = Mock(
        spec=AccountingAccountRoles
    )

    (
        chart_of_accounts_repository
        .load_control_accounts
        .return_value
    ) = control_accounts

    (
        chart_of_accounts_repository
        .load_vat_accounts
        .return_value
    ) = vat_accounts

    (
        chart_of_accounts_repository
        .load_account_roles
        .return_value
    ) = account_roles

    preparation = Mock()
    preparation.amounts = {}

    account_detail_service.build_for_e_bilanz.return_value = ()

    fixed_asset_schedule = (
        Mock(),
    )

    fixed_asset_schedule_service.build.return_value = (
        fixed_asset_schedule
    )

    expected_document = Mock()

    e_bilanz_service.build.return_value = (
        expected_document
    )

    workspace = FiscalYearWorkspace(
        context=context,
        booking_repository=booking_repository,
        company_repository=company_repository,
        chart_of_accounts_repository=(
            chart_of_accounts_repository
        ),
        posting_service=PostingService(),
        closing_workflow=Mock(),
        closing_consistency_service=Mock(),
        e_bilanz_preparation_service=(
            preparation_service
        ),
        e_bilanz_service=e_bilanz_service,
        e_bilanz_account_detail_service=(
            account_detail_service
        ),
        taxonomy_management_service=Mock(),
        e_bilanz_export_service=Mock(),
        fixed_asset_repository=(
            fixed_asset_repository
        ),
        fixed_asset_depreciation_repository=(
            fixed_asset_depreciation_repository
        ),
        tax_depreciation_adjustment_repository=(
            tax_depreciation_adjustment_repository
        ),
        fixed_asset_schedule_service=(
            fixed_asset_schedule_service
        ),
    )

    chart_of_accounts = Mock(
        spec=ChartOfAccountsTemplate
    )

    bvv_annual_data = BvvAnnualData(
        previous_hgb_equity=Decimal("13868.35"),
        contribution=Decimal("0.00"),
        withdrawal_distribution=Decimal("0.00"),
    )

    with (
        patch.object(
            workspace,
            "tax_depreciation_differences_for_bga",
            return_value=(
                Decimal("-83.33"),
                Decimal("-83.33"),
            ),
        ),
        patch.object(
            workspace,
            "load_bvv_annual_data",
            return_value=bvv_annual_data,
        ) as load_bvv_annual_data,
        patch.object(
            workspace,
            "effective_previous_hgb_equity",
            return_value=Decimal("13868.35"),
        ) as effective_previous_hgb_equity,
    ):
        result = workspace.build_e_bilanz(
            preparation=preparation,
            chart_of_accounts=chart_of_accounts,
        )

    assert result is expected_document

    load_bvv_annual_data.assert_called_once_with()

    effective_previous_hgb_equity.assert_called_once_with(
        chart_of_accounts=chart_of_accounts,
    )

    build_kwargs = (
        e_bilanz_service.build.call_args.kwargs
    )

    assert (
        build_kwargs["current_depreciation_difference"]
        == Decimal("-83.33")
    )

    assert (
        build_kwargs["previous_depreciation_difference"]
        == Decimal("-83.33")
    )

    assert (
        build_kwargs["previous_hgb_equity"]
        == Decimal("13868.35")
    )

    assert (
        build_kwargs["contribution"]
        == Decimal("0.00")
    )

    assert (
        build_kwargs["withdrawal_distribution"]
        == Decimal("0.00")
    )


def test_build_e_bilanz_passes_bvv_data_without_tax_difference(
    context: ApplicationContext,
) -> None:
    """Reicht BVV-Daten auch ohne steuerliche AfA-Differenz weiter."""

    booking_repository = Mock()
    company_repository = Mock()
    chart_of_accounts_repository = Mock()
    preparation_service = Mock()
    e_bilanz_service = Mock()
    account_detail_service = Mock()

    fixed_asset_repository = Mock()
    fixed_asset_depreciation_repository = Mock()
    tax_depreciation_adjustment_repository = Mock()
    fixed_asset_schedule_service = Mock()

    booking_repository.list_for_fiscal_year.return_value = ()

    company_repository.get_managed_fiscal_years.return_value = (
        ManagedFiscalYear(
            fiscal_year=context.fiscal_year,
            status=FiscalYearStatus.CLOSED,
            opening_source=None,
        ),
    )

    master_data = CompanyMasterData(
        company=context.company,
        legal_form="UG (haftungsbeschränkt)",
        tax_number="1234567890123",
    )

    company_repository.get_master_data.return_value = master_data

    control_accounts = Mock(
        spec=AccountingControlAccounts
    )
    vat_accounts = Mock(
        spec=VatAccounts
    )
    account_roles = Mock(
        spec=AccountingAccountRoles
    )

    (
        chart_of_accounts_repository
        .load_control_accounts
        .return_value
    ) = control_accounts

    (
        chart_of_accounts_repository
        .load_vat_accounts
        .return_value
    ) = vat_accounts

    (
        chart_of_accounts_repository
        .load_account_roles
        .return_value
    ) = account_roles

    preparation = Mock()
    preparation.amounts = {}

    account_detail_service.build_for_e_bilanz.return_value = ()

    fixed_asset_schedule_service.build.return_value = ()

    expected_document = Mock()

    e_bilanz_service.build.return_value = expected_document

    workspace = FiscalYearWorkspace(
        context=context,
        booking_repository=booking_repository,
        company_repository=company_repository,
        chart_of_accounts_repository=(
            chart_of_accounts_repository
        ),
        posting_service=PostingService(),
        closing_workflow=Mock(),
        closing_consistency_service=Mock(),
        e_bilanz_preparation_service=(
            preparation_service
        ),
        e_bilanz_service=e_bilanz_service,
        e_bilanz_account_detail_service=(
            account_detail_service
        ),
        taxonomy_management_service=Mock(),
        e_bilanz_export_service=Mock(),
        fixed_asset_repository=(
            fixed_asset_repository
        ),
        fixed_asset_depreciation_repository=(
            fixed_asset_depreciation_repository
        ),
        tax_depreciation_adjustment_repository=(
            tax_depreciation_adjustment_repository
        ),
        fixed_asset_schedule_service=(
            fixed_asset_schedule_service
        ),
    )

    chart_of_accounts = Mock(
        spec=ChartOfAccountsTemplate
    )

    bvv_annual_data = BvvAnnualData(
        previous_hgb_equity=None,
        contribution=Decimal("10000.00"),
        withdrawal_distribution=Decimal("0.00"),
    )

    with (
        patch.object(
            workspace,
            "tax_depreciation_differences_for_bga",
            return_value=(
                Decimal("0.00"),
                Decimal("0.00"),
            ),
        ),
        patch.object(
            workspace,
            "load_bvv_annual_data",
            return_value=bvv_annual_data,
        ) as load_bvv_annual_data,
        patch.object(
            workspace,
            "effective_previous_hgb_equity",
            return_value=None,
        ) as effective_previous_hgb_equity,
    ):
        result = workspace.build_e_bilanz(
            preparation=preparation,
            chart_of_accounts=chart_of_accounts,
        )

    assert result is expected_document

    load_bvv_annual_data.assert_called_once_with()

    effective_previous_hgb_equity.assert_called_once_with(
        chart_of_accounts=chart_of_accounts,
    )

    build_kwargs = (
        e_bilanz_service.build.call_args.kwargs
    )

    assert (
        build_kwargs["current_depreciation_difference"]
        == Decimal("0.00")
    )

    assert (
        build_kwargs["previous_depreciation_difference"]
        == Decimal("0.00")
    )

    assert (
        build_kwargs["previous_hgb_equity"]
        == Decimal("0.00")
    )

    assert (
        build_kwargs["contribution"]
        == Decimal("10000.00")
    )

    assert (
        build_kwargs["withdrawal_distribution"]
        == Decimal("0.00")
    )

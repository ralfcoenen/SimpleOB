"""Tests für den portablen Mandantenexport."""

from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import UUID

from simpleob.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
from simpleob.client_transfer.exporter import (
    ClientTransferExporter,
)
from simpleob.client_transfer.serialization import (
    client_transfer_from_json,
    client_transfer_to_json,
)
from simpleob.domain.account_type import AccountType
from simpleob.domain.depreciation_kind import DepreciationKind
from simpleob.domain.depreciation_source import DepreciationSource
from simpleob.domain.entry_side import EntrySide
from simpleob.domain.fiscal_year import FiscalYear
from simpleob.domain.fiscal_year_status import FiscalYearStatus
from simpleob.domain.fixed_asset_movement_type import (
    FixedAssetMovementType,
)
from simpleob.domain.fixed_asset_status import FixedAssetStatus
from simpleob.domain.managed_fiscal_year import ManagedFiscalYear
from simpleob.domain.profit_appropriation_posting_type import (
    ProfitAppropriationPostingType,
)


COMPANY_ID = UUID(
    "12345678-1234-5678-1234-567812345678"
)
BOOKING_ID = UUID(
    "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
)
SHAREHOLDER_ID = UUID(
    "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
)
FIXED_ASSET_ID = UUID(
    "cccccccc-cccc-cccc-cccc-cccccccccccc"
)
MOVEMENT_ID = UUID(
    "dddddddd-dddd-dddd-dddd-dddddddddddd"
)
DEPRECIATION_ID = UUID(
    "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"
)
POSTING_ID = UUID(
    "ffffffff-ffff-ffff-ffff-ffffffffffff"
)


ACCOUNT_NUMBERS = (
    "0200",
    "0755",
    "0846",
    "0855",
    "1000",
    "1200",
    "1571",
    "1576",
    "1771",
    "1776",
    "2970",
    "4830",
    "4900",
    "8020",
    "8021",
    "8500",
    "9000",
)


def _build_repositories() -> dict[str, Mock]:
    return {
        "company_repository": Mock(),
        "chart_of_accounts_repository": Mock(),
        "booking_repository": Mock(),
        "shareholder_repository": Mock(),
        "fixed_asset_repository": Mock(),
        "fixed_asset_movement_repository": Mock(),
        "fixed_asset_depreciation_repository": Mock(),
        "tax_depreciation_adjustment_repository": Mock(),
        "profit_appropriation_annual_data_repository": Mock(),
        "profit_appropriation_posting_repository": Mock(),
        "equity_contribution_repository": Mock(),
    }


def _configure_master_data(
    company_repository: Mock,
) -> None:
    company_repository.get_master_data.return_value = (
        SimpleNamespace(
            company=SimpleNamespace(
                name="Test UG",
            ),
            legal_form="UG (haftungsbeschränkt)",
            tax_number="123/456/78901",
            tax_office="Testfinanzamt",
            tax_id="",
            tax_economic_id="",
            bf4="",
            street="Teststraße",
            house_number="1",
            postal_code="40210",
            city="Düsseldorf",
            country="Deutschland",
            federal_state="Nordrhein-Westfalen",
            business="Softwareentwicklung",
        )
    )


def _configure_chart_of_accounts(
    chart_of_accounts_repository: Mock,
) -> None:
    debit_position = FinancialStatementPosition(
        code="HGB.266.AKTIVA.B.IV",
        name="Kassenbestand",
    )

    mapping_rule = SimpleNamespace(
        account_number="1000",
        debit_position=debit_position,
        credit_position=None,
    )

    accounts = tuple(
        SimpleNamespace(
            number=account_number,
            name=(
                "Kasse"
                if account_number == "1000"
                else f"Testkonto {account_number}"
            ),
            account_type=AccountType.ASSET,
            is_active=True,
        )
        for account_number in ACCOUNT_NUMBERS
    )

    chart_of_accounts = SimpleNamespace(
        account_mapping_rules=(
            mapping_rule,
        ),
    )

    chart_of_accounts_repository.load_for_company.return_value = (
        chart_of_accounts,
        accounts,
    )

    chart_of_accounts_repository.load_control_accounts.return_value = (
        SimpleNamespace(
            opening_balance_account="9000",
            income_summary_account="8020",
            profit_account="8020",
            loss_account="8021",
            profit_loss_carryforward_account="2970",
            statutory_reserve_account="0846",
            other_revenue_reserves_account="0855",
            distribution_liability_account="0755",
            depreciation_expense_account="4830",
            fixed_asset_disposal_gain_account="4900",
            fixed_asset_disposal_loss_account="8500",
        )
    )

    chart_of_accounts_repository.load_vat_accounts.return_value = (
        SimpleNamespace(
            input_tax_7="1571",
            input_tax_19="1576",
            output_tax_7="1771",
            output_tax_19="1776",
        )
    )

    chart_of_accounts_repository.load_account_roles.return_value = (
        SimpleNamespace(
            cash_accounts=frozenset({"1000"}),
            bank_accounts=frozenset({"1200"}),
            general_rate_sales_accounts=frozenset(),
        )
    )

    chart_of_accounts_repository.load_all_account_taxonomy_concepts.return_value = (
        {
            "6.9": {
                "1000": "bs.ass.currAss.cashEquiv.cash",
            },
            "test-version-2": {
                "1200": "test.bank",
            },
        }
    )


def _build_exporter(
    repositories: dict[str, Mock],
) -> ClientTransferExporter:
    return ClientTransferExporter(
        company_repository=(
            repositories["company_repository"]
        ),
        chart_of_accounts_repository=(
            repositories["chart_of_accounts_repository"]
        ),
        booking_repository=(
            repositories["booking_repository"]
        ),
        shareholder_repository=(
            repositories["shareholder_repository"]
        ),
        fixed_asset_repository=(
            repositories["fixed_asset_repository"]
        ),
        fixed_asset_movement_repository=(
            repositories[
                "fixed_asset_movement_repository"
            ]
        ),
        fixed_asset_depreciation_repository=(
            repositories[
                "fixed_asset_depreciation_repository"
            ]
        ),
        tax_depreciation_adjustment_repository=(
            repositories[
                "tax_depreciation_adjustment_repository"
            ]
        ),
        profit_appropriation_annual_data_repository=(
            repositories[
                "profit_appropriation_annual_data_repository"
            ]
        ),
        profit_appropriation_posting_repository=(
            repositories[
                "profit_appropriation_posting_repository"
            ]
        ),
        equity_contribution_repository=(
            repositories[
                "equity_contribution_repository"
            ]
        ),
    )


def test_exporter_builds_portable_client_transfer() -> None:
    fiscal_year = FiscalYear(
        start_date=date(2025, 7, 1),
        end_date=date(2026, 6, 30),
    )

    repositories = _build_repositories()

    company_repository = repositories[
        "company_repository"
    ]
    chart_of_accounts_repository = repositories[
        "chart_of_accounts_repository"
    ]

    _configure_master_data(
        company_repository
    )
    _configure_chart_of_accounts(
        chart_of_accounts_repository
    )

    company_repository.get_managed_fiscal_years.return_value = (
        ManagedFiscalYear(
            fiscal_year=fiscal_year,
            status=FiscalYearStatus.OPEN,
        ),
    )

    repositories[
        "booking_repository"
    ].list_for_fiscal_year.return_value = ()

    repositories[
        "shareholder_repository"
    ].list_for_company.return_value = ()

    repositories[
        "fixed_asset_repository"
    ].list_for_company.return_value = ()

    repositories[
        "profit_appropriation_annual_data_repository"
    ].get_for_fiscal_year.return_value = None

    repositories[
        "profit_appropriation_posting_repository"
    ].list_with_positions_for_source_fiscal_year.return_value = ()

    repositories[
        "equity_contribution_repository"
    ].list_for_fiscal_year.return_value = ()

    exporter = _build_exporter(
        repositories
    )

    transfer = exporter.export(
        company_id=COMPANY_ID,
        position_provider=Mock(),
    )

    assert transfer.client.company_id == COMPANY_ID
    assert transfer.client.master_data.name == "Test UG"

    assert len(transfer.client.accounts) == len(
        ACCOUNT_NUMBERS
    )

    transfer_account = next(
        account
        for account in transfer.client.accounts
        if account.account_number == "1000"
    )

    assert transfer_account.name == "Kasse"
    assert transfer_account.account_type == "ASSET"
    assert transfer_account.is_active is True
    assert (
        transfer_account.debit_position_code
        == "HGB.266.AKTIVA.B.IV"
    )
    assert transfer_account.credit_position_code is None

    assert len(transfer.client.fiscal_years) == 1

    transfer_fiscal_year = (
        transfer.client.fiscal_years[0]
    )

    assert transfer_fiscal_year.start_date == date(
        2025,
        7,
        1,
    )
    assert transfer_fiscal_year.end_date == date(
        2026,
        6,
        30,
    )
    assert transfer_fiscal_year.status == "OPEN"
    assert transfer_fiscal_year.opening_source is None

    assert transfer.client.account_roles.cash_accounts == (
        "1000",
    )
    assert transfer.client.account_roles.bank_accounts == (
        "1200",
    )

    repositories[
        "booking_repository"
    ].list_for_fiscal_year.assert_called_once_with(
        company_id=COMPANY_ID,
        fiscal_year=fiscal_year,
    )

    repositories[
        "profit_appropriation_posting_repository"
    ].list_with_positions_for_source_fiscal_year.assert_called_once_with(
        company_id=COMPANY_ID,
        source_fiscal_year_end=date(
            2026,
            6,
            30,
        ),
    )


def test_exporter_builds_complete_transfer() -> None:
    fiscal_year = FiscalYear(
        start_date=date(2025, 7, 1),
        end_date=date(2026, 6, 30),
    )

    repositories = _build_repositories()

    company_repository = repositories[
        "company_repository"
    ]
    chart_of_accounts_repository = repositories[
        "chart_of_accounts_repository"
    ]

    _configure_master_data(
        company_repository
    )
    _configure_chart_of_accounts(
        chart_of_accounts_repository
    )

    company_repository.get_managed_fiscal_years.return_value = (
        ManagedFiscalYear(
            fiscal_year=fiscal_year,
            status=FiscalYearStatus.CLOSED,
        ),
    )

    booking = SimpleNamespace(
        booking_id=BOOKING_ID,
        booking_date=date(2026, 6, 30),
        voucher_no="B-001",
        description="Vollständige Testbuchung",
        booking_type=SimpleNamespace(
            value="REGULAR",
        ),
        reversal_of_booking_id=None,
        lines=(
            SimpleNamespace(
                account_number="0200",
                side=EntrySide.DEBIT,
                amount=Decimal("1000.00"),
            ),
            SimpleNamespace(
                account_number="1200",
                side=EntrySide.CREDIT,
                amount=Decimal("1000.00"),
            ),
        ),
    )

    repositories[
        "booking_repository"
    ].list_for_fiscal_year.return_value = (
        booking,
    )

    shareholder = SimpleNamespace(
        shareholder_id=SHAREHOLDER_ID,
        shareholder_number="1",
        name="Mustermann",
        first_name="Max",
        legal_status="NATURAL_PERSON",
        share_numerator="1",
        share_denominator="1",
        tax_number="",
        tax_number_federal_state="",
        tax_id="",
        wid="",
    )

    repositories[
        "shareholder_repository"
    ].list_for_company.return_value = (
        shareholder,
    )

    fixed_asset = SimpleNamespace(
        fixed_asset_id=FIXED_ASSET_ID,
        asset_code="A-001",
        description="Testanlage",
        position_code="BGA",
        asset_account_number="0200",
        depreciation_expense_account_number="4830",
        acquisition_date=date(2025, 7, 1),
        acquisition_cost=Decimal("1000.00"),
        depreciation_start_date=date(2025, 7, 1),
        useful_life_months=60,
        status=FixedAssetStatus.ACTIVE,
        disposal_date=None,
    )

    repositories[
        "fixed_asset_repository"
    ].list_for_company.return_value = (
        fixed_asset,
    )

    movement = SimpleNamespace(
        movement_id=MOVEMENT_ID,
        fixed_asset_id=FIXED_ASSET_ID,
        fiscal_year_end=date(2026, 6, 30),
        movement_date=date(2026, 6, 30),
        amount=Decimal("1000.00"),
        booking_id=BOOKING_ID,
        movement_type=(
            FixedAssetMovementType.ACQUISITION
        ),
        reversed_movement_id=None,
    )

    repositories[
        "fixed_asset_movement_repository"
    ].list_with_positions_for_fixed_asset.return_value = (
        (
            movement,
            0,
        ),
    )

    depreciation = SimpleNamespace(
        depreciation_id=DEPRECIATION_ID,
        fixed_asset_id=FIXED_ASSET_ID,
        fiscal_year_end=date(2026, 6, 30),
        depreciation_date=date(2026, 6, 30),
        amount=Decimal("1000.00"),
        booking_id=BOOKING_ID,
        kind=DepreciationKind.LINEAR,
        source=DepreciationSource.CALCULATED,
    )

    repositories[
        "fixed_asset_depreciation_repository"
    ].list_with_positions_for_fixed_asset.return_value = (
        (
            depreciation,
            0,
        ),
    )

    repositories[
        "tax_depreciation_adjustment_repository"
    ].get_for_depreciation.return_value = (
        SimpleNamespace(
            depreciation_id=DEPRECIATION_ID,
            commercial_amount=Decimal("1000.00"),
            tax_amount=Decimal("900.00"),
        )
    )

    repositories[
        "profit_appropriation_annual_data_repository"
    ].get_for_fiscal_year.return_value = (
        SimpleNamespace(
            statutory_reserve_addition=Decimal("0.00"),
            other_revenue_reserves_addition=Decimal(
                "0.00"
            ),
            statutory_reserve_release=Decimal("0.00"),
            other_revenue_reserves_release=Decimal(
                "0.00"
            ),
            distribution=Decimal("1000.00"),
            profit_loss_carryforward=Decimal("0.00"),
        )
    )

    posting = SimpleNamespace(
        posting_id=POSTING_ID,
        source_fiscal_year_end=date(
            2026,
            6,
            30,
        ),
        posting_date=date(
            2026,
            6,
            30,
        ),
        amount=Decimal("1000.00"),
        booking_id=BOOKING_ID,
        posting_type=(
            ProfitAppropriationPostingType.DISTRIBUTION
        ),
    )

    repositories[
        "profit_appropriation_posting_repository"
    ].list_with_positions_for_source_fiscal_year.return_value = (
        (
            posting,
            0,
        ),
    )

    repositories[
        "equity_contribution_repository"
    ].list_for_fiscal_year.return_value = (
        SimpleNamespace(
            booking_id=BOOKING_ID,
            booking_line_position=0,
        ),
    )

    exporter = _build_exporter(
        repositories
    )

    transfer = exporter.export(
        company_id=COMPANY_ID,
        position_provider=Mock(),
    )

    assert transfer.client.company_id == COMPANY_ID

    assert transfer.client.taxonomy_mappings == (
        transfer.client.taxonomy_mappings
    )
    assert len(
        transfer.client.taxonomy_mappings
    ) == 2

    taxonomy_mappings = {
        (
            mapping.taxonomy_version,
            mapping.account_number,
        ): mapping.concept_name
        for mapping in transfer.client.taxonomy_mappings
    }

    assert taxonomy_mappings[
        (
            "6.9",
            "1000",
        )
    ] == "bs.ass.currAss.cashEquiv.cash"

    assert taxonomy_mappings[
        (
            "test-version-2",
            "1200",
        )
    ] == "test.bank"

    assert len(transfer.client.shareholders) == 1

    exported_shareholder = (
        transfer.client.shareholders[0]
    )

    assert (
        exported_shareholder.shareholder_id
        == SHAREHOLDER_ID
    )
    assert exported_shareholder.name == "Mustermann"

    assert len(transfer.client.fiscal_years) == 1

    exported_fiscal_year = (
        transfer.client.fiscal_years[0]
    )

    assert exported_fiscal_year.start_date == date(
        2025,
        7,
        1,
    )
    assert exported_fiscal_year.end_date == date(
        2026,
        6,
        30,
    )
    assert exported_fiscal_year.status == "CLOSED"

    assert len(exported_fiscal_year.bookings) == 1

    exported_booking = (
        exported_fiscal_year.bookings[0]
    )

    assert exported_booking.booking_id == BOOKING_ID
    assert exported_booking.voucher_no == "B-001"
    assert exported_booking.booking_type == "REGULAR"

    assert tuple(
        line.position
        for line in exported_booking.lines
    ) == (
        0,
        1,
    )

    assert (
        exported_booking.lines[0].account_number
        == "0200"
    )
    assert exported_booking.lines[0].side == "DEBIT"
    assert exported_booking.lines[0].amount == "1000.00"

    assert len(transfer.client.fixed_assets) == 1

    exported_fixed_asset = (
        transfer.client.fixed_assets[0]
    )

    assert (
        exported_fixed_asset.fixed_asset_id
        == FIXED_ASSET_ID
    )
    assert (
        exported_fixed_asset.acquisition_cost
        == "1000.00"
    )
    assert exported_fixed_asset.status == "ACTIVE"

    assert len(exported_fixed_asset.movements) == 1

    exported_movement = (
        exported_fixed_asset.movements[0]
    )

    assert exported_movement.movement_id == MOVEMENT_ID
    assert (
        exported_movement.movement_type
        == "ACQUISITION"
    )
    assert (
        exported_movement.booking_line.booking_id
        == BOOKING_ID
    )
    assert exported_movement.booking_line.position == 0

    assert len(
        exported_fixed_asset.depreciations
    ) == 1

    exported_depreciation = (
        exported_fixed_asset.depreciations[0]
    )

    assert (
        exported_depreciation.depreciation_id
        == DEPRECIATION_ID
    )
    assert exported_depreciation.kind == "LINEAR"
    assert exported_depreciation.source == "CALCULATED"
    assert (
        exported_depreciation.booking_line.position
        == 0
    )
    assert (
        exported_depreciation.tax_adjustment
        is not None
    )
    assert (
        exported_depreciation
        .tax_adjustment.tax_amount
        == "900.00"
    )

    assert len(
        transfer.client
        .profit_appropriation_annual_data
    ) == 1

    annual_data = (
        transfer.client
        .profit_appropriation_annual_data[0]
    )

    assert annual_data.fiscal_year.start_date == date(
        2025,
        7,
        1,
    )
    assert annual_data.fiscal_year.end_date == date(
        2026,
        6,
        30,
    )
    assert annual_data.distribution == "1000.00"

    assert len(
        transfer.client
        .profit_appropriation_postings
    ) == 1

    exported_posting = (
        transfer.client
        .profit_appropriation_postings[0]
    )

    assert exported_posting.posting_id == POSTING_ID

    assert (
        exported_posting.source_fiscal_year.start_date
        == date(
            2025,
            7,
            1,
        )
    )
    assert (
        exported_posting.source_fiscal_year.end_date
        == date(
            2026,
            6,
            30,
        )
    )

    assert (
        exported_posting.posting_type
        == "DISTRIBUTION"
    )
    assert exported_posting.amount == "1000.00"
    assert (
        exported_posting.booking_line.booking_id
        == BOOKING_ID
    )
    assert exported_posting.booking_line.position == 0

    assert len(
        transfer.client.equity_contributions
    ) == 1

    contribution = (
        transfer.client.equity_contributions[0]
    )

    assert (
        contribution.booking_line.booking_id
        == BOOKING_ID
    )
    assert contribution.booking_line.position == 0

    json_text = client_transfer_to_json(
        transfer
    )
    restored = client_transfer_from_json(
        json_text
    )

    assert restored == transfer

"""Tests für dokumentweite Mandantentransfer-Referenzen."""


from dataclasses import replace
from datetime import date, datetime, timezone
from uuid import UUID

import pytest

from simpleob.client_transfer.model import (
    ClientTransfer,
    ClientTransferAccount,
    ClientTransferAccountRoles,
    ClientTransferApplication,
    ClientTransferBooking,
    ClientTransferBookingLine,
    ClientTransferClient,
    ClientTransferEquityContribution,
    ClientTransferFiscalYear,
    ClientTransferFiscalYearReference,
    ClientTransferFormat,
    ClientTransferMasterData,
    ClientTransferBookingLineReference,
    ClientTransferControlAccounts,
    ClientTransferFixedAsset,
    ClientTransferFixedAssetDepreciation,
    ClientTransferFixedAssetMovement,
    ClientTransferProfitAppropriationAnnualData,
    ClientTransferProfitAppropriationPosting,
    ClientTransferTaxonomyMapping,
    ClientTransferVatAccounts,
)
from simpleob.client_transfer.validation import (
    validate_client_transfer_references,
)


COMPANY_ID = UUID(
    "12345678-1234-5678-1234-567812345678"
)
BOOKING_ID = UUID(
    "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
)
MOVEMENT_ID = UUID(
    "cccccccc-cccc-cccc-cccc-cccccccccccc"
)
DEPRECIATION_ID = UUID(
    "dddddddd-dddd-dddd-dddd-dddddddddddd"
)
POSTING_ID = UUID(
    "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"
)

def _build_transfer(
    *,
    account_number: str = "1000",
    opening_source: ClientTransferFiscalYearReference | None = None,
    reversal_of_booking_id: UUID | None = None,
    booking_type: str = "REGULAR",
    equity_contributions: tuple[
        ClientTransferEquityContribution,
        ...,
    ] = (),
) -> ClientTransfer:
    fiscal_year = ClientTransferFiscalYear(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        status="OPEN",
        opening_source=opening_source,
        bookings=(
            ClientTransferBooking(
                booking_id=BOOKING_ID,
                booking_date=date(2026, 6, 1),
                booking_type=booking_type,
                reversal_of_booking_id=(
                    reversal_of_booking_id
                ),
                lines=(
                    ClientTransferBookingLine(
                        position=0,
                        account_number=account_number,
                        side="DEBIT",
                        amount="100.00",
                    ),
                ),
            ),
        ),
    )

    return ClientTransfer(
        format=ClientTransferFormat(),
        application=ClientTransferApplication(
            name="SimpleOB",
            version="0.46.0",
        ),
        exported_at=datetime(
            2026,
            10,
            2,
            20,
            0,
            tzinfo=timezone.utc,
        ),
        client=ClientTransferClient(
            company_id=COMPANY_ID,
            master_data=ClientTransferMasterData(
                name="Test UG",
                legal_form="UG (haftungsbeschränkt)",
            ),
            accounts=(
                ClientTransferAccount(
                    account_number="1000",
                    name="Kasse",
                    account_type="ASSET",
                    is_active=True,
                ),
            ),
            control_accounts=None,
            vat_accounts=None,
            account_roles=ClientTransferAccountRoles(),
            equity_contributions=equity_contributions,
            fiscal_years=(fiscal_year,),
        ),
    )


def test_valid_transfer_references_are_accepted() -> None:
    transfer = _build_transfer()

    validate_client_transfer_references(transfer)


def test_unknown_booking_account_is_rejected() -> None:
    transfer = _build_transfer(
        account_number="9999",
    )

    with pytest.raises(
        ValueError,
        match="booking line references unknown account 9999",
    ):
        validate_client_transfer_references(transfer)


def test_unknown_opening_source_is_rejected() -> None:
    transfer = _build_transfer(
        opening_source=ClientTransferFiscalYearReference(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
        ),
    )

    with pytest.raises(
        ValueError,
        match="opening_source references unknown fiscal year",
    ):
        validate_client_transfer_references(transfer)


def test_unknown_reversal_booking_is_rejected() -> None:
    transfer = _build_transfer(
        booking_type="REVERSAL",
        reversal_of_booking_id=UUID(
            "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
        ),
    )

    with pytest.raises(
        ValueError,
        match="reversal booking references unknown booking",
    ):
        validate_client_transfer_references(transfer)


def test_validator_requires_transfer_object() -> None:
    with pytest.raises(
        TypeError,
        match="transfer must be a ClientTransfer",
    ):
        validate_client_transfer_references(None)  # type: ignore[arg-type]


def test_unknown_equity_contribution_line_is_rejected() -> None:
    contribution = ClientTransferEquityContribution(
        booking_line=ClientTransferBookingLineReference(
            booking_id=BOOKING_ID,
            position=1,
        ),
    )

    transfer = _build_transfer(
        equity_contributions=(contribution,),
    )

    with pytest.raises(
        ValueError,
        match=(
            "equity contribution references unknown "
            "booking line"
        ),
    ):
        validate_client_transfer_references(transfer)


@pytest.mark.parametrize(
    (
        "client_changes",
        "expected_message",
    ),
    (
        (
            {
                "control_accounts": ClientTransferControlAccounts(
                    opening_balance_account="9999",
                    income_summary_account="1000",
                    profit_account="1000",
                    loss_account="1000",
                    profit_loss_carryforward_account="1000",
                    statutory_reserve_account="1000",
                    other_revenue_reserves_account="1000",
                    distribution_liability_account="1000",
                    depreciation_expense_account="1000",
                    fixed_asset_disposal_gain_account="1000",
                    fixed_asset_disposal_loss_account="1000",
                ),
            },
            (
                "control account opening_balance_account "
                "references unknown account 9999"
            ),
        ),
        (
            {
                "vat_accounts": ClientTransferVatAccounts(
                    input_tax_7="9999",
                    input_tax_19="1000",
                    output_tax_7="1000",
                    output_tax_19="1000",
                ),
            },
            (
                "VAT account input_tax_7 references "
                "unknown account 9999"
            ),
        ),
        (
            {
                "account_roles": ClientTransferAccountRoles(
                    cash_accounts=("9999",),
                ),
            },
            "account role references unknown account 9999",
        ),
        (
            {
                "taxonomy_mappings": (
                    ClientTransferTaxonomyMapping(
                        taxonomy_version="6.9",
                        account_number="9999",
                        concept_name="test.concept",
                    ),
                ),
            },
            (
                "taxonomy mapping references unknown "
                "account 9999"
            ),
        ),
    ),
)
def test_unknown_configured_account_is_rejected(
    client_changes: dict[str, object],
    expected_message: str,
) -> None:
    transfer = _build_transfer()

    transfer = replace(
        transfer,
        client=replace(
            transfer.client,
            **client_changes,
        ),
    )

    with pytest.raises(
        ValueError,
        match=expected_message,
    ):
        validate_client_transfer_references(transfer)


@pytest.mark.parametrize(
    (
        "asset_account_number",
        "depreciation_expense_account_number",
        "expected_message",
    ),
    (
        (
            "9999",
            "1000",
            (
                "fixed asset asset account references "
                "unknown account 9999"
            ),
        ),
        (
            "1000",
            "9999",
            (
                "fixed asset depreciation expense account "
                "references unknown account 9999"
            ),
        ),
    ),
)
def test_unknown_fixed_asset_account_is_rejected(
    asset_account_number: str,
    depreciation_expense_account_number: str,
    expected_message: str,
) -> None:
    transfer = _build_transfer()

    fixed_asset = ClientTransferFixedAsset(
        fixed_asset_id=UUID(
            "ffffffff-ffff-ffff-ffff-ffffffffffff"
        ),
        asset_code="A-001",
        description="Testanlage",
        position_code="BGA",
        asset_account_number=asset_account_number,
        depreciation_expense_account_number=(
            depreciation_expense_account_number
        ),
        acquisition_date=date(2026, 1, 1),
        acquisition_cost="100.00",
        depreciation_start_date=date(2026, 1, 1),
        useful_life_months=60,
        status="ACTIVE",
    )

    transfer = replace(
        transfer,
        client=replace(
            transfer.client,
            fixed_assets=(fixed_asset,),
        ),
    )

    with pytest.raises(
        ValueError,
        match=expected_message,
    ):
        validate_client_transfer_references(transfer)


def test_fixed_asset_movement_unknown_year_is_rejected() -> None:
    transfer = _build_transfer()

    movement = ClientTransferFixedAssetMovement(
        movement_id=MOVEMENT_ID,
        fiscal_year_end=date(2025, 12, 31),
        movement_date=date(2026, 6, 1),
        amount="100.00",
        booking_line=ClientTransferBookingLineReference(
            booking_id=BOOKING_ID,
            position=0,
        ),
        movement_type="ACQUISITION",
    )

    fixed_asset = _build_fixed_asset(
        movements=(movement,),
    )

    transfer = replace(
        transfer,
        client=replace(
            transfer.client,
            fixed_assets=(fixed_asset,),
        ),
    )

    with pytest.raises(
        ValueError,
        match=(
            "fixed asset movement references unknown "
            "fiscal year"
        ),
    ):
        validate_client_transfer_references(transfer)


def test_fixed_asset_movement_unknown_line_is_rejected() -> None:
    transfer = _build_transfer()

    movement = ClientTransferFixedAssetMovement(
        movement_id=MOVEMENT_ID,
        fiscal_year_end=date(2026, 12, 31),
        movement_date=date(2026, 6, 1),
        amount="100.00",
        booking_line=ClientTransferBookingLineReference(
            booking_id=BOOKING_ID,
            position=1,
        ),
        movement_type="ACQUISITION",
    )

    fixed_asset = _build_fixed_asset(
        movements=(movement,),
    )

    transfer = replace(
        transfer,
        client=replace(
            transfer.client,
            fixed_assets=(fixed_asset,),
        ),
    )

    with pytest.raises(
        ValueError,
        match=(
            "fixed asset movement references unknown "
            "booking line"
        ),
    ):
        validate_client_transfer_references(transfer)


def test_unknown_reversed_movement_is_rejected() -> None:
    transfer = _build_transfer()

    movement = ClientTransferFixedAssetMovement(
        movement_id=MOVEMENT_ID,
        fiscal_year_end=date(2026, 12, 31),
        movement_date=date(2026, 6, 1),
        amount="100.00",
        booking_line=ClientTransferBookingLineReference(
            booking_id=BOOKING_ID,
            position=0,
        ),
        movement_type="REVERSAL",
        reversed_movement_id=UUID(
            "11111111-1111-1111-1111-111111111111"
        ),
    )

    fixed_asset = _build_fixed_asset(
        movements=(movement,),
    )

    transfer = replace(
        transfer,
        client=replace(
            transfer.client,
            fixed_assets=(fixed_asset,),
        ),
    )

    with pytest.raises(
        ValueError,
        match=(
            "fixed asset reversal movement references "
            "unknown movement"
        ),
    ):
        validate_client_transfer_references(transfer)


def test_fixed_asset_depreciation_unknown_line_is_rejected() -> None:
    transfer = _build_transfer()

    depreciation = ClientTransferFixedAssetDepreciation(
        depreciation_id=DEPRECIATION_ID,
        fiscal_year_end=date(2026, 12, 31),
        depreciation_date=date(2026, 6, 1),
        amount="100.00",
        booking_line=ClientTransferBookingLineReference(
            booking_id=BOOKING_ID,
            position=1,
        ),
        kind="LINEAR",
        source="CALCULATED",
    )

    fixed_asset = _build_fixed_asset(
        depreciations=(depreciation,),
    )

    transfer = replace(
        transfer,
        client=replace(
            transfer.client,
            fixed_assets=(fixed_asset,),
        ),
    )

    with pytest.raises(
        ValueError,
        match=(
            "fixed asset depreciation references unknown "
            "booking line"
        ),
    ):
        validate_client_transfer_references(transfer)


def test_profit_appropriation_annual_unknown_year_is_rejected() -> None:
    transfer = _build_transfer()

    annual_data = ClientTransferProfitAppropriationAnnualData(
        fiscal_year=ClientTransferFiscalYearReference(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
        ),
        statutory_reserve_addition="0.00",
        other_revenue_reserves_addition="0.00",
        statutory_reserve_release="0.00",
        other_revenue_reserves_release="0.00",
        distribution="0.00",
        profit_loss_carryforward="100.00",
    )

    transfer = replace(
        transfer,
        client=replace(
            transfer.client,
            profit_appropriation_annual_data=(annual_data,),
        ),
    )

    with pytest.raises(
        ValueError,
        match=(
            "profit appropriation annual data references "
            "unknown fiscal year"
        ),
    ):
        validate_client_transfer_references(transfer)


def test_profit_appropriation_posting_unknown_line_is_rejected() -> None:
    transfer = _build_transfer()

    posting = ClientTransferProfitAppropriationPosting(
        posting_id=POSTING_ID,
        source_fiscal_year=ClientTransferFiscalYearReference(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        ),
        posting_date=date(2026, 6, 1),
        amount="100.00",
        booking_line=ClientTransferBookingLineReference(
            booking_id=BOOKING_ID,
            position=1,
        ),
        posting_type="DISTRIBUTION",
    )

    transfer = replace(
        transfer,
        client=replace(
            transfer.client,
            profit_appropriation_postings=(posting,),
        ),
    )

    with pytest.raises(
        ValueError,
        match=(
            "profit appropriation posting references "
            "unknown booking line"
        ),
    ):
        validate_client_transfer_references(transfer)


def _build_fixed_asset(
    *,
    movements: tuple[
        ClientTransferFixedAssetMovement,
        ...,
    ] = (),
    depreciations: tuple[
        ClientTransferFixedAssetDepreciation,
        ...,
    ] = (),
) -> ClientTransferFixedAsset:
    return ClientTransferFixedAsset(
        fixed_asset_id=UUID(
            "ffffffff-ffff-ffff-ffff-ffffffffffff"
        ),
        asset_code="A-001",
        description="Testanlage",
        position_code="BGA",
        asset_account_number="1000",
        depreciation_expense_account_number="1000",
        acquisition_date=date(2026, 1, 1),
        acquisition_cost="100.00",
        depreciation_start_date=date(2026, 1, 1),
        useful_life_months=60,
        status="ACTIVE",
        movements=movements,
        depreciations=depreciations,
    )


def test_reversal_must_reference_regular_booking() -> None:
    transfer = _build_transfer()

    original = replace(
        transfer.client.fiscal_years[0].bookings[0],
        booking_type="CLOSING",
    )
    reversal = ClientTransferBooking(
        booking_id=UUID(
            "22222222-2222-2222-2222-222222222222"
        ),
        booking_date=date(2026, 6, 2),
        booking_type="REVERSAL",
        reversal_of_booking_id=BOOKING_ID,
        lines=(
            ClientTransferBookingLine(
                position=0,
                account_number="1000",
                side="CREDIT",
                amount="100.00",
            ),
        ),
    )

    fiscal_year = replace(
        transfer.client.fiscal_years[0],
        bookings=(original, reversal),
    )
    transfer = replace(
        transfer,
        client=replace(
            transfer.client,
            fiscal_years=(fiscal_year,),
        ),
    )

    with pytest.raises(
        ValueError,
        match=(
            "reversal booking must reference "
            "a REGULAR booking"
        ),
    ):
        validate_client_transfer_references(transfer)


def test_reversal_and_original_must_share_fiscal_year() -> None:
    transfer = _build_transfer()

    original_year = ClientTransferFiscalYear(
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
        status="CLOSED",
        opening_source=None,
        bookings=(
                ClientTransferBooking(
                    booking_id=BOOKING_ID,
                    booking_date=date(2025, 6, 1),
                    booking_type="REGULAR",
                    lines=(
                        ClientTransferBookingLine(
                            position=0,
                            account_number="1000",
                            side="DEBIT",
                            amount="100.00",
                        ),
                    ),
                ),
            ),
        )

    reversal_year = ClientTransferFiscalYear(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        status="OPEN",
        opening_source=None,
        bookings=(
            ClientTransferBooking(
                booking_id=UUID(
                    "22222222-2222-2222-2222-222222222222"
                ),
                booking_date=date(2026, 1, 2),
                booking_type="REVERSAL",
                reversal_of_booking_id=BOOKING_ID,
                lines=(
                    ClientTransferBookingLine(
                        position=0,
                        account_number="1000",
                        side="CREDIT",
                        amount="100.00",
                    ),
                ),
            ),
        ),
    )

    transfer = replace(
        transfer,
        client=replace(
            transfer.client,
            fiscal_years=(
                original_year,
                reversal_year,
            ),
        ),
    )

    with pytest.raises(
        ValueError,
        match=(
            "reversal booking and original booking "
            "must belong to the same fiscal year"
        ),
    ):
        validate_client_transfer_references(transfer)


def test_booking_must_not_be_reversed_twice() -> None:
    transfer = _build_transfer()

    original = transfer.client.fiscal_years[0].bookings[0]

    reversal_1 = ClientTransferBooking(
        booking_id=UUID(
            "22222222-2222-2222-2222-222222222222"
        ),
        booking_date=date(2026, 6, 2),
        booking_type="REVERSAL",
        reversal_of_booking_id=BOOKING_ID,
        lines=(
            ClientTransferBookingLine(
                position=0,
                account_number="1000",
                side="CREDIT",
                amount="100.00",
            ),
        ),
    )
    reversal_2 = ClientTransferBooking(
        booking_id=UUID(
            "33333333-3333-3333-3333-333333333333"
        ),
        booking_date=date(2026, 6, 3),
        booking_type="REVERSAL",
        reversal_of_booking_id=BOOKING_ID,
        lines=(
            ClientTransferBookingLine(
                position=0,
                account_number="1000",
                side="CREDIT",
                amount="100.00",
            ),
        ),
    )

    fiscal_year = replace(
        transfer.client.fiscal_years[0],
        bookings=(
            original,
            reversal_1,
            reversal_2,
        ),
    )
    transfer = replace(
        transfer,
        client=replace(
            transfer.client,
            fiscal_years=(fiscal_year,),
        ),
    )

    with pytest.raises(
        ValueError,
        match="booking must not be reversed more than once",
    ):
        validate_client_transfer_references(transfer)


def test_invalid_booking_line_decimal_is_rejected() -> None:
    transfer = _build_transfer()

    booking = transfer.client.fiscal_years[0].bookings[0]
    invalid_line = replace(
        booking.lines[0],
        amount="kein Betrag",
    )
    booking = replace(
        booking,
        lines=(invalid_line,),
    )
    fiscal_year = replace(
        transfer.client.fiscal_years[0],
        bookings=(booking,),
    )
    transfer = replace(
        transfer,
        client=replace(
            transfer.client,
            fiscal_years=(fiscal_year,),
        ),
    )

    with pytest.raises(
        ValueError,
        match="booking line amount must be a valid decimal",
    ):
        validate_client_transfer_references(transfer)


def test_fixed_asset_movement_and_booking_must_share_year() -> None:
    transfer = _build_transfer()

    previous_year = ClientTransferFiscalYear(
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
        status="CLOSED",
        opening_source=None,
    )

    movement = ClientTransferFixedAssetMovement(
        movement_id=MOVEMENT_ID,
        fiscal_year_end=date(2025, 12, 31),
        movement_date=date(2025, 12, 31),
        amount="100.00",
        booking_line=ClientTransferBookingLineReference(
            booking_id=BOOKING_ID,
            position=0,
        ),
        movement_type="ACQUISITION",
    )

    transfer = replace(
        transfer,
        client=replace(
            transfer.client,
            fiscal_years=(
                previous_year,
                transfer.client.fiscal_years[0],
            ),
            fixed_assets=(
                _build_fixed_asset(
                    movements=(movement,),
                ),
            ),
        ),
    )

    with pytest.raises(
        ValueError,
        match=(
            "fixed asset movement and booking "
            "must belong to the same fiscal year"
        ),
    ):
        validate_client_transfer_references(transfer)


def test_fixed_asset_movement_amount_must_match_line() -> None:
    transfer = _build_transfer()

    movement = ClientTransferFixedAssetMovement(
        movement_id=MOVEMENT_ID,
        fiscal_year_end=date(2026, 12, 31),
        movement_date=date(2026, 6, 1),
        amount="99.00",
        booking_line=ClientTransferBookingLineReference(
            booking_id=BOOKING_ID,
            position=0,
        ),
        movement_type="ACQUISITION",
    )

    transfer = replace(
        transfer,
        client=replace(
            transfer.client,
            fixed_assets=(
                _build_fixed_asset(
                    movements=(movement,),
                ),
            ),
        ),
    )

    with pytest.raises(
        ValueError,
        match=(
            "booking line amount does not match "
            "fixed asset movement amount"
        ),
    ):
        validate_client_transfer_references(transfer)


def test_fixed_asset_disposal_amount_may_differ_from_line() -> None:
    transfer = _build_transfer()

    movement = ClientTransferFixedAssetMovement(
        movement_id=MOVEMENT_ID,
        fiscal_year_end=date(2026, 12, 31),
        movement_date=date(2026, 6, 1),
        amount="75.00",
        booking_line=ClientTransferBookingLineReference(
            booking_id=BOOKING_ID,
            position=0,
        ),
        movement_type="DISPOSAL",
    )

    transfer = replace(
        transfer,
        client=replace(
            transfer.client,
            fixed_assets=(
                _build_fixed_asset(
                    movements=(movement,),
                ),
            ),
        ),
    )

    validate_client_transfer_references(transfer)


def test_fixed_asset_depreciation_amount_must_match_line() -> None:
    transfer = _build_transfer()

    depreciation = ClientTransferFixedAssetDepreciation(
        depreciation_id=DEPRECIATION_ID,
        fiscal_year_end=date(2026, 12, 31),
        depreciation_date=date(2026, 6, 1),
        amount="99.00",
        booking_line=ClientTransferBookingLineReference(
            booking_id=BOOKING_ID,
            position=0,
        ),
        kind="LINEAR",
        source="CALCULATED",
    )

    transfer = replace(
        transfer,
        client=replace(
            transfer.client,
            fixed_assets=(
                _build_fixed_asset(
                    depreciations=(depreciation,),
                ),
            ),
        ),
    )

    with pytest.raises(
        ValueError,
        match=(
            "booking line amount does not match "
            "fixed asset depreciation amount"
        ),
    ):
        validate_client_transfer_references(transfer)


def test_profit_appropriation_posting_must_match_booking() -> None:
    transfer = _build_transfer()

    posting = ClientTransferProfitAppropriationPosting(
        posting_id=POSTING_ID,
        source_fiscal_year=ClientTransferFiscalYearReference(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        ),
        posting_date=date(2026, 6, 2),
        amount="100.00",
        booking_line=ClientTransferBookingLineReference(
            booking_id=BOOKING_ID,
            position=0,
        ),
        posting_type="DISTRIBUTION",
    )

    transfer = replace(
        transfer,
        client=replace(
            transfer.client,
            profit_appropriation_postings=(posting,),
        ),
    )

    with pytest.raises(
        ValueError,
        match=(
            "profit appropriation posting date does "
            "not match booking date"
        ),
    ):
        validate_client_transfer_references(transfer)


def test_fixed_asset_movement_line_must_be_unique() -> None:
    transfer = _build_transfer()

    movement_1 = ClientTransferFixedAssetMovement(
        movement_id=MOVEMENT_ID,
        fiscal_year_end=date(2026, 12, 31),
        movement_date=date(2026, 6, 1),
        amount="100.00",
        booking_line=ClientTransferBookingLineReference(
            booking_id=BOOKING_ID,
            position=0,
        ),
        movement_type="ACQUISITION",
    )
    movement_2 = ClientTransferFixedAssetMovement(
        movement_id=UUID(
            "44444444-4444-4444-4444-444444444444"
        ),
        fiscal_year_end=date(2026, 12, 31),
        movement_date=date(2026, 6, 1),
        amount="100.00",
        booking_line=ClientTransferBookingLineReference(
            booking_id=BOOKING_ID,
            position=0,
        ),
        movement_type="ACQUISITION",
    )

    transfer = replace(
        transfer,
        client=replace(
            transfer.client,
            fixed_assets=(
                _build_fixed_asset(
                    movements=(
                        movement_1,
                        movement_2,
                    ),
                ),
            ),
        ),
    )

    with pytest.raises(
        ValueError,
        match=(
            "booking line must not be assigned "
            "to more than one fixed asset movement"
        ),
    ):
        validate_client_transfer_references(transfer)


def test_fixed_asset_depreciation_line_must_be_unique() -> None:
    transfer = _build_transfer()

    depreciation_1 = ClientTransferFixedAssetDepreciation(
        depreciation_id=DEPRECIATION_ID,
        fiscal_year_end=date(2026, 12, 31),
        depreciation_date=date(2026, 6, 1),
        amount="100.00",
        booking_line=ClientTransferBookingLineReference(
            booking_id=BOOKING_ID,
            position=0,
        ),
        kind="LINEAR",
        source="CALCULATED",
    )
    depreciation_2 = ClientTransferFixedAssetDepreciation(
        depreciation_id=UUID(
            "55555555-5555-5555-5555-555555555555"
        ),
        fiscal_year_end=date(2026, 12, 31),
        depreciation_date=date(2026, 6, 1),
        amount="100.00",
        booking_line=ClientTransferBookingLineReference(
            booking_id=BOOKING_ID,
            position=0,
        ),
        kind="LINEAR",
        source="CALCULATED",
    )

    transfer = replace(
        transfer,
        client=replace(
            transfer.client,
            fixed_assets=(
                _build_fixed_asset(
                    depreciations=(
                        depreciation_1,
                        depreciation_2,
                    ),
                ),
            ),
        ),
    )

    with pytest.raises(
        ValueError,
        match=(
            "booking line must not be assigned "
            "to more than one fixed asset depreciation"
        ),
    ):
        validate_client_transfer_references(transfer)


def test_profit_appropriation_posting_amount_must_match_line() -> None:
    transfer = _build_transfer()

    posting = ClientTransferProfitAppropriationPosting(
        posting_id=POSTING_ID,
        source_fiscal_year=ClientTransferFiscalYearReference(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        ),
        posting_date=date(2026, 6, 1),
        amount="99.00",
        booking_line=ClientTransferBookingLineReference(
            booking_id=BOOKING_ID,
            position=0,
        ),
        posting_type="DISTRIBUTION",
    )

    transfer = replace(
        transfer,
        client=replace(
            transfer.client,
            profit_appropriation_postings=(posting,),
        ),
    )

    with pytest.raises(
        ValueError,
        match=(
            "booking line amount does not match "
            "profit appropriation posting amount"
        ),
    ):
        validate_client_transfer_references(transfer)


def test_profit_appropriation_posting_line_must_be_unique() -> None:
    transfer = _build_transfer()

    posting_1 = ClientTransferProfitAppropriationPosting(
        posting_id=POSTING_ID,
        source_fiscal_year=ClientTransferFiscalYearReference(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        ),
        posting_date=date(2026, 6, 1),
        amount="100.00",
        booking_line=ClientTransferBookingLineReference(
            booking_id=BOOKING_ID,
            position=0,
        ),
        posting_type="DISTRIBUTION",
    )
    posting_2 = ClientTransferProfitAppropriationPosting(
        posting_id=UUID(
            "66666666-6666-6666-6666-666666666666"
        ),
        source_fiscal_year=ClientTransferFiscalYearReference(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        ),
        posting_date=date(2026, 6, 1),
        amount="100.00",
        booking_line=ClientTransferBookingLineReference(
            booking_id=BOOKING_ID,
            position=0,
        ),
        posting_type="DISTRIBUTION",
    )

    transfer = replace(
        transfer,
        client=replace(
            transfer.client,
            profit_appropriation_postings=(
                posting_1,
                posting_2,
            ),
        ),
    )

    with pytest.raises(
        ValueError,
        match=(
            "booking line must not be assigned to "
            "more than one profit appropriation posting"
        ),
    ):
        validate_client_transfer_references(transfer)

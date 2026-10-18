"""Tests für das Modell des portablen Mandantentransfers."""

from datetime import date, datetime, timezone
from uuid import UUID

import pytest

from simpleob.client_transfer.model import (
    CLIENT_TRANSFER_FORMAT_NAME,
    CLIENT_TRANSFER_FORMAT_VERSION,
    ClientTransfer,
    ClientTransferAccount,
    ClientTransferAccountRoles,
    ClientTransferApplication,
    ClientTransferClient,
    ClientTransferControlAccounts,
    ClientTransferFormat,
    ClientTransferMasterData,
    ClientTransferTaxonomyMapping,
    ClientTransferVatAccounts,
    ClientTransferBooking,
    ClientTransferBookingLine,
    ClientTransferFiscalYear,
    ClientTransferFiscalYearReference,
    ClientTransferBookingLineReference,
    ClientTransferFixedAsset,
    ClientTransferFixedAssetDepreciation,
    ClientTransferFixedAssetMovement,
    ClientTransferShareholder,
    ClientTransferTaxDepreciationAdjustment,
    ClientTransferEquityContribution,
    ClientTransferProfitAppropriationAnnualData,
    ClientTransferProfitAppropriationPosting,
)


COMPANY_ID = UUID(
    "12345678-1234-5678-1234-567812345678"
)


def _build_client() -> ClientTransferClient:
    return ClientTransferClient(
        company_id=COMPANY_ID,
        master_data=ClientTransferMasterData(
            name="Test UG",
            legal_form="UG (haftungsbeschränkt)",
            tax_number="1234567890123",
            tax_office="Testfinanzamt",
            street="Teststraße",
            house_number="1",
            postal_code="12345",
            city="Teststadt",
            country="DE",
            federal_state="NW",
            business="Softwareentwicklung",
        ),
        accounts=(
            ClientTransferAccount(
                account_number="1000",
                name="Kasse",
                account_type="ASSET",
                is_active=True,
                debit_position_code=(
                    "HGB.266.AKTIVA.B.IV"
                ),
                credit_position_code=(
                    "HGB.266.PASSIVA.C"
                ),
            ),
            ClientTransferAccount(
                account_number="1200",
                name="Bank",
                account_type="ASSET",
                is_active=True,
            ),
        ),
        control_accounts=ClientTransferControlAccounts(
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
        ),
        vat_accounts=ClientTransferVatAccounts(
            input_tax_7="1571",
            input_tax_19="1576",
            output_tax_7="1771",
            output_tax_19="1776",
        ),
        account_roles=ClientTransferAccountRoles(
            cash_accounts=("1000",),
            bank_accounts=("1200",),
        ),
        taxonomy_mappings=(
            ClientTransferTaxonomyMapping(
                taxonomy_version="6.9",
                account_number="1200",
                concept_name=(
                    "bs.ass.currAss.cashEquiv.bank"
                ),
            ),
        ),
    )


def test_client_transfer_format_has_current_version() -> None:
    transfer_format = ClientTransferFormat()

    assert (
        transfer_format.name
        == CLIENT_TRANSFER_FORMAT_NAME
    )
    assert (
        transfer_format.version
        == CLIENT_TRANSFER_FORMAT_VERSION
    )


def test_client_transfer_format_rejects_unknown_name() -> None:
    with pytest.raises(
        ValueError,
        match="Unbekanntes Mandantentransferformat",
    ):
        ClientTransferFormat(
            name="Unknown Format"
        )


def test_client_transfer_format_rejects_unknown_version() -> None:
    with pytest.raises(
        ValueError,
        match="Nicht unterstützte Version",
    ):
        ClientTransferFormat(
            version=2
        )


def test_client_transfer_application_normalizes_text() -> None:
    application = ClientTransferApplication(
        name=" SimpleOB ",
        version=" 0.46.0 ",
    )

    assert application.name == "SimpleOB"
    assert application.version == "0.46.0"


def test_client_transfer_account_normalizes_values() -> None:
    account = ClientTransferAccount(
        account_number=" 1000 ",
        name=" Kasse ",
        account_type=" ASSET ",
        is_active=True,
        debit_position_code=" HGB.266.AKTIVA.B.IV ",
    )

    assert account.account_number == "1000"
    assert account.name == "Kasse"
    assert account.account_type == "ASSET"
    assert (
        account.debit_position_code
        == "HGB.266.AKTIVA.B.IV"
    )
    assert account.credit_position_code is None


def test_account_roles_reject_overlap() -> None:
    with pytest.raises(
        ValueError,
        match="mehreren fachlichen Rollen",
    ):
        ClientTransferAccountRoles(
            cash_accounts=("1000",),
            bank_accounts=("1000",),
        )


def test_client_rejects_duplicate_accounts() -> None:
    account = ClientTransferAccount(
        account_number="1000",
        name="Kasse",
        account_type="ASSET",
        is_active=True,
    )

    with pytest.raises(
        ValueError,
        match="duplicate account numbers",
    ):
        ClientTransferClient(
            company_id=COMPANY_ID,
            master_data=ClientTransferMasterData(
                name="Test UG"
            ),
            accounts=(account, account),
            control_accounts=None,
            vat_accounts=None,
            account_roles=ClientTransferAccountRoles(),
        )


def test_taxonomy_mapping_preserves_version() -> None:
    mapping = ClientTransferTaxonomyMapping(
        taxonomy_version=" 6.9 ",
        account_number=" 1200 ",
        concept_name=" bs.ass.currAss.cashEquiv.bank ",
    )

    assert mapping.taxonomy_version == "6.9"
    assert mapping.account_number == "1200"
    assert (
        mapping.concept_name
        == "bs.ass.currAss.cashEquiv.bank"
    )


def test_client_transfer_requires_timezone() -> None:
    with pytest.raises(
        ValueError,
        match="timezone",
    ):
        ClientTransfer(
            format=ClientTransferFormat(),
            application=ClientTransferApplication(
                name="SimpleOB",
                version="0.46.0",
            ),
            exported_at=datetime(
                2026,
                10,
                2,
                15,
                30,
            ),
            client=_build_client(),
        )


def test_client_transfer_accepts_valid_account_data() -> None:
    exported_at = datetime(
        2026,
        10,
        2,
        15,
        30,
        tzinfo=timezone.utc,
    )

    transfer = ClientTransfer(
        format=ClientTransferFormat(),
        application=ClientTransferApplication(
            name="SimpleOB",
            version="0.46.0",
        ),
        exported_at=exported_at,
        client=_build_client(),
    )

    assert transfer.client.company_id == COMPANY_ID
    assert transfer.exported_at == exported_at
    assert len(transfer.client.accounts) == 2
    assert (
        transfer.client.account_roles.cash_accounts
        == ("1000",)
    )
    assert (
        transfer.client.taxonomy_mappings[0]
        .taxonomy_version
        == "6.9"
    )

def test_booking_line_preserves_portable_position() -> None:
    line = ClientTransferBookingLine(
        position=0,
        account_number=" 1000 ",
        side="DEBIT",
        amount="1234.56",
    )

    assert line.position == 0
    assert line.account_number == "1000"
    assert line.side == "DEBIT"
    assert line.amount == "1234.56"


def test_booking_requires_continuous_line_positions() -> None:
    with pytest.raises(
        ValueError,
        match="continuous and start at zero",
    ):
        ClientTransferBooking(
            booking_id=UUID(
                "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
            ),
            booking_date=date(2026, 5, 1),
            booking_type="REGULAR",
            lines=(
                ClientTransferBookingLine(
                    position=0,
                    account_number="1000",
                    side="DEBIT",
                    amount="100.00",
                ),
                ClientTransferBookingLine(
                    position=2,
                    account_number="1200",
                    side="CREDIT",
                    amount="100.00",
                ),
            ),
        )


def test_reversal_booking_requires_original_booking() -> None:
    with pytest.raises(
        ValueError,
        match="requires reversal_of_booking_id",
    ):
        ClientTransferBooking(
            booking_id=UUID(
                "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
            ),
            booking_date=date(2026, 5, 2),
            booking_type="REVERSAL",
            lines=(),
        )


def test_fiscal_year_contains_portable_bookings() -> None:
    booking = ClientTransferBooking(
        booking_id=UUID(
            "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
        ),
        booking_date=date(2026, 5, 1),
        booking_type="REGULAR",
        lines=(
            ClientTransferBookingLine(
                position=0,
                account_number="1000",
                side="DEBIT",
                amount="100.00",
            ),
            ClientTransferBookingLine(
                position=1,
                account_number="1200",
                side="CREDIT",
                amount="100.00",
            ),
        ),
    )

    fiscal_year = ClientTransferFiscalYear(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        status="OPEN",
        opening_source=(
            ClientTransferFiscalYearReference(
                start_date=date(2025, 1, 1),
                end_date=date(2025, 12, 31),
            )
        ),
        bookings=(booking,),
    )

    assert fiscal_year.bookings == (booking,)
    assert fiscal_year.opening_source is not None
    assert (
        fiscal_year.opening_source.end_date
        == date(2025, 12, 31)
    )


def test_fiscal_year_rejects_booking_outside_period() -> None:
    booking = ClientTransferBooking(
        booking_id=UUID(
            "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
        ),
        booking_date=date(2025, 12, 31),
        booking_type="REGULAR",
        lines=(),
    )

    with pytest.raises(
        ValueError,
        match="within the fiscal year",
    ):
        ClientTransferFiscalYear(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            status="OPEN",
            opening_source=None,
            bookings=(booking,),
        )


def test_client_rejects_duplicate_fiscal_years() -> None:
    fiscal_year = ClientTransferFiscalYear(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        status="OPEN",
        opening_source=None,
    )

    client = _build_client()

    with pytest.raises(
        ValueError,
        match="fiscal_years must not contain duplicates",
    ):
        ClientTransferClient(
            company_id=client.company_id,
            master_data=client.master_data,
            accounts=client.accounts,
            control_accounts=client.control_accounts,
            vat_accounts=client.vat_accounts,
            account_roles=client.account_roles,
            taxonomy_mappings=(
                client.taxonomy_mappings
            ),
            fiscal_years=(
                fiscal_year,
                fiscal_year,
            ),
        )


def test_shareholder_preserves_portable_identity() -> None:
    shareholder = ClientTransferShareholder(
        shareholder_id=UUID(
            "11111111-1111-1111-1111-111111111111"
        ),
        shareholder_number=" 1 ",
        name=" Mustermann ",
        first_name=" Erika ",
        legal_status=" Gesellschafter ",
        share_numerator="50",
        share_denominator="100",
    )

    assert shareholder.shareholder_number == "1"
    assert shareholder.name == "Mustermann"
    assert shareholder.first_name == "Erika"


def test_fixed_asset_movement_requires_booking_line_reference() -> None:
    booking_line = ClientTransferBookingLineReference(
        booking_id=UUID(
            "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
        ),
        position=1,
    )

    movement = ClientTransferFixedAssetMovement(
        movement_id=UUID(
            "22222222-2222-2222-2222-222222222222"
        ),
        fiscal_year_end=date(2026, 12, 31),
        movement_date=date(2026, 4, 1),
        amount="1000.00",
        booking_line=booking_line,
        movement_type="ACQUISITION",
    )

    assert movement.booking_line == booking_line


def test_reversal_movement_requires_reversed_movement_id() -> None:
    with pytest.raises(
        ValueError,
        match="requires reversed_movement_id",
    ):
        ClientTransferFixedAssetMovement(
            movement_id=UUID(
                "22222222-2222-2222-2222-222222222222"
            ),
            fiscal_year_end=date(2026, 12, 31),
            movement_date=date(2026, 4, 2),
            amount="1000.00",
            booking_line=ClientTransferBookingLineReference(
                booking_id=UUID(
                    "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
                ),
                position=1,
            ),
            movement_type="REVERSAL",
        )


def test_depreciation_contains_tax_adjustment() -> None:
    depreciation_id = UUID(
        "33333333-3333-3333-3333-333333333333"
    )

    adjustment = ClientTransferTaxDepreciationAdjustment(
        depreciation_id=depreciation_id,
        tax_amount="900.00",
    )

    depreciation = ClientTransferFixedAssetDepreciation(
        depreciation_id=depreciation_id,
        fiscal_year_end=date(2026, 12, 31),
        depreciation_date=date(2026, 12, 31),
        amount="1000.00",
        booking_line=ClientTransferBookingLineReference(
            booking_id=UUID(
                "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
            ),
            position=0,
        ),
        kind="LINEAR",
        source="CALCULATED",
        tax_adjustment=adjustment,
    )

    assert depreciation.tax_adjustment == adjustment


def test_tax_adjustment_must_reference_depreciation() -> None:
    adjustment = ClientTransferTaxDepreciationAdjustment(
        depreciation_id=UUID(
            "44444444-4444-4444-4444-444444444444"
        ),
        tax_amount="900.00",
    )

    with pytest.raises(
        ValueError,
        match="must reference this depreciation",
    ):
        ClientTransferFixedAssetDepreciation(
            depreciation_id=UUID(
                "33333333-3333-3333-3333-333333333333"
            ),
            fiscal_year_end=date(2026, 12, 31),
            depreciation_date=date(2026, 12, 31),
            amount="1000.00",
            booking_line=ClientTransferBookingLineReference(
                booking_id=UUID(
                    "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
                ),
                position=0,
            ),
            kind="LINEAR",
            source="CALCULATED",
            tax_adjustment=adjustment,
        )


def test_fixed_asset_contains_complete_history() -> None:
    booking_line = ClientTransferBookingLineReference(
        booking_id=UUID(
            "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
        ),
        position=1,
    )

    movement = ClientTransferFixedAssetMovement(
        movement_id=UUID(
            "22222222-2222-2222-2222-222222222222"
        ),
        fiscal_year_end=date(2026, 12, 31),
        movement_date=date(2026, 4, 1),
        amount="1000.00",
        booking_line=booking_line,
        movement_type="ACQUISITION",
    )

    fixed_asset = ClientTransferFixedAsset(
        fixed_asset_id=UUID(
            "55555555-5555-5555-5555-555555555555"
        ),
        asset_code="BGA-001",
        description="Notebook",
        position_code=(
            "HGB.266.AKTIVA.A.II.3"
        ),
        asset_account_number="0400",
        depreciation_expense_account_number="4830",
        acquisition_date=date(2026, 4, 1),
        acquisition_cost="1000.00",
        depreciation_start_date=date(2026, 4, 1),
        useful_life_months=36,
        status="ACTIVE",
        movements=(movement,),
    )

    assert fixed_asset.movements == (movement,)
    assert fixed_asset.depreciations == ()


def test_profit_appropriation_annual_data_references_year() -> None:
    fiscal_year = ClientTransferFiscalYearReference(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )

    data = ClientTransferProfitAppropriationAnnualData(
        fiscal_year=fiscal_year,
        statutory_reserve_addition="100.00",
        other_revenue_reserves_addition="200.00",
        statutory_reserve_release="0.00",
        other_revenue_reserves_release="0.00",
        distribution="500.00",
        profit_loss_carryforward="-50.00",
    )

    assert data.fiscal_year == fiscal_year
    assert data.profit_loss_carryforward == "-50.00"


def test_profit_appropriation_posting_preserves_references() -> None:
    source_fiscal_year = ClientTransferFiscalYearReference(
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
    )
    booking_line = ClientTransferBookingLineReference(
        booking_id=UUID(
            "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
        ),
        position=1,
    )

    posting = ClientTransferProfitAppropriationPosting(
        posting_id=UUID(
            "66666666-6666-6666-6666-666666666666"
        ),
        source_fiscal_year=source_fiscal_year,
        posting_date=date(2026, 3, 1),
        amount="500.00",
        booking_line=booking_line,
        posting_type="DISTRIBUTION",
    )

    assert posting.source_fiscal_year == source_fiscal_year
    assert posting.booking_line == booking_line


def test_profit_appropriation_posting_rejects_unknown_type() -> None:
    with pytest.raises(
        ValueError,
        match="unknown posting_type",
    ):
        ClientTransferProfitAppropriationPosting(
            posting_id=UUID(
                "66666666-6666-6666-6666-666666666666"
            ),
            source_fiscal_year=(
                ClientTransferFiscalYearReference(
                    start_date=date(2025, 1, 1),
                    end_date=date(2025, 12, 31),
                )
            ),
            posting_date=date(2026, 3, 1),
            amount="500.00",
            booking_line=(
                ClientTransferBookingLineReference(
                    booking_id=UUID(
                        "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
                    ),
                    position=1,
                )
            ),
            posting_type="UNKNOWN",
        )


def test_equity_contribution_is_booking_line_reference() -> None:
    booking_line = ClientTransferBookingLineReference(
        booking_id=UUID(
            "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
        ),
        position=1,
    )

    contribution = ClientTransferEquityContribution(
        booking_line=booking_line,
    )

    assert contribution.booking_line == booking_line


def test_client_rejects_duplicate_equity_contributions() -> None:
    contribution = ClientTransferEquityContribution(
        booking_line=ClientTransferBookingLineReference(
            booking_id=UUID(
                "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
            ),
            position=1,
        ),
    )

    with pytest.raises(
        ValueError,
        match="duplicate booking lines",
    ):
        ClientTransferClient(
            company_id=UUID(
                "12345678-1234-5678-1234-567812345678"
            ),
            master_data=ClientTransferMasterData(
                name="Test UG",
                legal_form="UG (haftungsbeschränkt)",
            ),
            accounts=(),
            control_accounts=ClientTransferControlAccounts(),
            vat_accounts=ClientTransferVatAccounts(),
            account_roles=ClientTransferAccountRoles(),
            equity_contributions=(
                contribution,
                contribution,
            ),
        )


def test_client_rejects_duplicate_equity_contributions() -> None:
    contribution = ClientTransferEquityContribution(
        booking_line=ClientTransferBookingLineReference(
            booking_id=UUID(
                "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
            ),
            position=1,
        ),
    )

    with pytest.raises(
        ValueError,
        match="duplicate booking lines",
    ):
        ClientTransferClient(
            company_id=COMPANY_ID,
            master_data=ClientTransferMasterData(
                name="Test UG",
                legal_form="UG (haftungsbeschränkt)",
            ),
            accounts=(),
            control_accounts=None,
            vat_accounts=None,
            account_roles=ClientTransferAccountRoles(),
            equity_contributions=(
                contribution,
                contribution,
            ),
        )

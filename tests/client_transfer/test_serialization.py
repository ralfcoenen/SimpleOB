"""Tests für die JSON-Serialisierung des Mandantentransfers."""

import json
from datetime import date, datetime, timezone
from uuid import UUID

import pytest

from openbilanz.client_transfer.model import (
    ClientTransfer,
    ClientTransferAccount,
    ClientTransferAccountRoles,
    ClientTransferApplication,
    ClientTransferBooking,
    ClientTransferBookingLine,
    ClientTransferBookingLineReference,
    ClientTransferClient,
    ClientTransferControlAccounts,
    ClientTransferEquityContribution,
    ClientTransferFiscalYear,
    ClientTransferFiscalYearReference,
    ClientTransferFixedAsset,
    ClientTransferFixedAssetDepreciation,
    ClientTransferFixedAssetMovement,
    ClientTransferFormat,
    ClientTransferMasterData,
    ClientTransferProfitAppropriationAnnualData,
    ClientTransferProfitAppropriationPosting,
    ClientTransferShareholder,
    ClientTransferTaxDepreciationAdjustment,
    ClientTransferTaxonomyMapping,
    ClientTransferVatAccounts,
)
from openbilanz.client_transfer.serialization import (
    client_transfer_from_json,
    client_transfer_to_dict,
    client_transfer_to_json,
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


def _build_transfer() -> ClientTransfer:
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
            30,
            tzinfo=timezone.utc,
        ),
        client=ClientTransferClient(
            company_id=COMPANY_ID,
            master_data=ClientTransferMasterData(
                name="Test UG",
                legal_form="UG (haftungsbeschränkt)",
                tax_number="123/456/78901",
                city="Düsseldorf",
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
            account_roles=ClientTransferAccountRoles(
                cash_accounts=("1000",),
            ),
            fiscal_years=(
                ClientTransferFiscalYear(
                    start_date=date(2026, 1, 1),
                    end_date=date(2026, 12, 31),
                    status="OPEN",
                    opening_source=None,
                    bookings=(
                        ClientTransferBooking(
                            booking_id=BOOKING_ID,
                            booking_date=date(2026, 6, 1),
                            booking_type="REGULAR",
                            voucher_no="B-001",
                            description="Testbuchung",
                            lines=(
                                ClientTransferBookingLine(
                                    position=0,
                                    account_number="1000",
                                    side="DEBIT",
                                    amount="1234.56",
                                ),
                            ),
                        ),
                    ),
                ),
            ),
        ),
    )


def test_transfer_json_roundtrip() -> None:
    transfer = _build_transfer()

    text = client_transfer_to_json(transfer)
    restored = client_transfer_from_json(text)

    assert restored == transfer


def test_transfer_json_uses_portable_scalar_values() -> None:
    transfer = _build_transfer()

    data = client_transfer_to_dict(transfer)

    assert data["exported_at"] == (
        "2026-10-02T20:30:00+00:00"
    )
    assert data["client"]["company_id"] == str(
        COMPANY_ID
    )
    assert (
        data["client"]["fiscal_years"][0]["start_date"]
        == "2026-01-01"
    )
    assert (
        data["client"]["fiscal_years"][0]["bookings"][0][
            "booking_id"
        ]
        == str(BOOKING_ID)
    )
    assert (
        data["client"]["fiscal_years"][0]["bookings"][0][
            "lines"
        ][0]["amount"]
        == "1234.56"
    )


def test_transfer_json_preserves_unicode() -> None:
    text = client_transfer_to_json(
        _build_transfer()
    )

    assert "Düsseldorf" in text
    assert "\\u00fcsseldorf" not in text


def test_transfer_json_is_valid_json() -> None:
    text = client_transfer_to_json(
        _build_transfer()
    )

    data = json.loads(text)

    assert data["format"]["name"] == (
        "SimpleOB Client Transfer"
    )
    assert data["format"]["version"] == 1


def test_invalid_json_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="invalid client transfer JSON",
    ):
        client_transfer_from_json("{kein JSON}")


def test_unsupported_format_version_is_rejected() -> None:
    transfer = _build_transfer()
    data = client_transfer_to_dict(transfer)

    data["format"]["version"] = 2

    text = json.dumps(data)

    with pytest.raises(
        ValueError,
        match=(
            "Nicht unterstützte Version des "
            "Mandantentransferformats"
        ),
    ):
        client_transfer_from_json(text)


def test_complete_transfer_json_roundtrip() -> None:
    fiscal_year_reference = (
        ClientTransferFiscalYearReference(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )
    )
    booking_line_reference = (
        ClientTransferBookingLineReference(
            booking_id=BOOKING_ID,
            position=0,
        )
    )

    transfer = ClientTransfer(
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
            30,
            tzinfo=timezone.utc,
        ),
        client=ClientTransferClient(
            company_id=COMPANY_ID,
            master_data=ClientTransferMasterData(
                name="Test UG",
                legal_form="UG (haftungsbeschränkt)",
                tax_number="123/456/78901",
                tax_office="Düsseldorf",
                tax_id="12345678901",
                tax_economic_id="DE123456789",
                bf4="1234",
                street="Teststraße",
                house_number="1",
                postal_code="40210",
                city="Düsseldorf",
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
                    debit_position_code="CASH",
                    credit_position_code=None,
                ),
            ),
            control_accounts=ClientTransferControlAccounts(
                opening_balance_account="1000",
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
            vat_accounts=ClientTransferVatAccounts(
                input_tax_7="1000",
                input_tax_19="1000",
                output_tax_7="1000",
                output_tax_19="1000",
            ),
            account_roles=ClientTransferAccountRoles(
                cash_accounts=("1000",),
            ),
            taxonomy_mappings=(
                ClientTransferTaxonomyMapping(
                    taxonomy_version="6.9",
                    account_number="1000",
                    concept_name="test.concept",
                ),
            ),
            shareholders=(
                ClientTransferShareholder(
                    shareholder_id=SHAREHOLDER_ID,
                    shareholder_number="1",
                    name="Mustermann",
                    first_name="Max",
                    legal_status="NATURAL_PERSON",
                    share_numerator="1",
                    share_denominator="1",
                    tax_number="123/456/78901",
                    tax_number_federal_state="NW",
                    tax_id="12345678901",
                    wid="",
                ),
            ),
            fixed_assets=(
                ClientTransferFixedAsset(
                    fixed_asset_id=FIXED_ASSET_ID,
                    asset_code="BGA-001",
                    description="Testanlage",
                    position_code="BGA",
                    asset_account_number="1000",
                    depreciation_expense_account_number="1000",
                    acquisition_date=date(2026, 1, 1),
                    acquisition_cost="100.00",
                    depreciation_start_date=date(2026, 1, 1),
                    useful_life_months=60,
                    status="ACTIVE",
                    movements=(
                        ClientTransferFixedAssetMovement(
                            movement_id=MOVEMENT_ID,
                            fiscal_year_end=date(
                                2026,
                                12,
                                31,
                            ),
                            movement_date=date(
                                2026,
                                6,
                                1,
                            ),
                            amount="100.00",
                            booking_line=(
                                booking_line_reference
                            ),
                            movement_type="ACQUISITION",
                        ),
                    ),
                    depreciations=(
                        ClientTransferFixedAssetDepreciation(
                            depreciation_id=DEPRECIATION_ID,
                            fiscal_year_end=date(
                                2026,
                                12,
                                31,
                            ),
                            depreciation_date=date(
                                2026,
                                6,
                                1,
                            ),
                            amount="100.00",
                            booking_line=(
                                booking_line_reference
                            ),
                            kind="LINEAR",
                            source="CALCULATED",
                            tax_adjustment=(
                                ClientTransferTaxDepreciationAdjustment(
                                    depreciation_id=(
                                        DEPRECIATION_ID
                                    ),
                                    tax_amount="90.00",
                                )
                            ),
                        ),
                    ),
                ),
            ),
            profit_appropriation_annual_data=(
                ClientTransferProfitAppropriationAnnualData(
                    fiscal_year=fiscal_year_reference,
                    statutory_reserve_addition="0.00",
                    other_revenue_reserves_addition="0.00",
                    statutory_reserve_release="0.00",
                    other_revenue_reserves_release="0.00",
                    distribution="0.00",
                    profit_loss_carryforward="100.00",
                ),
            ),
            profit_appropriation_postings=(
                ClientTransferProfitAppropriationPosting(
                    posting_id=POSTING_ID,
                    source_fiscal_year=(
                        fiscal_year_reference
                    ),
                    posting_date=date(2026, 6, 1),
                    amount="100.00",
                    booking_line=booking_line_reference,
                    posting_type="DISTRIBUTION",
                ),
            ),
            equity_contributions=(
                ClientTransferEquityContribution(
                    booking_line=booking_line_reference,
                ),
            ),
            fiscal_years=(
                ClientTransferFiscalYear(
                    start_date=date(2026, 1, 1),
                    end_date=date(2026, 12, 31),
                    status="OPEN",
                    opening_source=None,
                    bookings=(
                        ClientTransferBooking(
                            booking_id=BOOKING_ID,
                            booking_date=date(
                                2026,
                                6,
                                1,
                            ),
                            booking_type="REGULAR",
                            voucher_no="B-001",
                            description="Testbuchung",
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
                ),
            ),
        ),
    )

    text = client_transfer_to_json(transfer)
    restored = client_transfer_from_json(text)

    assert restored == transfer

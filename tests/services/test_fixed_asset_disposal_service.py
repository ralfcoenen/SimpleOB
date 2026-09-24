"""Tests für die Berechnung von Anlagenverkäufen."""

from datetime import date
from decimal import Decimal

import pytest

from openbilanz.domain.accounting_control_accounts import (
    AccountingControlAccounts,
)
from openbilanz.domain.entry_side import EntrySide
from openbilanz.domain.vat_accounts import VatAccounts
from openbilanz.services.fixed_asset_disposal_service import (
    FixedAssetDisposalService,
)


@pytest.mark.parametrize(
    (
        "gross_proceeds",
        "expected_net_proceeds",
        "expected_tax_amount",
        "expected_gain",
        "expected_loss",
        "expected_lines",
    ),
    (
        (
            Decimal("2500.00"),
            Decimal("2100.84"),
            Decimal("399.16"),
            Decimal("150.84"),
            Decimal("0.00"),
            (
                ("1200", EntrySide.DEBIT, Decimal("2500.00")),
                ("0400", EntrySide.CREDIT, Decimal("1950.00")),
                ("8500", EntrySide.CREDIT, Decimal("150.84")),
                ("1776", EntrySide.CREDIT, Decimal("399.16")),
            ),
        ),
        (
            Decimal("1785.00"),
            Decimal("1500.00"),
            Decimal("285.00"),
            Decimal("0.00"),
            Decimal("450.00"),
            (
                ("1200", EntrySide.DEBIT, Decimal("1785.00")),
                ("0400", EntrySide.CREDIT, Decimal("1950.00")),
                ("4900", EntrySide.DEBIT, Decimal("450.00")),
                ("1776", EntrySide.CREDIT, Decimal("285.00")),
            ),
        ),
        (
            Decimal("2320.50"),
            Decimal("1950.00"),
            Decimal("370.50"),
            Decimal("0.00"),
            Decimal("0.00"),
            (
                ("1200", EntrySide.DEBIT, Decimal("2320.50")),
                ("0400", EntrySide.CREDIT, Decimal("1950.00")),
                ("1776", EntrySide.CREDIT, Decimal("370.50")),
            ),
        ),
    ),
)
def test_calculates_fixed_asset_disposal_booking(
    gross_proceeds: Decimal,
    expected_net_proceeds: Decimal,
    expected_tax_amount: Decimal,
    expected_gain: Decimal,
    expected_loss: Decimal,
    expected_lines: tuple[
        tuple[str, EntrySide, Decimal],
        ...,
    ],
) -> None:
    service = FixedAssetDisposalService()

    control_accounts = AccountingControlAccounts(
        opening_balance_account="9000",
        income_summary_account="8990",
        profit_account="8020",
        loss_account="8021",
        profit_loss_carryforward_account="2970",
        statutory_reserve_account="0846",
        other_revenue_reserves_account="0855",
        distribution_liability_account="0755",
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

    result = service.calculate(
        booking_date=date(2026, 9, 20),
        acquisition_cost=Decimal("2600.00"),
        accumulated_depreciation=Decimal("650.00"),
        gross_proceeds=gross_proceeds,
        tax_rate=19,
        asset_account_number="0400",
        counter_account_number="1200",
        control_accounts=control_accounts,
        vat_accounts=vat_accounts,
        voucher_no="AB-001",
        description="Verkauf PA-Anlage",
    )

    assert result.acquisition_cost == Decimal("2600.00")
    assert result.accumulated_depreciation == Decimal("650.00")
    assert result.carrying_amount == Decimal("1950.00")
    assert result.gross_proceeds == gross_proceeds
    assert result.net_proceeds == expected_net_proceeds
    assert result.tax_amount == expected_tax_amount
    assert result.gain == expected_gain
    assert result.loss == expected_loss

    assert result.booking.booking_date == date(2026, 9, 20)
    assert result.booking.voucher_no == "AB-001"
    assert result.booking.description == "Verkauf PA-Anlage"
    assert result.booking.is_balanced

    assert tuple(
        (
            line.account_number,
            line.side,
            line.amount,
        )
        for line in result.booking.lines
    ) == expected_lines

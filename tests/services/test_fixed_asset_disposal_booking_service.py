"""Tests für Buchungen aus Anlagenverkäufen."""

from datetime import date
from decimal import Decimal

from openbilanz.domain.entry_side import EntrySide
from openbilanz.services.fixed_asset_disposal_booking_service import (
    FixedAssetDisposalBookingService,
)


def test_builds_fixed_asset_disposal_bookings_with_19_percent_vat() -> None:
    service = FixedAssetDisposalBookingService()

    result = service.build_bookings(
        disposal_date=date(2026, 8, 15),
        net_sale_amount=Decimal("8000.00"),
        book_value=Decimal("10000.00"),
        settlement_account_number="1200",
        revenue_account_number="8510",
        output_tax_account_number="1776",
        asset_account_number="0400",
        book_value_expense_account_number="4840",
        tax_rate=Decimal("0.19"),
        asset_code="A-0001",
    )

    sale = result.sale_booking

    assert sale.debit_total == Decimal("9520.00")
    assert sale.credit_total == Decimal("9520.00")

    assert sale.lines[0].account_number == "1200"
    assert sale.lines[0].side is EntrySide.DEBIT
    assert sale.lines[0].amount == Decimal("9520.00")

    assert sale.lines[1].account_number == "8510"
    assert sale.lines[1].side is EntrySide.CREDIT
    assert sale.lines[1].amount == Decimal("8000.00")

    assert sale.lines[2].account_number == "1776"
    assert sale.lines[2].side is EntrySide.CREDIT
    assert sale.lines[2].amount == Decimal("1520.00")

    book_value = result.book_value_booking

    assert book_value.debit_total == Decimal("10000.00")
    assert book_value.credit_total == Decimal("10000.00")

    assert book_value.lines[0].account_number == "4840"
    assert book_value.lines[0].side is EntrySide.DEBIT

    assert book_value.lines[1].account_number == "0400"
    assert book_value.lines[1].side is EntrySide.CREDIT


def test_builds_fixed_asset_disposal_booking_without_vat() -> None:
    service = FixedAssetDisposalBookingService()

    result = service.build_bookings(
        disposal_date=date(2026, 8, 15),
        net_sale_amount=Decimal("8000.00"),
        book_value=Decimal("10000.00"),
        settlement_account_number="1200",
        revenue_account_number="8510",
        output_tax_account_number="1776",
        asset_account_number="0400",
        book_value_expense_account_number="4840",
        tax_rate=Decimal("0.00"),
        asset_code="A-0001",
    )

    sale = result.sale_booking

    assert len(sale.lines) == 2
    assert sale.debit_total == Decimal("8000.00")
    assert sale.credit_total == Decimal("8000.00")
    assert (
        result.sale_booking.description
        == "Verkauf Anlagegut – A-0001"
    )

    assert (
        result.book_value_booking.description
        == "Buchwertabgang Anlagegut – A-0001"
    )

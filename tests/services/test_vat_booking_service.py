"""Tests für die Erzeugung von Umsatzsteuerbuchungen."""

from datetime import date
from decimal import Decimal

from openbilanz.domain.entry_side import EntrySide
from openbilanz.domain.vat_accounts import VatAccounts
from openbilanz.domain.vat_booking_item import VatBookingItem
from openbilanz.domain.vat_configuration import VatConfiguration
from openbilanz.domain.vat_taxation_type import VatTaxationType
from openbilanz.services.vat_booking_service import (
    VatBookingService,
)

VAT_ACCOUNTS = VatAccounts(
    input_tax_7="1571",
    input_tax_19="1576",
    output_tax_7="1771",
    output_tax_19="1776",
)

STANDARD_VAT_CONFIGURATION = VatConfiguration(
    taxation_type=VatTaxationType.STANDARD,
    effective_from=date(2026, 1, 1),
)

SMALL_BUSINESS_VAT_CONFIGURATION = VatConfiguration(
    taxation_type=VatTaxationType.SMALL_BUSINESS,
    effective_from=date(2026, 1, 1),
)

def test_builds_output_booking_with_19_percent_vat() -> None:
    """Eine Ausgangsrechnung trennt Erlös und Umsatzsteuer."""

    service = VatBookingService()

    booking = service.build_output_booking(
        booking_date=date(2026, 8, 20),
        counter_account_number="1400",
        items=(
            VatBookingItem(
                account_number="8400",
                gross_amount=Decimal("119.00"),
                tax_rate=19,
            ),
        ),
        vat_accounts=VAT_ACCOUNTS,
        vat_configuration=STANDARD_VAT_CONFIGURATION,
        voucher_no="AR-001",
        description="Ausgangsrechnung",
    )

    assert booking.debit_total == Decimal("119.00")
    assert booking.credit_total == Decimal("119.00")

    assert tuple(
        (
            line.account_number,
            line.side,
            line.amount,
        )
        for line in booking.lines
    ) == (
        (
            "1400",
            EntrySide.DEBIT,
            Decimal("119.00"),
        ),
        (
            "8400",
            EntrySide.CREDIT,
            Decimal("100.00"),
        ),
        (
            "1776",
            EntrySide.CREDIT,
            Decimal("19.00"),
        ),
    )


def test_builds_input_booking_with_19_percent_vat() -> None:
    """Eine Eingangsrechnung trennt Aufwand und Vorsteuer."""

    service = VatBookingService()

    booking = service.build_input_booking(
        booking_date=date(2026, 8, 20),
        counter_account_number="1600",
        items=(
            VatBookingItem(
                account_number="3100",
                gross_amount=Decimal("119.00"),
                tax_rate=19,
            ),
        ),
        vat_accounts=VAT_ACCOUNTS,
        vat_configuration=STANDARD_VAT_CONFIGURATION,
        voucher_no="ER-001",
        description="Eingangsrechnung",
    )

    assert booking.debit_total == Decimal("119.00")
    assert booking.credit_total == Decimal("119.00")

    assert tuple(
        (
            line.account_number,
            line.side,
            line.amount,
        )
        for line in booking.lines
    ) == (
        (
            "3100",
            EntrySide.DEBIT,
            Decimal("100.00"),
        ),
        (
            "1576",
            EntrySide.DEBIT,
            Decimal("19.00"),
        ),
        (
            "1600",
            EntrySide.CREDIT,
            Decimal("119.00"),
        ),
    )


def test_builds_mixed_output_booking() -> None:
    """Eine Rechnung darf 7 und 19 Prozent enthalten."""

    service = VatBookingService()

    booking = service.build_output_booking(
        booking_date=date(2026, 8, 20),
        counter_account_number="1400",
        items=(
            VatBookingItem(
                account_number="8400",
                gross_amount=Decimal("119.00"),
                tax_rate=19,
            ),
            VatBookingItem(
                account_number="8300",
                gross_amount=Decimal("107.00"),
                tax_rate=7,
            ),
        ),
        vat_accounts=VAT_ACCOUNTS,
        vat_configuration=STANDARD_VAT_CONFIGURATION,
    )

    assert booking.debit_total == Decimal("226.00")
    assert booking.credit_total == Decimal("226.00")

    assert tuple(
        (
            line.account_number,
            line.side,
            line.amount,
        )
        for line in booking.lines
    ) == (
        (
            "1400",
            EntrySide.DEBIT,
            Decimal("226.00"),
        ),
        (
            "8400",
            EntrySide.CREDIT,
            Decimal("100.00"),
        ),
        (
            "1776",
            EntrySide.CREDIT,
            Decimal("19.00"),
        ),
        (
            "8300",
            EntrySide.CREDIT,
            Decimal("100.00"),
        ),
        (
            "1771",
            EntrySide.CREDIT,
            Decimal("7.00"),
        ),
    )

def test_builds_zero_percent_booking_without_tax_line() -> None:
    """Bei 0 Prozent entsteht keine Steuerzeile."""

    service = VatBookingService()

    booking = service.build_output_booking(
        booking_date=date(2026, 8, 20),
        counter_account_number="1400",
        items=(
            VatBookingItem(
                account_number="8500",
                gross_amount=Decimal("100.00"),
                tax_rate=0,
            ),
        ),
        vat_accounts=VAT_ACCOUNTS,
        vat_configuration=STANDARD_VAT_CONFIGURATION,
    )

    assert booking.debit_total == Decimal("100.00")
    assert booking.credit_total == Decimal("100.00")

    assert tuple(
        (
            line.account_number,
            line.side,
            line.amount,
        )
        for line in booking.lines
    ) == (
        (
            "1400",
            EntrySide.DEBIT,
            Decimal("100.00"),
        ),
        (
            "8500",
            EntrySide.CREDIT,
            Decimal("100.00"),
        ),
    )

def test_rounds_vat_amounts_to_cents() -> None:
    """Bruttobeträge werden centgenau in Netto und Steuer geteilt."""

    service = VatBookingService()

    booking = service.build_output_booking(
        booking_date=date(2026, 8, 20),
        counter_account_number="1400",
        items=(
            VatBookingItem(
                account_number="8400",
                gross_amount=Decimal("10.00"),
                tax_rate=19,
            ),
        ),
        vat_accounts=VAT_ACCOUNTS,
        vat_configuration=STANDARD_VAT_CONFIGURATION,
    )

    assert booking.debit_total == Decimal("10.00")
    assert booking.credit_total == Decimal("10.00")

    assert tuple(
        line.amount
        for line in booking.credit_lines
    ) == (
        Decimal("8.40"),
        Decimal("1.60"),
    )

def test_builds_customer_credit_note_with_7_percent_vat() -> None:
    """Eine Kundengutschrift mindert Erlös und Umsatzsteuer."""

    service = VatBookingService()

    booking = service.build_customer_credit_note(
        booking_date=date(2026, 8, 20),
        counter_account_number="1400",
        items=(
            VatBookingItem(
                account_number="8410",
                gross_amount=Decimal("107.00"),
                tax_rate=7,
            ),
        ),
        vat_accounts=VAT_ACCOUNTS,
        vat_configuration=STANDARD_VAT_CONFIGURATION,
        voucher_no="KG-001",
        description="Kundengutschrift",
    )

    assert booking.debit_total == Decimal("107.00")
    assert booking.credit_total == Decimal("107.00")

    assert tuple(
        (
            line.account_number,
            line.side,
            line.amount,
        )
        for line in booking.lines
    ) == (
        (
            "8410",
            EntrySide.DEBIT,
            Decimal("100.00"),
        ),
        (
            "1771",
            EntrySide.DEBIT,
            Decimal("7.00"),
        ),
        (
            "1400",
            EntrySide.CREDIT,
            Decimal("107.00"),
        ),
    )


def test_builds_supplier_credit_note_with_19_percent_vat() -> None:
    """Eine Lieferantengutschrift mindert Aufwand und Vorsteuer."""

    service = VatBookingService()

    booking = service.build_supplier_credit_note(
        booking_date=date(2026, 8, 20),
        counter_account_number="1600",
        items=(
            VatBookingItem(
                account_number="4930",
                gross_amount=Decimal("119.00"),
                tax_rate=19,
            ),
        ),
        vat_accounts=VAT_ACCOUNTS,
        vat_configuration=STANDARD_VAT_CONFIGURATION,
        voucher_no="LG-001",
        description="Lieferantengutschrift",
    )

    assert booking.debit_total == Decimal("119.00")
    assert booking.credit_total == Decimal("119.00")

    assert tuple(
        (
            line.account_number,
            line.side,
            line.amount,
        )
        for line in booking.lines
    ) == (
        (
            "1600",
            EntrySide.DEBIT,
            Decimal("119.00"),
        ),
        (
            "4930",
            EntrySide.CREDIT,
            Decimal("100.00"),
        ),
        (
            "1576",
            EntrySide.CREDIT,
            Decimal("19.00"),
        ),
    )

def test_builds_small_business_output_booking_without_vat() -> None:
    """§ 19 bucht den Bruttobetrag vollständig als Erlös."""

    service = VatBookingService()

    booking = service.build_output_booking(
        booking_date=date(2026, 8, 20),
        counter_account_number="1400",
        items=(
            VatBookingItem(
                account_number="8400",
                gross_amount=Decimal("119.00"),
                tax_rate=19,
            ),
        ),
        vat_accounts=VAT_ACCOUNTS,
        vat_configuration=SMALL_BUSINESS_VAT_CONFIGURATION,
    )

    assert tuple(
        (
            line.account_number,
            line.side,
            line.amount,
        )
        for line in booking.lines
    ) == (
        (
            "1400",
            EntrySide.DEBIT,
            Decimal("119.00"),
        ),
        (
            "8400",
            EntrySide.CREDIT,
            Decimal("119.00"),
        ),
    )

def test_builds_small_business_input_booking_without_input_tax() -> None:
    """§ 19 bucht den Bruttobetrag ohne Vorsteuerabzug."""

    service = VatBookingService()

    booking = service.build_input_booking(
        booking_date=date(2026, 8, 20),
        counter_account_number="1600",
        items=(
            VatBookingItem(
                account_number="3100",
                gross_amount=Decimal("119.00"),
                tax_rate=19,
            ),
        ),
        vat_accounts=VAT_ACCOUNTS,
        vat_configuration=SMALL_BUSINESS_VAT_CONFIGURATION,
    )

    assert tuple(
        (
            line.account_number,
            line.side,
            line.amount,
        )
        for line in booking.lines
    ) == (
        (
            "3100",
            EntrySide.DEBIT,
            Decimal("119.00"),
        ),
        (
            "1600",
            EntrySide.CREDIT,
            Decimal("119.00"),
        ),
    )

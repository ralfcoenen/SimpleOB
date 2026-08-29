"""Tests für die PySide6-Umsatzsteuerbuchung."""

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, Mock

from PySide6.QtWidgets import QApplication, QLabel

from openbilanz.domain.account import Account
from openbilanz.domain.account_role import AccountRole
from openbilanz.domain.account_type import AccountType
from openbilanz.domain.vat_accounts import VatAccounts
from openbilanz.domain.vat_configuration import VatConfiguration
from openbilanz.domain.vat_payment_kind import VatPaymentKind
from openbilanz.domain.vat_revenue_kind import VatRevenueKind
from openbilanz.domain.vat_taxation_type import VatTaxationType
from openbilanz.ui_qt.vat_booking_widget import VatBookingWidget

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


def _application() -> QApplication:
    application = QApplication.instance()

    if application is None:
        application = QApplication([])

    return application


def _account(
    *,
    number: str,
    name: str,
    account_type: AccountType,
    account_role: AccountRole | None = None,
) -> Account:
    """Erzeugt ein minimales Konto für den Widget-Test."""

    account = MagicMock(spec=Account)
    account.number = number
    account.name = name
    account.account_type = account_type
    account.account_role = account_role
    account.__str__.return_value = f"{number} {name}"

    return account


def test_standard_vat_configuration_keeps_tax_rate_enabled() -> None:
    """Regelbesteuerung startet mit auswählbaren 19 Prozent."""

    _application()

    widget = VatBookingWidget(
        accounts=(),
        vat_accounts=VAT_ACCOUNTS,
        vat_configuration=STANDARD_VAT_CONFIGURATION,
        on_vat_booking_created=lambda *_args: None,
        on_vat_revenue_created=lambda *_args: None,
    )

    row = widget._position_rows[0]

    assert row.tax_rate_box.currentText() == "19 %"
    assert row.tax_rate_box.isEnabled() is True

    labels = {
        label.text()
        for label in widget.findChildren(QLabel)
    }

    assert (
        "Kleinunternehmer gemäß § 19 UStG – "
        "keine Umsatzsteuerberechnung"
        not in labels
    )

    widget.deleteLater()


def test_small_business_configuration_disables_tax_rate() -> None:
    """Kleinunternehmer buchen ohne auswählbare Umsatzsteuer."""

    _application()

    widget = VatBookingWidget(
        accounts=(),
        vat_accounts=VAT_ACCOUNTS,
        vat_configuration=SMALL_BUSINESS_VAT_CONFIGURATION,
        on_vat_booking_created=lambda *_args: None,
        on_vat_revenue_created=lambda *_args: None,
    )

    row = widget._position_rows[0]

    assert row.tax_rate_box.currentText() == "0 %"
    assert row.tax_rate_box.isEnabled() is False

    labels = {
        label.text()
        for label in widget.findChildren(QLabel)
    }

    assert (
        "Kleinunternehmer gemäß § 19 UStG – "
        "keine Umsatzsteuerberechnung"
        in labels
    )

    widget.deleteLater()


def test_output_invoice_reports_immediate_vat_revenue() -> None:
    """Eine sofort vereinnahmte Ausgangsrechnung meldet den Umsatz."""

    _application()

    bank_account = _account(
        number="1200",
        name="Bank",
        account_type=AccountType.ASSET,
        account_role=AccountRole.BANK,
    )
    revenue_account = _account(
        number="8400",
        name="Erlöse 19 %",
        account_type=AccountType.REVENUE,
    )

    on_vat_booking_created = Mock()
    on_vat_revenue_created = Mock()

    widget = VatBookingWidget(
        accounts=(
            bank_account,
            revenue_account,
        ),
        vat_accounts=VAT_ACCOUNTS,
        vat_configuration=STANDARD_VAT_CONFIGURATION,
        on_vat_booking_created=on_vat_booking_created,
        on_vat_revenue_created=on_vat_revenue_created,
    )

    widget._invoice_type_box.setCurrentText(
        "Ausgangsrechnung"
    )
    widget._counter_account.setCurrentText(
        str(bank_account)
    )

    row = widget._position_rows[0]
    row.account_box.setCurrentText(
        str(revenue_account)
    )
    row.amount_entry.setText("119,00")
    row.tax_rate_box.setCurrentText("19 %")

    widget._payment_kind_box.setCurrentText(
        "Sofort bezahlt"
    )

    widget._create_booking()

    on_vat_booking_created.assert_not_called()
    on_vat_revenue_created.assert_called_once()

    (
        booking,
        booking_details,
        gross_amount,
        revenue_kind,
        payment_kind,
        service_date,
    ) = on_vat_revenue_created.call_args.args

    assert len(booking_details) == 1

    detail = booking_details[0]

    assert detail.booking_id == booking.booking_id
    assert detail.account_number == "8400"
    assert detail.net_amount == Decimal("100.00")
    assert detail.tax_amount == Decimal("19.00")
    assert detail.tax_rate == 19

    assert booking.debit_total == Decimal("119.00")
    assert booking.credit_total == Decimal("119.00")
    assert gross_amount == Decimal("119.00")
    assert revenue_kind is VatRevenueKind.NORMAL
    assert payment_kind is VatPaymentKind.IMMEDIATE
    assert service_date == date.today()

    widget.deleteLater()


def test_output_invoice_reports_receivable_vat_revenue() -> None:
    """Eine noch offene Ausgangsrechnung wird als Forderung registriert."""

    _application()

    receivable_account = _account(
        number="1400",
        name="Forderungen",
        account_type=AccountType.ASSET,
        account_role=AccountRole.RECEIVABLE,
    )
    revenue_account = _account(
        number="8400",
        name="Erlöse 19 %",
        account_type=AccountType.REVENUE,
    )

    on_vat_booking_created = Mock()
    on_vat_revenue_created = Mock()

    widget = VatBookingWidget(
        accounts=(
            receivable_account,
            revenue_account,
        ),
        vat_accounts=VAT_ACCOUNTS,
        vat_configuration=STANDARD_VAT_CONFIGURATION,
        on_vat_booking_created=on_vat_booking_created,
        on_vat_revenue_created=on_vat_revenue_created,
    )

    widget._invoice_type_box.setCurrentText(
        "Ausgangsrechnung"
    )
    widget._counter_account.setCurrentText(
        str(receivable_account)
    )

    row = widget._position_rows[0]
    row.account_box.setCurrentText(
        str(revenue_account)
    )
    row.amount_entry.setText("119,00")
    row.tax_rate_box.setCurrentText("19 %")

    widget._payment_kind_box.setCurrentText(
        "Auf Rechnung / Forderung"
    )

    widget._create_booking()

    on_vat_booking_created.assert_not_called()
    on_vat_revenue_created.assert_called_once()

    (
        booking,
        booking_details,
        gross_amount,
        revenue_kind,
        payment_kind,
        service_date,
    ) = on_vat_revenue_created.call_args.args

    assert len(booking_details) == 1

    detail = booking_details[0]

    assert detail.booking_id == booking.booking_id
    assert detail.account_number == "8400"
    assert detail.net_amount == Decimal("100.00")
    assert detail.tax_amount == Decimal("19.00")
    assert detail.tax_rate == 19

    assert booking.debit_total == Decimal("119.00")
    assert booking.credit_total == Decimal("119.00")
    assert gross_amount == Decimal("119.00")
    assert revenue_kind is VatRevenueKind.NORMAL
    assert payment_kind is VatPaymentKind.RECEIVABLE
    assert service_date == date.today()

    widget.deleteLater()

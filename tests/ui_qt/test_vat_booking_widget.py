"""Tests für die PySide6-Umsatzsteuerbuchung."""

from datetime import date

from PySide6.QtWidgets import QApplication, QLabel

from openbilanz.domain.vat_accounts import VatAccounts
from openbilanz.domain.vat_configuration import VatConfiguration
from openbilanz.domain.vat_taxation_type import VatTaxationType
from openbilanz.ui_qt.vat_booking_widget import VatBookingWidget

VAT_ACCOUNTS = VatAccounts(
    input_tax_7="1571",
    input_tax_19="1576",
    output_tax_7="1771",
    output_tax_19="1776",
)


def _application() -> QApplication:
    application = QApplication.instance()

    if application is None:
        application = QApplication([])

    return application


def test_standard_vat_configuration_keeps_tax_rate_enabled() -> None:
    """Regelbesteuerung startet mit auswählbaren 19 Prozent."""

    _application()

    configuration = VatConfiguration(
        taxation_type=VatTaxationType.STANDARD,
        effective_from=date(2026, 1, 1),
    )

    widget = VatBookingWidget(
        accounts=(),
        vat_accounts=VAT_ACCOUNTS,
        vat_configuration=configuration,
        on_booking_created=lambda _booking: None,
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

    configuration = VatConfiguration(
        taxation_type=VatTaxationType.SMALL_BUSINESS,
        effective_from=date(2026, 1, 1),
    )

    widget = VatBookingWidget(
        accounts=(),
        vat_accounts=VAT_ACCOUNTS,
        vat_configuration=configuration,
        on_booking_created=lambda _booking: None,
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

from unittest.mock import Mock

from PySide6.QtWidgets import QApplication

from simpleob.domain.vat_accounts import VatAccounts
from simpleob.ui_qt.vat_booking_frame import VatBookingFrame


def _frame() -> tuple[QApplication, VatBookingFrame, Mock]:
    app = QApplication.instance() or QApplication([])
    on_booking_created = Mock()
    frame = VatBookingFrame(
        accounts=(),
        vat_accounts=VatAccounts("1576", "1571", "1776", "1771"),
        on_booking_created=on_booking_created,
    )
    return app, frame, on_booking_created


def test_vat_rate_defaults_to_19_percent_and_is_remembered_by_invoice_type():
    app, frame, _on_booking_created = _frame()
    try:
        rate_box = frame._position_rows[0]["tax_rate_box"]
        assert rate_box.currentText() == "19 %"

        rate_box.setCurrentText("7 %")
        frame._clear()
        assert frame._position_rows[0]["tax_rate_box"].currentText() == "7 %"

        frame._invoice_type_box.setCurrentText("Ausgangsrechnung")
        app.processEvents()
        assert frame._position_rows[0]["tax_rate_box"].currentText() == "19 %"

        frame._position_rows[0]["tax_rate_box"].setCurrentText("0 %")
        frame._invoice_type_box.setCurrentText("Eingangsrechnung")
        app.processEvents()
        assert frame._position_rows[0]["tax_rate_box"].currentText() == "7 %"

        frame._invoice_type_box.setCurrentText("Ausgangsrechnung")
        app.processEvents()
        assert frame._position_rows[0]["tax_rate_box"].currentText() == "0 %"
    finally:
        frame.close()
        app.processEvents()


def test_invoice_number_button_fills_or_appends_without_duplicates_or_booking():
    app, frame, on_booking_created = _frame()
    try:
        frame._voucher_no_entry.setText("INV-2026-0042")
        frame._copy_invoice_number_button.click()
        assert frame._description_entry.text() == "INV-2026-0042"

        frame._description_entry.setText("Wartung März")
        frame._copy_invoice_number_button.click()
        assert frame._description_entry.text() == "Wartung März INV-2026-0042"

        frame._copy_invoice_number_button.click()
        assert frame._description_entry.text() == "Wartung März INV-2026-0042"
        on_booking_created.assert_not_called()
    finally:
        frame.close()
        app.processEvents()


def test_invoice_number_button_is_next_to_date_and_ignores_empty_number():
    app, frame, on_booking_created = _frame()
    try:
        frame.resize(900, 500)
        frame.show()
        app.processEvents()

        assert (
            frame._copy_invoice_number_button.geometry().left()
            > frame._booking_date_entry.geometry().right()
        )
        frame._description_entry.setText("Vorhandener Text")
        frame._voucher_no_entry.clear()
        frame._copy_invoice_number_button.click()
        assert frame._description_entry.text() == "Vorhandener Text"
        on_booking_created.assert_not_called()
    finally:
        frame.close()
        app.processEvents()

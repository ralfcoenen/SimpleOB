from dataclasses import replace
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLabel, QMessageBox, QPushButton

from simpleob.domain.booking_line import BookingLine
from simpleob.domain.entry_side import EntrySide
from simpleob.domain.fiscal_year import FiscalYear
from simpleob.domain.open_item_overview import (
    OpenItemActivity,
    OpenItemActivityKind,
    OpenItemKind,
    OpenItemOverviewDetail,
    OpenItemOverviewItem,
    OpenItemOverviewReport,
    OpenItemPartnerOption,
)
from simpleob.ui_qt.open_item_detail_dialog import OpenItemDetailDialog
from simpleob.ui_qt.open_item_overview_widget import OpenItemOverviewWidget


class _OverviewService:
    def __init__(self, report, details):
        self.report = report
        self.details = details
        self.list_calls = []
        self.detail_calls = []

    def list_items(self, *, company_id, include_settled=False):
        self.list_calls.append((company_id, include_settled))
        items = self.report.items
        if not include_settled:
            items = tuple(item for item in items if item.open_amount > 0)
        return OpenItemOverviewReport(
            company_id=company_id,
            partners=self.report.partners,
            items=items,
            include_settled=include_settled,
        )

    def get_detail(self, *, company_id, open_item_id):
        self.detail_calls.append((company_id, open_item_id))
        return self.details[open_item_id]


def _item(company_id, partner_id, name, kind, number, amount, open_amount):
    return OpenItemOverviewItem(
        company_id=company_id,
        partner_id=partner_id,
        partner_name=name,
        open_item_id=uuid4(),
        kind=kind,
        document_number=number,
        document_date=date(2026, 1, 2),
        booking_date=date(2026, 1, 3),
        due_date=date(2026, 2, 2) if "CREDIT" not in kind.value else None,
        original_amount=Decimal(amount),
        payments_amount=Decimal("10.00"),
        offsets_amount=Decimal("5.00"),
        open_amount=Decimal(open_amount),
        source_booking_id="booking-reference",
    )


def _environment():
    company_id = uuid4()
    dual_partner = uuid4()
    customer_partner = uuid4()
    supplier_partner = uuid4()
    items = (
        _item(company_id, dual_partner, "Dual", OpenItemKind.CUSTOMER_RECEIVABLE, "AR-OPEN", "119.00", "104.00"),
        _item(company_id, dual_partner, "Dual", OpenItemKind.CUSTOMER_CREDIT, "CC-SETTLED", "30.00", "0.00"),
        _item(company_id, dual_partner, "Dual", OpenItemKind.SUPPLIER_PAYABLE, "AP-OPEN", "50.00", "35.00"),
        _item(company_id, dual_partner, "Dual", OpenItemKind.SUPPLIER_CREDIT, "SC-SETTLED", "20.00", "0.00"),
        _item(company_id, customer_partner, "Customer", OpenItemKind.CUSTOMER_RECEIVABLE, "AR-SETTLED", "40.00", "0.00"),
        _item(company_id, customer_partner, "Customer", OpenItemKind.CUSTOMER_CREDIT, "CC-OPEN", "10.00", "10.00"),
        _item(company_id, supplier_partner, "Supplier", OpenItemKind.SUPPLIER_PAYABLE, "AP-SETTLED", "60.00", "0.00"),
        _item(company_id, supplier_partner, "Supplier", OpenItemKind.SUPPLIER_CREDIT, "SC-OPEN", "15.00", "15.00"),
    )
    details = {
        item.open_item_id: OpenItemOverviewDetail(
            item=item,
            activities=(
                OpenItemActivity(
                    kind=OpenItemActivityKind.ORIGINAL,
                    activity_date=item.document_date,
                    booking_date=item.booking_date,
                    amount=item.original_amount,
                    reference=item.document_number,
                    description="Ursprungsbeleg",
                    booking_id="booking-reference",
                ),
                OpenItemActivity(
                    kind=OpenItemActivityKind.PAYMENT,
                    activity_date=date(2026, 1, 5),
                    booking_date=date(2026, 1, 6),
                    amount=Decimal("10.00"),
                    reference="Kundenzahlung · Dual · Rechnung AR-OPEN",
                    description="Zahlungszuordnung",
                    payment_id="payment-id",
                    booking_id="payment-booking",
                    payment_total=Decimal("25.00"),
                ),
                OpenItemActivity(
                    kind=OpenItemActivityKind.OFFSET,
                    activity_date=date(2026, 1, 6),
                    booking_date=date(2026, 1, 6),
                    amount=Decimal("5.00"),
                    reference="Gutschriftenverrechnung · Gutschrift CN-1",
                    description="Dual: Rechnung AR-OPEN mit Gutschrift verrechnet",
                    booking_id="offset-booking",
                ),
                OpenItemActivity(
                    kind=OpenItemActivityKind.PAYMENT_CORRECTION,
                    activity_date=date(2026, 1, 7),
                    booking_date=date(2026, 1, 7),
                    amount=Decimal("-2.00"),
                    reference=(
                        "Zahlungszuordnungskorrektur · Dual · Rechnung AR-OPEN · "
                        "ursprüngliche Zahlung 05.01.2026"
                    ),
                    description="Zuordnung entlastet: Begründung",
                    payment_id="payment-id",
                ),
                OpenItemActivity(
                    kind=OpenItemActivityKind.INVOICE_CANCELLATION,
                    activity_date=date(2026, 1, 8),
                    booking_date=date(2026, 1, 8),
                    amount=Decimal("119.00"),
                    reference="Storno AR-OPEN",
                    description="Rechnungsstorno · Fehlerhafte Rechnung",
                    booking_id="reversal-booking",
                ),
            ),
        )
        for item in items
    }
    report = OpenItemOverviewReport(
        company_id=company_id,
        partners=(
            OpenItemPartnerOption(dual_partner, "Dual"),
            OpenItemPartnerOption(customer_partner, "Customer"),
            OpenItemPartnerOption(supplier_partner, "Supplier"),
        ),
        items=items,
        include_settled=True,
    )
    return company_id, items, _OverviewService(report, details)


def _shown_numbers(table):
    return {table.item(row, 2).text() for row in range(table.rowCount())}


def test_nine_combined_filter_states_apply_to_items_and_summaries():
    app = QApplication.instance() or QApplication([])
    company_id, items, service = _environment()
    widget = OpenItemOverviewWidget(company_id=company_id, service=service)

    assert len(widget.findChildren(QPushButton)) == 2
    assert widget._partner_type_filter.count() == 3
    assert widget._status_filter.count() == 3
    assert widget._views.tabText(0) == "Einzelposten"
    assert widget._views.tabText(1) == "Summen"
    assert not hasattr(widget, "_activity_table")
    assert service.list_calls == [(company_id, False)]

    for partner_type_index in range(3):
        for status_index in range(3):
            widget._partner_box.setCurrentIndex(0)
            widget._partner_type_filter.setCurrentIndex(partner_type_index)
            widget._status_filter.setCurrentIndex(status_index)
            if status_index == 0:
                expected = [item for item in items if item.open_amount > 0]
            elif status_index == 1:
                expected = [item for item in items if item.open_amount == 0]
            else:
                expected = list(items)
            if partner_type_index == 1:
                expected = [
                    item for item in expected
                    if item.kind in {
                        OpenItemKind.CUSTOMER_RECEIVABLE,
                        OpenItemKind.CUSTOMER_CREDIT,
                    }
                ]
            elif partner_type_index == 2:
                expected = [
                    item for item in expected
                    if item.kind in {
                        OpenItemKind.SUPPLIER_PAYABLE,
                        OpenItemKind.SUPPLIER_CREDIT,
                    }
                ]

            assert _shown_numbers(widget._items_table) == {
                item.document_number for item in expected
            }
            assert sum(
                int(widget._summary_table.item(row, 2).text())
                for row in range(widget._summary_table.rowCount())
            ) == len(expected)
            assert {
                widget._summary_table.item(row, 1).text()
                for row in range(widget._summary_table.rowCount())
            } == {item.kind.label for item in expected}

    # Dual-role partner's customer and supplier items appear in their respective filters.
    widget._partner_type_filter.setCurrentIndex(1)
    assert "AR-OPEN" in _shown_numbers(widget._items_table)
    assert "AP-OPEN" not in _shown_numbers(widget._items_table)
    widget._partner_type_filter.setCurrentIndex(2)
    assert "AP-OPEN" in _shown_numbers(widget._items_table)
    assert "AR-OPEN" not in _shown_numbers(widget._items_table)

    # The partner selector independently narrows both views.
    widget._partner_type_filter.setCurrentIndex(0)
    widget._status_filter.setCurrentIndex(0)
    partner_index = widget._partner_box.findText("Dual")
    widget._partner_box.setCurrentIndex(partner_index)
    assert _shown_numbers(widget._items_table) == {"AR-OPEN", "AP-OPEN"}
    assert sum(
        int(widget._summary_table.item(row, 2).text())
        for row in range(widget._summary_table.rowCount())
    ) == 2
    widget._views.setCurrentIndex(1)
    assert not widget._details_button.isEnabled()
    widget._views.setCurrentIndex(0)
    assert widget._details_button.isEnabled()
    widget.close()
    app.processEvents()


def test_detail_dialog_is_read_only_and_shows_existing_event_history(monkeypatch):
    app = QApplication.instance() or QApplication([])
    company_id, items, service = _environment()
    item = items[0]
    dialog = OpenItemDetailDialog(
        None, company_id=company_id, item=item, service=service
    )

    assert dialog.windowTitle() == "OP-Details · AR-OPEN"
    assert dialog._activity_table.rowCount() == 5
    displayed = " ".join(
        dialog._activity_table.item(row, column).text()
        for row in range(dialog._activity_table.rowCount())
        for column in range(6)
    )
    assert "Ursprungsbeleg" in displayed
    assert "Kundenzahlung" in displayed
    assert "Gesamtzahlung 25,00 EUR" in displayed
    assert "Verrechnung" in displayed
    assert "Gutschriftenverrechnung · Gutschrift CN-1" in displayed
    assert "5,00 €" in displayed
    assert "Korrektur der Zahlungszuordnung" in displayed
    assert "Rechnungsstorno" in displayed
    assert "payment-id" not in displayed
    assert "payment-booking" not in displayed
    assert "booking-reference" not in displayed
    assert service.detail_calls == [(company_id, item.open_item_id)]
    assert not hasattr(dialog, "_service_write_method")
    dialog.close()

    opened = []
    monkeypatch.setattr(
        "simpleob.ui_qt.open_item_overview_widget.OpenItemDetailDialog.exec",
        lambda instance: opened.append(instance.windowTitle()) or 0,
    )
    widget = OpenItemOverviewWidget(company_id=company_id, service=service)
    widget.show()
    widget._items_table.setFocus()
    app.processEvents()
    widget._items_table.cellDoubleClicked.emit(0, 0)
    QTest.keyClick(widget._items_table, Qt.Key.Key_Return)
    QTest.keyClick(widget._items_table, Qt.Key.Key_Enter)
    widget._details_button.click()
    assert opened == ["OP-Details · AR-OPEN"] * 4
    assert service.detail_calls[-4:] == [
        (company_id, item.open_item_id),
        (company_id, item.open_item_id),
        (company_id, item.open_item_id),
        (company_id, item.open_item_id),
    ]
    widget._items_table.clearSelection()
    widget._items_table.setCurrentCell(-1, -1)
    widget._update_action_availability()
    assert not widget._details_button.isEnabled()
    widget.close()
    app.processEvents()


def test_refund_amount_is_separate_from_offsets_in_summary_and_detail():
    app = QApplication.instance() or QApplication([])
    company_id, items, service = _environment()
    credit_item = next(
        item for item in items
        if item.kind is OpenItemKind.CUSTOMER_CREDIT and item.open_amount > 0
    )
    credit_item = replace(
        credit_item,
        offsets_amount=Decimal("5.00"),
        refunds_amount=Decimal("4.00"),
        open_amount=Decimal("1.00"),
    )
    service.report = replace(
        service.report,
        items=tuple(
            credit_item if item.open_item_id == credit_item.open_item_id else item
            for item in service.report.items
        ),
    )
    service.details[credit_item.open_item_id] = OpenItemOverviewDetail(
        item=credit_item,
        activities=(
            OpenItemActivity(
                kind=OpenItemActivityKind.REFUND,
                activity_date=date(2026, 4, 15),
                booking_date=date(2026, 4, 16),
                amount=Decimal("4.00"),
                reference="Auszahlung Kundenguthaben · Hauptbuch V-16",
                description="Tatsächliche Auszahlung 15.04.2026",
                booking_id="refund-booking-id",
            ),
        ),
    )

    widget = OpenItemOverviewWidget(company_id=company_id, service=service)
    summary_row = next(
        row for row in range(widget._summary_table.rowCount())
        if widget._summary_table.item(row, 1).text() == "Kundenguthaben"
    )
    assert widget._summary_table.horizontalHeaderItem(5).text() == "Verrechnet"
    assert widget._summary_table.horizontalHeaderItem(6).text() == "Rückerstattet"
    assert widget._summary_table.item(summary_row, 5).text() == "5,00"
    assert widget._summary_table.item(summary_row, 6).text() == "4,00"

    dialog = OpenItemDetailDialog(
        None, company_id=company_id, item=credit_item, service=service
    )
    labels = [label.text() for label in dialog.findChildren(QLabel)]
    assert "4,00 €" in labels
    assert dialog._activity_table.item(0, 0).text() == "Rückerstattung"
    assert dialog._activity_table.item(0, 2).text() == "16.04.2026"
    assert "Hauptbuch V-16" in dialog._activity_table.item(0, 4).text()
    dialog.close()
    widget.close()
    app.processEvents()


def test_context_menu_and_visible_actions_share_storno_eligibility(monkeypatch):
    app = QApplication.instance() or QApplication([])
    company_id, items, overview = _environment()
    receivable = items[0]

    class CancellationService:
        def __init__(self):
            self.preview_calls = []
            self.assessment_calls = []
            self.cancel_calls = []

        def preview(self, **kwargs):
            self.preview_calls.append(kwargs)
            return SimpleNamespace(
                partner_name="Dual",
                invoice_number="AR-OPEN",
                amount=Decimal("119.00"),
                original_booking=SimpleNamespace(
                    lines=(BookingLine("1200", EntrySide.DEBIT, Decimal("119.00")),)
                ),
            )

        def assess_payment_history(self, **kwargs):
            self.assessment_calls.append(kwargs)
            return SimpleNamespace(
                invoice_amount=Decimal("119.00"),
                effective_payment_amount=Decimal("15.00"),
                open_amount=Decimal("104.00"),
            )

        def cancel_invoice(self, **kwargs):
            self.cancel_calls.append(kwargs)
            overview.report = replace(
                overview.report,
                items=tuple(
                    replace(item, open_amount=Decimal("0.00"))
                    if item.open_item_id == receivable.open_item_id
                    else item
                    for item in overview.report.items
                ),
            )

    cancellation = CancellationService()
    answers = iter(("Rechnungsfehler",))
    confirmation_text = []
    monkeypatch.setattr(
        OpenItemOverviewWidget,
        "_request_cancellation_date",
        lambda self, default_date, fiscal_year_name: date(2026, 4, 15),
    )
    monkeypatch.setattr(
        "simpleob.ui_qt.open_item_overview_widget.QInputDialog.getText",
        lambda *args, **kwargs: (next(answers), True),
    )
    monkeypatch.setattr(
        "simpleob.ui_qt.open_item_overview_widget.QMessageBox.question",
        lambda *args, **kwargs: (
            confirmation_text.append(args[2])
            or QMessageBox.StandardButton.Yes
        ),
    )
    fiscal_year = FiscalYear(date(2026, 1, 1), date(2026, 12, 31))
    widget = OpenItemOverviewWidget(
        company_id=company_id,
        service=overview,
        cancellation_service=cancellation,
        fiscal_year=fiscal_year,
        on_cancelled=lambda: confirmation_text.append("refreshed main window"),
    )
    cancel_button = next(
        button for button in widget.findChildren(QPushButton)
        if button.text() == "Rechnung vollständig stornieren"
    )
    assert cancel_button.isEnabled()
    menu = widget._build_context_menu()
    assert menu.actions()[0].text() == "Details anzeigen"
    assert menu.actions()[1].text() == "Rechnung vollständig stornieren"
    assert menu.actions()[1].isEnabled()

    widget._status_filter.setCurrentIndex(2)
    credit_row = next(
        row for row in range(widget._items_table.rowCount())
        if widget._items_table.item(row, 2).text() == "CC-SETTLED"
    )
    widget._items_table.setCurrentCell(credit_row, 0)
    assert not cancel_button.isEnabled()
    assert not widget._build_context_menu().actions()[1].isEnabled()
    widget._items_table.setCurrentCell(0, 0)
    cancel_button.click()

    assert cancellation.preview_calls == [
        {
            "company_id": company_id,
            "fiscal_year": fiscal_year,
            "open_item_id": receivable.open_item_id,
        }
    ]
    assert cancellation.assessment_calls[0]["proposed_booking_date"] == date(2026, 4, 15)
    assert cancellation.cancel_calls[0]["booking_date"] == date(2026, 4, 15)
    assert cancellation.cancel_calls[0]["reason"] == "Rechnungsfehler"
    assert cancellation.cancel_calls[0]["confirmed"] is True
    assert "Haben" in confirmation_text[0]
    assert "keine Bank- oder Kassenbewegung" in confirmation_text[0]
    assert "refreshed main window" in confirmation_text
    assert overview.list_calls[-1] == (company_id, True)
    receivable_row = next(
        row for row in range(widget._items_table.rowCount())
        if widget._items_table.item(row, 2).text() == receivable.document_number
    )
    assert widget._items_table.item(receivable_row, 6).text() == "0,00"
    assert not cancel_button.isEnabled()
    assert not widget._build_context_menu().actions()[1].isEnabled()

    # Fully settled invoice OPs remain actionable; credit OPs do not.
    settled_invoice = next(item for item in items if item.document_number == "AR-SETTLED")
    settled_detail = overview.details[settled_invoice.open_item_id]
    overview.details[settled_invoice.open_item_id] = replace(
        settled_detail,
        activities=tuple(
            activity for activity in settled_detail.activities
            if activity.kind is not OpenItemActivityKind.INVOICE_CANCELLATION
        ),
    )
    widget._status_filter.setCurrentIndex(1)
    settled_invoice_row = next(
        row for row in range(widget._items_table.rowCount())
        if widget._items_table.item(row, 2).text() == "AR-SETTLED"
    )
    widget._items_table.setCurrentCell(settled_invoice_row, 0)
    assert cancel_button.isEnabled()
    assert widget._build_context_menu().actions()[1].isEnabled()
    settled_credit_row = next(
        row for row in range(widget._items_table.rowCount())
        if widget._items_table.item(row, 2).text() == "CC-SETTLED"
    )
    widget._items_table.setCurrentCell(settled_credit_row, 0)
    assert not cancel_button.isEnabled()
    assert not widget._build_context_menu().actions()[1].isEnabled()
    widget.close()
    app.processEvents()


@pytest.mark.parametrize("supplier", (False, True), ids=("customer", "supplier"))
@pytest.mark.parametrize(
    ("paid_amount", "open_amount", "status_index"),
    (
        (Decimal("0.00"), Decimal("119.00"), 0),
        (Decimal("40.00"), Decimal("79.00"), 0),
        (Decimal("119.00"), Decimal("0.00"), 1),
    ),
    ids=("unpaid", "partial", "fully-paid"),
)
def test_invoice_cancellation_confirmation_shows_payment_assessment(
    monkeypatch, supplier, paid_amount, open_amount, status_index
):
    app = QApplication.instance() or QApplication([])
    company_id, items, overview = _environment()
    invoice = items[2] if supplier else items[0]
    invoice = replace(
        invoice,
        original_amount=Decimal("119.00"),
        payments_amount=paid_amount,
        offsets_amount=Decimal("0.00"),
        open_amount=open_amount,
    )
    overview.report = replace(
        overview.report,
        items=tuple(
            invoice if item.open_item_id == invoice.open_item_id else item
            for item in overview.report.items
        ),
    )
    cancellation_activity = next(
        activity for activity in overview.details[invoice.open_item_id].activities
        if activity.kind is OpenItemActivityKind.INVOICE_CANCELLATION
    )
    overview.details[invoice.open_item_id] = replace(
        overview.details[invoice.open_item_id],
        activities=tuple(
            activity for activity in overview.details[invoice.open_item_id].activities
            if activity.kind is not OpenItemActivityKind.INVOICE_CANCELLATION
        ),
    )

    class CancellationService:
        def __init__(self):
            self.preview_calls = []
            self.assessment_calls = []
            self.cancel_calls = []

        def preview(self, **kwargs):
            self.preview_calls.append(kwargs)
            return SimpleNamespace(
                partner_name=invoice.partner_name,
                invoice_number=invoice.document_number,
                amount=Decimal("119.00"),
                original_booking=SimpleNamespace(
                    lines=(BookingLine("1200", EntrySide.DEBIT, Decimal("119.00")),)
                ),
            )

        def assess_payment_history(self, **kwargs):
            self.assessment_calls.append(kwargs)
            return SimpleNamespace(
                invoice_amount=Decimal("119.00"),
                effective_payment_amount=paid_amount,
                open_amount=open_amount,
            )

        def cancel_invoice(self, **kwargs):
            self.cancel_calls.append(kwargs)
            closed_invoice = replace(invoice, open_amount=Decimal("0.00"))
            items_after = tuple(
                closed_invoice if item.open_item_id == invoice.open_item_id else item
                for item in overview.report.items
            )
            if paid_amount > Decimal("0.00"):
                credit = _item(
                    company_id,
                    invoice.partner_id,
                    invoice.partner_name,
                    OpenItemKind.SUPPLIER_CREDIT if supplier else OpenItemKind.CUSTOMER_CREDIT,
                    f"Storno {invoice.document_number}",
                    str(paid_amount),
                    str(paid_amount),
                )
                credit = replace(
                    credit,
                    payments_amount=Decimal("0.00"),
                    offsets_amount=Decimal("0.00"),
                )
                items_after += (credit,)
            overview.report = replace(overview.report, items=items_after)
            overview.details[invoice.open_item_id] = replace(
                overview.details[invoice.open_item_id],
                activities=(
                    *overview.details[invoice.open_item_id].activities,
                    cancellation_activity,
                ),
            )

    cancellation = CancellationService()
    answers = iter(("Fehlerhafte Rechnung",))
    confirmation_text = []
    monkeypatch.setattr(
        OpenItemOverviewWidget,
        "_request_cancellation_date",
        lambda self, default_date, fiscal_year_name: date(2026, 4, 15),
    )
    monkeypatch.setattr(
        "simpleob.ui_qt.open_item_overview_widget.QInputDialog.getText",
        lambda *args, **kwargs: (next(answers), True),
    )
    monkeypatch.setattr(
        "simpleob.ui_qt.open_item_overview_widget.QMessageBox.question",
        lambda *args, **kwargs: (
            confirmation_text.append(args[2])
            or QMessageBox.StandardButton.Yes
        ),
    )
    fiscal_year = FiscalYear(date(2026, 1, 1), date(2026, 12, 31))
    widget = OpenItemOverviewWidget(
        company_id=company_id,
        service=overview,
        cancellation_service=cancellation,
        fiscal_year=fiscal_year,
    )
    if status_index:
        widget._status_filter.setCurrentIndex(status_index)
    row = next(
        index for index in range(widget._items_table.rowCount())
        if widget._items_table.item(index, 2).text() == invoice.document_number
    )
    widget._items_table.setCurrentCell(row, 0)
    cancel_button = next(
        button for button in widget.findChildren(QPushButton)
        if button.text() == "Rechnung vollständig stornieren"
    )
    assert cancel_button.isEnabled()
    assert widget._build_context_menu().actions()[1].isEnabled()
    cancel_button.click()

    assert cancellation.assessment_calls == [
        {
            "company_id": company_id,
            "fiscal_year": fiscal_year,
            "open_item_id": invoice.open_item_id,
            "proposed_booking_date": date(2026, 4, 15),
        }
    ]
    prompt = confirmation_text[0]
    assert "Ursprünglicher Rechnungsbetrag: 119,00 €" in prompt
    assert f"Wirksam bezahlt: {_german_money(paid_amount)} €" in prompt
    assert f"Noch offener Rechnungsbetrag: {_german_money(open_amount)} €" in prompt
    assert "Stornodatum: 15.04.2026" in prompt
    assert "Bereits erfolgte Zahlungen werden nicht rückgängig gemacht" in prompt
    assert "keine Bank- oder Kassenbewegung" in prompt
    if paid_amount > Decimal("0.00"):
        credit_label = "Lieferantenguthaben" if supplier else "Kundenguthaben"
        assert f"Entstehendes {credit_label}:" in prompt
        assert f"{_german_money(paid_amount)} €" in prompt
    else:
        assert "Es entsteht kein Partnerguthaben." in prompt
        assert "Entstehendes Kundenguthaben" not in prompt
        assert "Entstehendes Lieferantenguthaben" not in prompt
    assert cancellation.cancel_calls[0]["confirmed"] is True
    assert cancellation.cancel_calls[0]["booking_date"] == date(2026, 4, 15)
    widget._status_filter.setCurrentIndex(2)
    visible_numbers = _shown_numbers(widget._items_table)
    assert invoice.document_number in visible_numbers
    if paid_amount > Decimal("0.00"):
        assert f"Storno {invoice.document_number}" in visible_numbers
    widget.close()
    app.processEvents()


def _german_money(value):
    return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


@pytest.mark.parametrize(
    ("failure_stage", "message"),
    (
        ("preview", "Die Rechnung hat Verrechnungshistorie"),
        ("assessment", "Stornodatum liegt vor dem Zahlungsdatum"),
    ),
)
def test_invoice_cancellation_rejections_show_warning_without_confirmation(
    monkeypatch, failure_stage, message
):
    app = QApplication.instance() or QApplication([])
    company_id, items, overview = _environment()
    invoice = items[0]

    class CancellationService:
        def preview(self, **kwargs):
            if failure_stage == "preview":
                raise ValueError(message)
            return SimpleNamespace(
                partner_name=invoice.partner_name,
                invoice_number=invoice.document_number,
                amount=invoice.original_amount,
                original_booking=SimpleNamespace(
                    lines=(BookingLine("1200", EntrySide.DEBIT, Decimal("119.00")),)
                ),
            )

        def assess_payment_history(self, **kwargs):
            assert kwargs["proposed_booking_date"] == date(2026, 4, 15)
            raise ValueError(message)

        def cancel_invoice(self, **kwargs):
            raise AssertionError("Bei abgelehnter Prüfung darf nicht storniert werden.")

    answers = iter(("Fehlerhafte Rechnung",))
    warnings = []
    confirmations = []
    monkeypatch.setattr(
        OpenItemOverviewWidget,
        "_request_cancellation_date",
        lambda self, default_date, fiscal_year_name: date(2026, 4, 15),
    )
    monkeypatch.setattr(
        "simpleob.ui_qt.open_item_overview_widget.QInputDialog.getText",
        lambda *args, **kwargs: (next(answers), True),
    )
    monkeypatch.setattr(
        "simpleob.ui_qt.open_item_overview_widget.QMessageBox.warning",
        lambda *args, **kwargs: warnings.append(args[2]),
    )
    monkeypatch.setattr(
        "simpleob.ui_qt.open_item_overview_widget.QMessageBox.question",
        lambda *args, **kwargs: confirmations.append(args[2]),
    )
    widget = OpenItemOverviewWidget(
        company_id=company_id,
        service=overview,
        cancellation_service=CancellationService(),
        fiscal_year=FiscalYear(date(2026, 1, 1), date(2026, 12, 31)),
    )
    widget._items_table.setCurrentCell(0, 0)
    widget._cancel_invoice_button.click()
    assert warnings == [message]
    assert confirmations == []
    widget.close()
    app.processEvents()

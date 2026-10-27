from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

from PySide6.QtWidgets import QApplication, QMessageBox, QPushButton

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
from simpleob.ui_qt.open_item_overview_widget import OpenItemOverviewWidget


class _OverviewService:
    def __init__(self, report, details):
        self.report = report
        self.details = details
        self.list_calls = []
        self.detail_calls = []

    def list_items(self, *, company_id, include_settled=False):
        self.list_calls.append((company_id, include_settled))
        return OpenItemOverviewReport(
            company_id=company_id,
            partners=self.report.partners,
            items=(
                self.report.items
                if include_settled
                else tuple(item for item in self.report.items if item.open_amount > 0)
            ),
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


def test_widget_filters_partner_and_settled_items_and_shows_read_only_details():
    app = QApplication.instance() or QApplication([])
    company_id = uuid4()
    first_partner = uuid4()
    second_partner = uuid4()
    items = (
        _item(
            company_id,
            first_partner,
            "Alpha",
            OpenItemKind.CUSTOMER_RECEIVABLE,
            "AR-1",
            "119.00",
            "104.00",
        ),
        _item(
            company_id,
            first_partner,
            "Alpha",
            OpenItemKind.CUSTOMER_CREDIT,
            "CN-1",
            "30.00",
            "25.00",
        ),
        _item(
            company_id,
            second_partner,
            "Beta",
            OpenItemKind.SUPPLIER_PAYABLE,
            "AP-1",
            "50.00",
            "35.00",
        ),
        _item(
            company_id,
            second_partner,
            "Beta",
            OpenItemKind.SUPPLIER_CREDIT,
            "CN-2",
            "20.00",
            "15.00",
        ),
        _item(
            company_id,
            first_partner,
            "Alpha",
            OpenItemKind.CUSTOMER_RECEIVABLE,
            "AR-SETTLED",
            "20.00",
            "0.00",
        ),
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
                    description="Ursprungsrechnung",
                    booking_id="booking-reference",
                ),
                OpenItemActivity(
                    kind=OpenItemActivityKind.PAYMENT,
                    activity_date=date(2026, 1, 5),
                    booking_date=date(2026, 1, 6),
                    amount=Decimal("10.00"),
                    reference="Kundenzahlung · Alpha · Rechnung AR-1",
                    description="Zahlungszuordnung",
                    payment_id="payment-id",
                    booking_id="payment-booking",
                ),
                OpenItemActivity(
                    kind=OpenItemActivityKind.PAYMENT_CORRECTION,
                    activity_date=date(2026, 1, 7),
                    booking_date=date(2026, 1, 7),
                    amount=Decimal("-2.00"),
                    reference=(
                        "Zahlungszuordnungskorrektur · Alpha · Rechnung AR-1 · "
                        "ursprüngliche Zahlung 05.01.2026"
                    ),
                    description="Zuordnung entlastet: Begründung",
                    payment_id="payment-id",
                ),
            ),
        )
        for item in items
    }
    service = _OverviewService(
        OpenItemOverviewReport(
            company_id=company_id,
            partners=(
                OpenItemPartnerOption(first_partner, "Alpha"),
                OpenItemPartnerOption(second_partner, "Beta"),
            ),
            items=items,
            include_settled=False,
        ),
        details,
    )
    widget = OpenItemOverviewWidget(company_id=company_id, service=service)

    assert service.list_calls == [(company_id, False)]
    assert widget._items_table.rowCount() == 4
    assert widget._summary_table.rowCount() == 4
    assert widget._activity_table.rowCount() == 3
    assert widget._activity_table.item(2, 3).text() == "-2,00"
    assert "Alpha" in widget._activity_table.item(1, 4).text()
    assert "AR-1" in widget._activity_table.item(1, 4).text()
    assert widget._activity_table.item(1, 1).text() == "05.01.2026"
    assert widget._activity_table.item(1, 2).text() == "06.01.2026"
    assert widget._activity_table.item(1, 3).text() == "10,00"
    assert "05.01.2026" in widget._activity_table.item(2, 4).text()
    assert widget._activity_table.item(2, 1).text() == "07.01.2026"
    assert widget._activity_table.item(2, 2).text() == "07.01.2026"
    displayed_references = " ".join(
        widget._activity_table.item(row, 4).text()
        for row in range(widget._activity_table.rowCount())
    )
    assert "payment-id" not in displayed_references
    assert "payment-booking" not in displayed_references
    assert "booking-reference" not in displayed_references
    assert widget._items_table.horizontalHeaderItem(9).text() == "Offen"
    assert widget._summary_table.horizontalHeaderItem(1).text() == "OP-Art"
    assert len(widget.findChildren(QPushButton)) == 1
    assert widget._status_filter.count() == 3
    assert widget._status_filter.currentText() == "Nur offene Posten"

    widget._partner_box.setCurrentIndex(1)
    assert widget._items_table.rowCount() == 2
    assert all(
        widget._items_table.item(row, 0).text() == "Alpha"
        for row in range(widget._items_table.rowCount())
    )

    widget._status_filter.setCurrentIndex(1)
    assert service.list_calls[-1] == (company_id, True)
    assert widget._items_table.rowCount() == 1
    assert widget._summary_table.rowCount() == 1
    assert widget._summary_table.item(0, 2).text() == "1"
    assert widget._summary_table.item(0, 6).text() == "0,00"
    assert {
        widget._items_table.item(row, 2).text()
        for row in range(widget._items_table.rowCount())
    } == {"AR-SETTLED"}

    widget._status_filter.setCurrentIndex(2)
    assert service.list_calls[-1] == (company_id, True)
    assert widget._items_table.rowCount() == 3
    assert widget._summary_table.rowCount() == 2
    assert {
        widget._items_table.item(row, 2).text()
        for row in range(widget._items_table.rowCount())
    } == {"AR-1", "CN-1", "AR-SETTLED"}
    receivable_summary_row = next(
        row
        for row in range(widget._summary_table.rowCount())
        if widget._summary_table.item(row, 1).text() == "Kundenforderung"
    )
    assert widget._summary_table.item(receivable_summary_row, 2).text() == "2"
    assert widget._summary_table.item(receivable_summary_row, 6).text() == "104,00"

    widget._partner_box.setCurrentIndex(0)
    assert widget._items_table.rowCount() == 5
    assert widget._summary_table.rowCount() == 4
    assert all(call[0] == company_id for call in service.detail_calls)
    widget.close()
    app.processEvents()


def test_widget_exposes_explicit_invoice_cancellation_confirmation(monkeypatch):
    app = QApplication.instance() or QApplication([])
    company_id = uuid4()
    partner_id = uuid4()
    item = _item(
        company_id,
        partner_id,
        "Kunde",
        OpenItemKind.CUSTOMER_RECEIVABLE,
        "AR-1",
        "119.00",
        "119.00",
    )
    overview = _OverviewService(
        OpenItemOverviewReport(
            company_id=company_id,
            partners=(OpenItemPartnerOption(partner_id, "Kunde"),),
            items=(item,),
            include_settled=False,
        ),
        {
            item.open_item_id: OpenItemOverviewDetail(item=item, activities=()),
        },
    )

    class CancellationService:
        def __init__(self):
            self.preview_calls = []
            self.cancel_calls = []

        def preview(self, **kwargs):
            self.preview_calls.append(kwargs)
            return SimpleNamespace(
                partner_name="Kunde",
                invoice_number="AR-1",
                amount=Decimal("119.00"),
                original_booking=SimpleNamespace(
                    lines=(BookingLine("1200", EntrySide.DEBIT, Decimal("119.00")),)
                ),
            )

        def cancel_invoice(self, **kwargs):
            self.cancel_calls.append(kwargs)

    cancellation = CancellationService()
    text_answers = iter(("15.04.2026", "Rechnungsfehler"))
    confirmation_text = []
    monkeypatch.setattr(
        "simpleob.ui_qt.open_item_overview_widget.QInputDialog.getText",
        lambda *args, **kwargs: (next(text_answers), True),
    )
    monkeypatch.setattr(
        "simpleob.ui_qt.open_item_overview_widget.QMessageBox.question",
        lambda *args, **kwargs: (
            confirmation_text.append(args[2])
            or QMessageBox.StandardButton.Yes
        ),
    )
    widget = OpenItemOverviewWidget(
        company_id=company_id,
        service=overview,
        cancellation_service=cancellation,
        fiscal_year=FiscalYear(date(2026, 1, 1), date(2026, 12, 31)),
    )
    button = next(
        control for control in widget.findChildren(QPushButton)
        if control.text() == "Rechnung vollständig stornieren"
    )
    assert button.isEnabled()
    button.click()
    assert cancellation.preview_calls == [
        {"company_id": company_id, "fiscal_year": FiscalYear(date(2026, 1, 1), date(2026, 12, 31)), "open_item_id": item.open_item_id}
    ]
    assert cancellation.cancel_calls[0]["booking_date"] == date(2026, 4, 15)
    assert cancellation.cancel_calls[0]["reason"] == "Rechnungsfehler"
    assert cancellation.cancel_calls[0]["confirmed"] is True
    assert "Haben" in confirmation_text[0]
    assert "keine Bank- oder Kassenbewegung" in confirmation_text[0]
    widget.close()
    app.processEvents()

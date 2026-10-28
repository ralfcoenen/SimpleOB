"""Darstellung der lesenden OP-Abstimmung."""

from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

from PySide6.QtWidgets import QApplication, QPushButton

from simpleob.domain.open_item_reconciliation import (
    OpenItemReconciliationReport,
    OpenItemReconciliationRow,
    UnresolvedCorrectionTiming,
)
from simpleob.ui_qt.open_item_reconciliation_widget import OpenItemReconciliationWidget


class _ReconciliationService:
    def __init__(self):
        self.calls = []

    def reconcile(self, *, company_id, as_of_date):
        self.calls.append((company_id, as_of_date))
        row = OpenItemReconciliationRow(
            role="CUSTOMER_RECEIVABLES", role_label="Kundenforderungen",
            account_number="1200", account_name="Forderungen",
            ledger_balance=Decimal("10.00"), open_item_balance=Decimal("9.00"),
            difference=Decimal("1.00"), status="ZEITLICH_UNGEKLAERT",
            unresolved_correction_timings=(UnresolvedCorrectionTiming(
                correction_id="legacy-id", correction_date=date(2026, 4, 1),
                reason="Buchungsdatum unbekannt", amount=Decimal("1.00"),
                source_open_item_id="source-op", target_open_item_id="target-op",
            ),),
        )
        return OpenItemReconciliationReport(company_id, as_of_date, (row,))


def test_widget_shows_date_reconciliation_and_only_refresh_action():
    app = QApplication.instance() or QApplication([])
    company_id = uuid4()
    service = _ReconciliationService()
    widget = OpenItemReconciliationWidget(company_id=company_id, service=service)
    assert service.calls == [(company_id, date.today())]
    assert widget._table.item(0, 5).text() == "1,00"
    assert widget._table.item(0, 6).text() == "ZEITLICH_UNGEKLAERT"
    assert widget._uncertain_corrections.item(0, 2).text() == "Unbekannt (Altbestand)"
    assert widget._uncertain_corrections.item(0, 6).text() == "Buchungsdatum unbekannt"
    assert len(widget.findChildren(QPushButton)) == 1
    next_day = date.today() + timedelta(days=1)
    widget._date.set_date(next_day)
    widget.refresh()
    assert service.calls[-1] == (company_id, next_day)
    widget.close()
    app.processEvents()


def test_widget_rejects_invalid_stichtag_without_calling_service(monkeypatch):
    app = QApplication.instance() or QApplication([])
    service = _ReconciliationService()
    widget = OpenItemReconciliationWidget(company_id=uuid4(), service=service)
    calls = []
    monkeypatch.setattr(
        "simpleob.ui_qt.open_item_reconciliation_widget.QMessageBox.warning",
        lambda *_args: calls.append(_args[2]),
    )

    widget._date.setText("31.02.2026")
    widget.refresh()

    assert len(service.calls) == 1
    assert calls and "Ungültiges Datum" in calls[0]
    widget.close()
    app.processEvents()

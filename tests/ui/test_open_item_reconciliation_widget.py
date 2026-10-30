"""Darstellung der lesenden OP-Abstimmung."""

from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
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
        self.status = "ZEITLICH_UNGEKLAERT"
        self.report_date = None

    def reconcile(self, *, company_id, as_of_date):
        self.calls.append((company_id, as_of_date))
        row = OpenItemReconciliationRow(
            role="CUSTOMER_RECEIVABLES", role_label="Kundenforderungen",
            account_number="1200", account_name="Forderungen",
            ledger_balance=Decimal("10.00"), open_item_balance=Decimal("9.00"),
            difference=Decimal("1.00"), status=self.status,
            unresolved_correction_timings=(UnresolvedCorrectionTiming(
                correction_id="legacy-id", correction_date=date(2026, 4, 1),
                reason="Buchungsdatum unbekannt", amount=Decimal("1.00"),
                source_open_item_id="source-op", target_open_item_id="target-op",
            ),),
        )
        return OpenItemReconciliationReport(
            company_id, self.report_date or as_of_date, (row,)
        )


def test_widget_shows_date_reconciliation_and_only_refresh_action():
    app = QApplication.instance() or QApplication([])
    company_id = uuid4()
    service = _ReconciliationService()
    widget = OpenItemReconciliationWidget(company_id=company_id, service=service)
    assert service.calls == [(company_id, date.today())]
    assert widget._table.item(0, 5).text() == "1,00"
    assert widget._table.item(0, 6).text() == "Zeitlich ungeklärt"
    assert "kein Buchungsdatum" in widget._table.item(0, 6).toolTip()
    assert widget._result_label.text() == (
        f"Abstimmung zum Stichtag {date.today():%d.%m.%Y}: "
        "Prüfung erforderlich"
    )
    assert widget._uncertain_corrections.item(0, 2).text() == "Unbekannt (Altbestand)"
    assert widget._uncertain_corrections.item(0, 6).text() == "Buchungsdatum unbekannt"
    assert len(widget.findChildren(QPushButton)) == 1
    next_day = date.today() + timedelta(days=1)
    widget._date.set_date(next_day)
    widget.refresh()
    assert service.calls[-1] == (company_id, next_day)
    widget.close()
    app.processEvents()


def test_widget_displays_stichtag_from_returned_report_not_current_input():
    app = QApplication.instance() or QApplication([])
    company_id = uuid4()
    service = _ReconciliationService()
    service.report_date = date(2026, 4, 30)
    widget = OpenItemReconciliationWidget(company_id=company_id, service=service)

    assert service.calls == [(company_id, date.today())]
    assert widget._result_label.text() == (
        "Abstimmung zum Stichtag 30.04.2026: Prüfung erforderlich"
    )
    widget._date.set_date(date(2026, 5, 1))
    assert widget._result_label.text() == (
        "Abstimmung zum Stichtag 30.04.2026: Prüfung erforderlich"
    )
    widget.close()
    app.processEvents()


@pytest.mark.parametrize(
    ("status", "label", "help_fragment"),
    (
        ("ABGESTIMMT", "Abgestimmt", "stimmen für diesen Stichtag überein"),
        ("ABWEICHUNG", "Abweichung", "Ursache kann nicht automatisch bestimmt werden"),
        (
            "ZEITLICH_UNGEKLAERT",
            "Zeitlich ungeklärt",
            "kein Buchungsdatum",
        ),
        (
            "NICHT_KONFIGURIERT",
            "Nicht konfiguriert",
            "Kontenrollenzuordnung",
        ),
        ("KONTOFEHLER", "Kontofehler", "erwarteten Kontotyp"),
        (
            "OP_KONTO_UNERMITTELBAR",
            "OP-Konto nicht eindeutig",
            "nicht eindeutig ermittelt",
        ),
        (
            "UNGEKLAERTE_BEWEGUNG",
            "Ungeklärte Hauptbuchbewegung",
            "ohne bekannte OP-Zuordnung",
        ),
        (
            "KONTO_NICHT_MEHR_ZUGEORDNET",
            "Konto nicht mehr zugeordnet",
            "nicht mehr aktuell zugeordnet",
        ),
    ),
)
def test_widget_translates_reconciliation_statuses_without_changing_amounts(
    status, label, help_fragment
):
    app = QApplication.instance() or QApplication([])
    service = _ReconciliationService()
    service.status = status
    widget = OpenItemReconciliationWidget(company_id=uuid4(), service=service)

    assert widget._table.item(0, 5).text() == "1,00"
    assert widget._table.item(0, 6).text() == label
    assert help_fragment in widget._table.item(0, 6).toolTip()
    expected_result = (
        "Alle OP-Konten abgestimmt" if status == "ABGESTIMMT"
        else "Prüfung erforderlich"
    )
    assert expected_result in widget._result_label.text()
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

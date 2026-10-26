"""Lesende Oberfläche für die OP-Hauptbuch-Abstimmung."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QDateEdit,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from simpleob.services.open_item_reconciliation_service import (
    OpenItemReconciliationService,
)


class OpenItemReconciliationWidget(QWidget):
    """Zeigt Salden und nicht zugeordnete Sammelkonto-Bewegungen an."""

    def __init__(self, *, company_id: UUID, service: OpenItemReconciliationService) -> None:
        super().__init__()
        self._company_id = company_id
        self._service = service
        self._rows = ()
        self._date = QDateEdit()
        self._date.setCalendarPopup(True)
        self._date.setDisplayFormat("dd.MM.yyyy")
        self._date.setDate(QDate.currentDate())
        refresh = QPushButton("Aktualisieren")
        refresh.clicked.connect(self.refresh)
        controls = QHBoxLayout()
        controls.addWidget(QLabel("Stichtag"))
        controls.addWidget(self._date)
        controls.addWidget(refresh)
        controls.addStretch()
        self._table = QTableWidget(0, 7)
        self._table.setHorizontalHeaderLabels((
            "OP-Rolle", "Konto", "Bezeichnung", "Hauptbuchsaldo",
            "OP-Saldo", "Differenz", "Status",
        ))
        self._details = QTableWidget(0, 5)
        self._details.setHorizontalHeaderLabels((
            "Buchungsdatum", "Beleg", "Buchungstext", "Seite", "Betrag",
        ))
        self._uncertain_corrections = QTableWidget(0, 7)
        self._uncertain_corrections.setHorizontalHeaderLabels((
            "Korrektur-ID", "Korrekturdatum", "Buchungsdatum", "Betrag",
            "Quell-OP", "Ziel-OP", "Begründung",
        ))
        self._table.currentCellChanged.connect(self._show_movements)
        layout = QVBoxLayout(self)
        layout.addLayout(controls)
        layout.addWidget(self._table)
        layout.addWidget(QLabel("Nicht zugeordnete Hauptbuchbewegungen"))
        layout.addWidget(self._details)
        layout.addWidget(QLabel("Zeitlich ungeklärte historische Korrekturen"))
        layout.addWidget(self._uncertain_corrections)
        self.refresh()

    def refresh(self) -> None:
        qdate = self._date.date()
        report = self._service.reconcile(
            company_id=self._company_id,
            as_of_date=date(qdate.year(), qdate.month(), qdate.day()),
        )
        self._rows = report.rows
        self._table.setRowCount(len(self._rows))
        for row_index, row in enumerate(self._rows):
            values = (
                row.role_label, row.account_number or "—", row.account_name,
                _money(row.ledger_balance), _money(row.open_item_balance),
                _money(row.difference), row.status,
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                self._table.setItem(row_index, column, item)
            if row.status != "ABGESTIMMT":
                explanation = (
                    "Historische Zahlungszuordnungskorrektur ohne bekanntes "
                    "Buchungsdatum; der OP-Saldo ist zum Stichtag zeitlich ungeklärt."
                    if row.status == "ZEITLICH_UNGEKLAERT"
                    else "Abstimmungsdifferenz oder ungeklärte Bewegung prüfen."
                )
                for column in range(self._table.columnCount()):
                    self._table.item(row_index, column).setToolTip(explanation)
        if self._rows:
            self._table.selectRow(0)
        else:
            self._details.setRowCount(0)
            self._uncertain_corrections.setRowCount(0)

    def _show_movements(self, current_row: int, *_args: object) -> None:
        if current_row < 0 or current_row >= len(self._rows):
            self._details.setRowCount(0)
            self._uncertain_corrections.setRowCount(0)
            return
        movements = self._rows[current_row].unexplained_movements
        self._details.setRowCount(len(movements))
        for row_index, movement in enumerate(movements):
            values = (
                movement.booking_date.strftime("%d.%m.%Y"),
                movement.voucher_no or movement.booking_id,
                movement.description or "", movement.side, _money(movement.amount),
            )
            for column, value in enumerate(values):
                self._details.setItem(row_index, column, QTableWidgetItem(value))
        uncertainties = self._rows[current_row].unresolved_correction_timings
        self._uncertain_corrections.setRowCount(len(uncertainties))
        for row_index, correction in enumerate(uncertainties):
            values = (
                correction.correction_id,
                correction.correction_date.strftime("%d.%m.%Y"),
                "Unbekannt (Altbestand)",
                _money(correction.amount),
                correction.source_open_item_id,
                correction.target_open_item_id,
                correction.reason,
            )
            for column, value in enumerate(values):
                self._uncertain_corrections.setItem(
                    row_index, column, QTableWidgetItem(value)
                )


def _money(value: Decimal) -> str:
    return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

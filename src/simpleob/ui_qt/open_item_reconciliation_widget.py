"""Lesende Oberfläche für die OP-Hauptbuch-Abstimmung."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from simpleob.date_input import GermanDateEdit
from simpleob.services.open_item_reconciliation_service import (
    OpenItemReconciliationService,
)

_STATUS_LABELS = {
    "ABGESTIMMT": "Abgestimmt",
    "ABWEICHUNG": "Abweichung",
    "ZEITLICH_UNGEKLAERT": "Zeitlich ungeklärt",
    "NICHT_KONFIGURIERT": "Nicht konfiguriert",
    "KONTOFEHLER": "Kontofehler",
    "OP_KONTO_UNERMITTELBAR": "OP-Konto nicht eindeutig",
    "UNGEKLAERTE_BEWEGUNG": "Ungeklärte Hauptbuchbewegung",
    "KONTO_NICHT_MEHR_ZUGEORDNET": "Konto nicht mehr zugeordnet",
}

_STATUS_HELP = {
    "ABGESTIMMT": (
        "Hauptbuchsaldo und OP-Saldo stimmen für diesen Stichtag überein."
    ),
    "ABWEICHUNG": (
        "OP-Bestand und Hauptbuchsaldo stimmen nicht überein. Prüfen Sie die "
        "Buchungen auf dem zugeordneten Sammelkonto und die OP-Historie. "
        "Die Ursache kann nicht automatisch bestimmt werden."
    ),
    "ZEITLICH_UNGEKLAERT": (
        "Mindestens eine historische Zahlungszuordnungskorrektur hat kein "
        "Buchungsdatum. Ihre Wirkung kann deshalb diesem Stichtag nicht "
        "eindeutig zugeordnet werden. Einzelheiten stehen in der Tabelle "
        "„Zeitlich ungeklärte historische Korrekturen“."
    ),
    "NICHT_KONFIGURIERT": (
        "Für diese OP-Rolle ist kein Konto konfiguriert und es wurde auch aus "
        "den Ursprungsbuchungen kein Konto ermittelt. Prüfen Sie die "
        "Kontenrollenzuordnung."
    ),
    "KONTOFEHLER": (
        "Das zugeordnete oder aus der Ursprungsbuchung ermittelte Konto fehlt "
        "oder hat nicht den erwarteten Kontotyp. Prüfen Sie Konto und "
        "Kontenrollenzuordnung."
    ),
    "OP_KONTO_UNERMITTELBAR": (
        "Das OP-Sammelkonto konnte aus der Ursprungsbuchung nicht eindeutig "
        "ermittelt werden. Prüfen Sie deren Buchungszeilen und Kontenzuordnung."
    ),
    "UNGEKLAERTE_BEWEGUNG": (
        "Auf dem OP-Sammelkonto liegt mindestens eine Hauptbuchbewegung ohne "
        "bekannte OP-Zuordnung. Prüfen Sie die unten aufgeführten Buchungen "
        "und die OP-Historie."
    ),
    "KONTO_NICHT_MEHR_ZUGEORDNET": (
        "Dieses Konto wurde für OPs dieser Rolle verwendet, ist der Rolle "
        "aber nicht mehr aktuell zugeordnet. Prüfen Sie die Kontenrolle und "
        "die historischen Buchungen."
    ),
}


class OpenItemReconciliationWidget(QWidget):
    """Zeigt Salden und nicht zugeordnete Sammelkonto-Bewegungen an."""

    def __init__(self, *, company_id: UUID, service: OpenItemReconciliationService) -> None:
        super().__init__()
        self._company_id = company_id
        self._service = service
        self._rows = ()
        self._date = GermanDateEdit(value=date.today())
        refresh = QPushButton("Aktualisieren")
        refresh.clicked.connect(self.refresh)
        controls = QHBoxLayout()
        controls.addWidget(QLabel("Stichtag"))
        controls.addWidget(self._date)
        controls.addWidget(refresh)
        controls.addStretch()
        self._result_label = QLabel("Noch keine Abstimmung ausgeführt.")
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
        layout.addWidget(self._result_label)
        layout.addWidget(self._table)
        layout.addWidget(QLabel("Nicht zugeordnete Hauptbuchbewegungen"))
        layout.addWidget(self._details)
        layout.addWidget(QLabel("Zeitlich ungeklärte historische Korrekturen"))
        layout.addWidget(self._uncertain_corrections)
        self.refresh()

    def refresh(self) -> None:
        try:
            as_of_date = self._date.date_value()
        except ValueError as exc:
            QMessageBox.warning(self, "Ungültiger Stichtag", str(exc))
            return
        if as_of_date is None:
            QMessageBox.warning(
                self,
                "Ungültiger Stichtag",
                "Bitte geben Sie einen Stichtag ein.",
            )
            return
        report = self._service.reconcile(
            company_id=self._company_id,
            as_of_date=as_of_date,
        )
        self._rows = report.rows
        if not self._rows:
            result_text = "Keine Abstimmungsergebnisse"
        elif all(row.status == "ABGESTIMMT" for row in self._rows):
            result_text = "Alle OP-Konten abgestimmt"
        else:
            result_text = "Prüfung erforderlich"
        self._result_label.setText(
            f"Abstimmung zum Stichtag "
            f"{report.as_of_date.strftime('%d.%m.%Y')}: {result_text}"
        )
        self._table.setRowCount(len(self._rows))
        for row_index, row in enumerate(self._rows):
            values = (
                row.role_label, row.account_number or "—", row.account_name,
                _money(row.ledger_balance), _money(row.open_item_balance),
                _money(row.difference),
                _STATUS_LABELS.get(row.status, row.status),
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                self._table.setItem(row_index, column, item)
            explanation = _STATUS_HELP.get(
                row.status,
                f"Unbekannter Abstimmungsstatus: {row.status}",
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

"""Rein lesender Dialog mit OP-Stammdaten und Ereignishistorie."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from simpleob.domain.open_item_overview import OpenItemOverviewItem
from simpleob.services.open_item_overview_service import OpenItemOverviewService


class OpenItemDetailDialog(QDialog):
    """Zeigt den aktuellen OP und dessen vorhandene Ereignisse ohne Schreibweg."""

    def __init__(
        self,
        parent,
        *,
        company_id: UUID,
        item: OpenItemOverviewItem,
        service: OpenItemOverviewService,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"OP-Details · {item.document_number}")
        self.setMinimumSize(700, 420)
        self.resize(900, 600)

        detail = service.get_detail(
            company_id=company_id,
            open_item_id=item.open_item_id,
        )
        self._detail = detail
        displayed_item = detail.item if detail is not None else item

        form = QFormLayout()
        form.addRow("Geschäftspartner", QLabel(displayed_item.partner_name))
        form.addRow("OP-Art", QLabel(displayed_item.kind.label))
        form.addRow("Rechnung/Gutschrift", QLabel(displayed_item.document_number))
        form.addRow("Belegdatum", QLabel(_date(displayed_item.document_date)))
        form.addRow("Buchungsdatum", QLabel(_date(displayed_item.booking_date)))
        if displayed_item.due_date is not None:
            form.addRow("Fälligkeit", QLabel(_date(displayed_item.due_date)))
        form.addRow("Ursprungsbetrag", QLabel(f"{_money(displayed_item.original_amount)} €"))
        form.addRow("Zahlungen netto", QLabel(f"{_money(displayed_item.payments_amount)} €"))
        form.addRow("Verrechnet", QLabel(f"{_money(displayed_item.offsets_amount)} €"))
        form.addRow("Rückerstattet", QLabel(f"{_money(displayed_item.refunds_amount)} €"))
        form.addRow("Aktuell offen", QLabel(f"{_money(displayed_item.open_amount)} €"))

        self._activity_table = QTableWidget(0, 6)
        self._activity_table.setHorizontalHeaderLabels(
            (
                "Ereignis",
                "Vorgangsdatum",
                "Buchungsdatum",
                "Betrag",
                "Referenz",
                "Hinweis",
            )
        )
        self._activity_table.verticalHeader().setVisible(False)
        self._activity_table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        self._activity_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self._activity_table.setWordWrap(False)
        self._activity_table.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        header = self._activity_table.horizontalHeader()
        header.setMinimumSectionSize(90)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Interactive)
        header.resizeSection(4, 240)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        activities = detail.activities if detail is not None else ()
        self._activity_table.setRowCount(len(activities))
        for row, activity in enumerate(activities):
            values = (
                activity.kind.label,
                _date(activity.activity_date),
                _date(activity.booking_date),
                f"{_money(activity.amount)} €",
                _reference_text(activity),
                activity.description,
            )
            for column, value in enumerate(values):
                cell = QTableWidgetItem(value)
                cell.setToolTip(value)
                self._activity_table.setItem(row, column, cell)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        buttons.clicked.connect(self.accept)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self._activity_table, 1)
        layout.addWidget(buttons)


def _money(value: Decimal) -> str:
    return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _date(value: date | None) -> str:
    return value.strftime("%d.%m.%Y") if value is not None else "—"


def _reference_text(activity) -> str:
    parts = [activity.reference]
    if activity.payment_total is not None:
        parts.append(f"Gesamtzahlung {_money(activity.payment_total)} EUR")
    return " · ".join(parts)

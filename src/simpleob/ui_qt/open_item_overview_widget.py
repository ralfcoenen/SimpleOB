"""Lesende aktuelle Übersicht über offene Rechnungs- und Guthaben-OPs."""

from collections import defaultdict
from datetime import date
from decimal import Decimal
from uuid import UUID

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from simpleob.domain.open_item_overview import (
    OpenItemKind,
    OpenItemOverviewItem,
)
from simpleob.services.open_item_overview_service import OpenItemOverviewService

_OPEN_ITEMS = "open"
_SETTLED_ITEMS = "settled"
_ALL_ITEMS = "all"


class OpenItemOverviewWidget(QWidget):
    """Zeigt OP-Summen je Partner/Art und zugehörige Einzelposten."""

    def __init__(
        self,
        *,
        company_id: UUID,
        service: OpenItemOverviewService,
    ) -> None:
        super().__init__()
        self._company_id = company_id
        self._service = service
        self._items: tuple[OpenItemOverviewItem, ...] = ()

        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                "Aktuelle OP-Situation – keine historische "
                "Stichtagsauswertung."
            )
        )

        controls = QHBoxLayout()
        self._partner_box = QComboBox()
        self._partner_box.addItem("Alle Geschäftspartner", None)
        self._status_filter = QComboBox()
        self._status_filter.addItem("Nur offene Posten", _OPEN_ITEMS)
        self._status_filter.addItem(
            "Nur vollständig ausgeglichene Posten", _SETTLED_ITEMS
        )
        self._status_filter.addItem("Alle Posten", _ALL_ITEMS)
        self._refresh_button = QPushButton("Aktualisieren")
        controls.addWidget(QLabel("Geschäftspartner"))
        controls.addWidget(self._partner_box, 1)
        controls.addWidget(QLabel("Postenstatus"))
        controls.addWidget(self._status_filter)
        controls.addWidget(self._refresh_button)
        layout.addLayout(controls)

        layout.addWidget(QLabel("Summen je Geschäftspartner und OP-Art"))
        self._summary_table = QTableWidget(0, 7)
        self._summary_table.setHorizontalHeaderLabels(
            (
                "Geschäftspartner",
                "OP-Art",
                "Posten",
                "Ursprung",
                "Zahlungen netto",
                "Verrechnet",
                "Offen",
            )
        )
        self._summary_table.verticalHeader().setVisible(False)
        self._summary_table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        self._summary_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self._summary_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        layout.addWidget(self._summary_table)

        layout.addWidget(QLabel("Einzelposten"))
        self._items_table = QTableWidget(0, 10)
        self._items_table.setHorizontalHeaderLabels(
            (
                "Geschäftspartner",
                "OP-Art",
                "Rechnungs-/Gutschriftnummer",
                "Belegdatum",
                "Buchungsdatum",
                "Fälligkeit",
                "Ursprung",
                "Zahlungen netto",
                "Verrechnet",
                "Offen",
            )
        )
        self._items_table.verticalHeader().setVisible(False)
        self._items_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._items_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self._items_table.setSelectionMode(
            QTableWidget.SelectionMode.SingleSelection
        )
        self._items_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        self._items_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        self._items_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch
        )
        layout.addWidget(self._items_table)

        layout.addWidget(QLabel("Ereignisse des ausgewählten Postens"))
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
        self._activity_table.horizontalHeader().setSectionResizeMode(
            4, QHeaderView.ResizeMode.Stretch
        )
        self._activity_table.horizontalHeader().setSectionResizeMode(
            5, QHeaderView.ResizeMode.Stretch
        )
        layout.addWidget(self._activity_table)

        self._partner_box.currentIndexChanged.connect(self._render)
        self._status_filter.currentIndexChanged.connect(self.refresh)
        self._refresh_button.clicked.connect(self.refresh)
        self._items_table.currentCellChanged.connect(self._show_detail)
        self.refresh()

    def refresh(self, *_args: object) -> None:
        """Lädt den aktuellen Mandantenbestand erneut, ohne Änderungen."""

        selected_partner = self._partner_box.currentData()
        report = self._service.list_items(
            company_id=self._company_id,
            include_settled=(
                self._status_filter.currentData() != _OPEN_ITEMS
            ),
        )
        self._partner_box.blockSignals(True)
        self._partner_box.clear()
        self._partner_box.addItem("Alle Geschäftspartner", None)
        for partner in report.partners:
            self._partner_box.addItem(partner.name, str(partner.partner_id))
        if selected_partner is not None:
            selected_index = self._partner_box.findData(selected_partner)
            if selected_index >= 0:
                self._partner_box.setCurrentIndex(selected_index)
        self._partner_box.blockSignals(False)
        self._items = report.items
        self._render()

    def _visible_items(self) -> tuple[OpenItemOverviewItem, ...]:
        status_filter = self._status_filter.currentData()
        if status_filter == _OPEN_ITEMS:
            items = tuple(
                item
                for item in self._items
                if item.open_amount > Decimal("0.00")
            )
        elif status_filter == _SETTLED_ITEMS:
            items = tuple(
                item
                for item in self._items
                if item.open_amount == Decimal("0.00")
            )
        else:
            items = self._items
        selected_partner = self._partner_box.currentData()
        if selected_partner is None:
            return items
        selected_id = UUID(str(selected_partner))
        return tuple(item for item in items if item.partner_id == selected_id)

    def _render(self, *_args: object) -> None:
        items = self._visible_items()
        self._render_summaries(items)
        self._items_table.blockSignals(True)
        self._items_table.setRowCount(len(items))
        for row_index, item in enumerate(items):
            values = (
                item.partner_name,
                item.kind.label,
                item.document_number,
                _date(item.document_date),
                _date(item.booking_date),
                _date(item.due_date),
                _money(item.original_amount),
                _money(item.payments_amount),
                _money(item.offsets_amount),
                _money(item.open_amount),
            )
            for column, value in enumerate(values):
                cell = QTableWidgetItem(value)
                if column == 0:
                    cell.setData(Qt.ItemDataRole.UserRole, str(item.open_item_id))
                self._items_table.setItem(row_index, column, cell)
        self._activity_table.setRowCount(0)
        if items:
            self._items_table.setCurrentCell(0, 0)
        else:
            self._items_table.clearSelection()
            self._items_table.setCurrentCell(-1, -1)
        self._items_table.blockSignals(False)
        if items:
            self._show_detail(0, 0, -1, -1)

    def _render_summaries(
        self,
        items: tuple[OpenItemOverviewItem, ...],
    ) -> None:
        grouped: dict[
            tuple[UUID, OpenItemKind], list[OpenItemOverviewItem]
        ] = defaultdict(list)
        for item in items:
            grouped[(item.partner_id, item.kind)].append(item)
        summary_rows = sorted(
            grouped.values(),
            key=lambda group: (group[0].partner_name.casefold(), group[0].kind.value),
        )
        self._summary_table.setRowCount(len(summary_rows))
        for row_index, group in enumerate(summary_rows):
            first = group[0]
            values = (
                first.partner_name,
                first.kind.label,
                str(len(group)),
                _money(_sum(item.original_amount for item in group)),
                _money(_sum(item.payments_amount for item in group)),
                _money(_sum(item.offsets_amount for item in group)),
                _money(_sum(item.open_amount for item in group)),
            )
            for column, value in enumerate(values):
                self._summary_table.setItem(
                    row_index,
                    column,
                    QTableWidgetItem(value),
                )

    def _show_detail(
        self,
        current_row: int,
        _current_column: int,
        _previous_row: int,
        _previous_column: int,
    ) -> None:
        visible_items = self._visible_items()
        if current_row < 0 or current_row >= len(visible_items):
            self._activity_table.setRowCount(0)
            return
        detail = self._service.get_detail(
            company_id=self._company_id,
            open_item_id=visible_items[current_row].open_item_id,
        )
        activities = detail.activities if detail is not None else ()
        self._activity_table.setRowCount(len(activities))
        for row_index, activity in enumerate(activities):
            values = (
                activity.kind.label,
                _date(activity.activity_date),
                _date(activity.booking_date),
                _money(activity.amount),
                _reference_text(activity),
                activity.description,
            )
            for column, value in enumerate(values):
                self._activity_table.setItem(
                    row_index,
                    column,
                    QTableWidgetItem(value),
                )


def _sum(values) -> Decimal:
    return sum(values, start=Decimal("0.00"))


def _money(value: Decimal) -> str:
    return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _date(value: date | None) -> str:
    return value.strftime("%d.%m.%Y") if value is not None else "—"


def _reference_text(activity) -> str:
    parts = [activity.reference]
    if activity.payment_total is not None:
        parts.append(f"Gesamtzahlung {_money(activity.payment_total)} EUR")
    return " · ".join(parts)

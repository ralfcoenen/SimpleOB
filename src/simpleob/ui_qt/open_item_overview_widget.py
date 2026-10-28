"""Kompakte aktuelle OP-Übersicht mit lesenden Einzelpostendetails."""

from collections import defaultdict
from datetime import date
from decimal import Decimal
from uuid import UUID

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QAction, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QMenu,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from simpleob.date_input import parse_german_date
from simpleob.domain.fiscal_year import FiscalYear
from simpleob.domain.open_item_overview import (
    OpenItemActivityKind,
    OpenItemKind,
    OpenItemOverviewItem,
)
from simpleob.services.open_item_invoice_cancellation_service import (
    OpenItemInvoiceCancellationService,
)
from simpleob.services.open_item_overview_service import OpenItemOverviewService
from simpleob.ui_qt.open_item_detail_dialog import OpenItemDetailDialog

_OPEN_ITEMS = "open"
_SETTLED_ITEMS = "settled"
_ALL_ITEMS = "all"
_ALL_PARTNER_TYPES = "all"
_CUSTOMERS = "customers"
_SUPPLIERS = "suppliers"
_INVOICE_KINDS = {
    OpenItemKind.CUSTOMER_RECEIVABLE,
    OpenItemKind.SUPPLIER_PAYABLE,
}
_CUSTOMER_KINDS = {
    OpenItemKind.CUSTOMER_RECEIVABLE,
    OpenItemKind.CUSTOMER_CREDIT,
}
_SUPPLIER_KINDS = {
    OpenItemKind.SUPPLIER_PAYABLE,
    OpenItemKind.SUPPLIER_CREDIT,
}


class OpenItemOverviewWidget(QWidget):
    """Zeigt gefilterte OP-Einzelposten oder Summen je Partner und OP-Art."""

    def __init__(
        self,
        *,
        company_id: UUID,
        service: OpenItemOverviewService,
        cancellation_service: OpenItemInvoiceCancellationService | None = None,
        fiscal_year: FiscalYear | None = None,
        on_cancelled=None,
    ) -> None:
        super().__init__()
        self._company_id = company_id
        self._service = service
        self._cancellation_service = cancellation_service
        self._fiscal_year = fiscal_year
        self._on_cancelled = on_cancelled
        self._items: tuple[OpenItemOverviewItem, ...] = ()

        layout = QVBoxLayout(self)
        self._current_status = QLabel(
            "Aktuelle OP-Situation · keine historische Stichtagsauswertung"
        )
        layout.addWidget(self._current_status)

        controls = QHBoxLayout()
        self._partner_type_filter = QComboBox()
        self._partner_type_filter.addItem("Alle", _ALL_PARTNER_TYPES)
        self._partner_type_filter.addItem("Kunden", _CUSTOMERS)
        self._partner_type_filter.addItem("Lieferanten", _SUPPLIERS)
        self._status_filter = QComboBox()
        self._status_filter.addItem("Nur offene Posten", _OPEN_ITEMS)
        self._status_filter.addItem(
            "Nur vollständig ausgeglichene Posten", _SETTLED_ITEMS
        )
        self._status_filter.addItem("Alle Posten", _ALL_ITEMS)
        self._partner_box = QComboBox()
        self._partner_box.addItem("Alle Geschäftspartner", None)
        self._refresh_button = QPushButton("Aktualisieren")
        controls.addWidget(QLabel("Art"))
        controls.addWidget(self._partner_type_filter)
        controls.addWidget(self._status_filter)
        controls.addWidget(self._partner_box, 1)
        controls.addWidget(self._refresh_button)
        layout.addLayout(controls)

        self._views = QTabWidget()
        self._items_table = QTableWidget(0, 7)
        self._items_table.setHorizontalHeaderLabels(
            (
                "Geschäftspartner",
                "OP-Art",
                "Rechnung/Gutschrift",
                "Belegdatum",
                "Fälligkeit",
                "Ursprung",
                "Offen",
            )
        )
        self._items_table.verticalHeader().setVisible(False)
        self._items_table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        self._items_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self._items_table.setSelectionMode(
            QTableWidget.SelectionMode.SingleSelection
        )
        header = self._items_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        self._items_table.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )
        self._views.addTab(self._items_table, "Einzelposten")

        self._summary_table = QTableWidget(0, 8)
        self._summary_table.setHorizontalHeaderLabels(
            (
                "Geschäftspartner",
                "OP-Art",
                "Posten",
                "Ursprung",
                "Zahlungen netto",
                "Verrechnet",
                "Rückerstattet",
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
        self._views.addTab(self._summary_table, "Summen")
        layout.addWidget(self._views, 1)

        actions = QHBoxLayout()
        actions.addStretch()
        self._details_button = QPushButton("Details")
        self._details_button.setEnabled(False)
        self._details_button.clicked.connect(self._show_selected_detail)
        actions.addWidget(self._details_button)
        self._cancel_invoice_button: QPushButton | None = None
        if cancellation_service is not None:
            self._cancel_invoice_button = QPushButton(
                "Rechnung vollständig stornieren"
            )
            self._cancel_invoice_button.setEnabled(False)
            self._cancel_invoice_button.clicked.connect(
                self._cancel_selected_invoice
            )
            actions.addWidget(self._cancel_invoice_button)
        layout.addLayout(actions)

        self._partner_type_filter.currentIndexChanged.connect(self._render)
        self._partner_box.currentIndexChanged.connect(self._render)
        self._status_filter.currentIndexChanged.connect(self.refresh)
        self._refresh_button.clicked.connect(self.refresh)
        self._items_table.currentCellChanged.connect(
            self._update_action_availability
        )
        self._items_table.cellDoubleClicked.connect(
            self._show_selected_detail
        )
        self._items_table.customContextMenuRequested.connect(
            self._show_context_menu
        )
        self._views.currentChanged.connect(self._update_action_availability)
        self._return_shortcut = QShortcut(
            QKeySequence(Qt.Key.Key_Return), self._items_table
        )
        self._return_shortcut.activated.connect(self._show_selected_detail)
        self._enter_shortcut = QShortcut(
            QKeySequence(Qt.Key.Key_Enter), self._items_table
        )
        self._enter_shortcut.activated.connect(self._show_selected_detail)
        self.refresh()

    def refresh(self, *_args: object) -> None:
        """Lädt die aktuellen OPs und erhält eine weiterhin sichtbare Auswahl."""

        selected_item_id = self._selected_item_id()
        selected_partner = self._partner_box.currentData()
        report = self._service.list_items(
            company_id=self._company_id,
            include_settled=(
                self._status_filter.currentData() != _OPEN_ITEMS
            ),
        )
        self._items = report.items
        self._rebuild_partner_choices(selected_partner)
        self._render(preferred_item_id=selected_item_id)

    def _rebuild_partner_choices(self, selected_partner: object) -> None:
        candidates = self._items_after_type_and_status()
        partner_names = {
            item.partner_id: item.partner_name for item in candidates
        }
        self._partner_box.blockSignals(True)
        self._partner_box.clear()
        self._partner_box.addItem("Alle Geschäftspartner", None)
        for partner_id, name in sorted(
            partner_names.items(), key=lambda pair: pair[1].casefold()
        ):
            self._partner_box.addItem(name, str(partner_id))
        selected_index = (
            self._partner_box.findData(selected_partner)
            if selected_partner is not None
            else 0
        )
        self._partner_box.setCurrentIndex(
            selected_index if selected_index >= 0 else 0
        )
        self._partner_box.blockSignals(False)

    def _items_after_type_and_status(
        self,
    ) -> tuple[OpenItemOverviewItem, ...]:
        partner_type = self._partner_type_filter.currentData()
        status = self._status_filter.currentData()
        items = self._items
        if status == _OPEN_ITEMS:
            items = tuple(item for item in items if item.open_amount > Decimal("0.00"))
        elif status == _SETTLED_ITEMS:
            items = tuple(item for item in items if item.open_amount == Decimal("0.00"))
        if partner_type == _CUSTOMERS:
            items = tuple(item for item in items if item.kind in _CUSTOMER_KINDS)
        elif partner_type == _SUPPLIERS:
            items = tuple(item for item in items if item.kind in _SUPPLIER_KINDS)
        return items

    def _visible_items(self) -> tuple[OpenItemOverviewItem, ...]:
        items = self._items_after_type_and_status()
        selected_partner = self._partner_box.currentData()
        if selected_partner is None:
            return items
        selected_id = UUID(str(selected_partner))
        return tuple(item for item in items if item.partner_id == selected_id)

    def _render(
        self,
        *_args: object,
        preferred_item_id: UUID | None = None,
    ) -> None:
        if preferred_item_id is None:
            preferred_item_id = self._selected_item_id()
        self._rebuild_partner_choices(self._partner_box.currentData())
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
                _date(item.due_date),
                _money(item.original_amount),
                _money(item.open_amount),
            )
            for column, value in enumerate(values):
                cell = QTableWidgetItem(value)
                if column == 0:
                    cell.setData(Qt.ItemDataRole.UserRole, str(item.open_item_id))
                self._items_table.setItem(row_index, column, cell)
        selected_row = next(
            (
                index
                for index, item in enumerate(items)
                if item.open_item_id == preferred_item_id
            ),
            0 if items else -1,
        )
        if selected_row >= 0:
            self._items_table.setCurrentCell(selected_row, 0)
        else:
            self._items_table.clearSelection()
            self._items_table.setCurrentCell(-1, -1)
        self._items_table.blockSignals(False)
        self._update_action_availability()

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
            key=lambda group: (
                group[0].partner_name.casefold(), group[0].kind.value
            ),
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
                _money(_sum(item.refunds_amount for item in group)),
                _money(_sum(item.open_amount for item in group)),
            )
            for column, value in enumerate(values):
                self._summary_table.setItem(
                    row_index, column, QTableWidgetItem(value)
                )

    def _selected_item_id(self) -> UUID | None:
        row = self._items_table.currentRow()
        if row < 0:
            return None
        cell = self._items_table.item(row, 0)
        if cell is None:
            return None
        value = cell.data(Qt.ItemDataRole.UserRole)
        return UUID(str(value)) if value else None

    def _selected_item(self) -> OpenItemOverviewItem | None:
        if self._views.currentWidget() is not self._items_table:
            return None
        item_id = self._selected_item_id()
        return next(
            (item for item in self._visible_items() if item.open_item_id == item_id),
            None,
        )

    def _can_cancel_selected_invoice(self) -> bool:
        item = self._selected_item()
        if (
            self._cancellation_service is None
            or self._fiscal_year is None
            or item is None
            or item.kind not in _INVOICE_KINDS
        ):
            return False
        if item.open_amount > Decimal("0.00"):
            return True
        detail = self._service.get_detail(
            company_id=self._company_id,
            open_item_id=item.open_item_id,
        )
        return bool(
            detail is not None
            and not any(
                activity.kind is OpenItemActivityKind.INVOICE_CANCELLATION
                for activity in detail.activities
            )
        )

    def _update_action_availability(self, *_args: object) -> None:
        has_selection = self._selected_item() is not None
        self._details_button.setEnabled(has_selection)
        if self._cancel_invoice_button is not None:
            self._cancel_invoice_button.setEnabled(
                self._can_cancel_selected_invoice()
            )

    def _show_selected_detail(self, *_args: object) -> None:
        item = self._selected_item()
        if item is None:
            return
        dialog = OpenItemDetailDialog(
            self,
            company_id=self._company_id,
            item=item,
            service=self._service,
        )
        dialog.exec()

    def _show_context_menu(self, position: QPoint) -> None:
        row = self._items_table.rowAt(position.y())
        if row < 0:
            return
        self._items_table.setCurrentCell(row, 0)
        menu = self._build_context_menu()
        menu.exec(self._items_table.viewport().mapToGlobal(position))

    def _build_context_menu(self) -> QMenu:
        menu = QMenu(self)
        details_action = QAction("Details anzeigen", menu)
        details_action.triggered.connect(self._show_selected_detail)
        menu.addAction(details_action)
        if self._cancel_invoice_button is not None:
            cancel_action = QAction("Rechnung vollständig stornieren", menu)
            cancel_action.setEnabled(self._can_cancel_selected_invoice())
            cancel_action.triggered.connect(self._cancel_selected_invoice)
            menu.addAction(cancel_action)
        return menu

    def _cancel_selected_invoice(self, *_args: object) -> None:
        service = self._cancellation_service
        fiscal_year = self._fiscal_year
        item = self._selected_item()
        if (
            service is None
            or fiscal_year is None
            or item is None
            or not self._can_cancel_selected_invoice()
        ):
            return
        try:
            preview = service.preview(
                company_id=self._company_id,
                fiscal_year=fiscal_year,
                open_item_id=item.open_item_id,
            )
        except (TypeError, ValueError) as error:
            QMessageBox.warning(self, "Rechnung nicht stornierbar", str(error))
            return
        default_date = date.today()
        if not fiscal_year.contains(default_date):
            default_date = fiscal_year.end_date
        date_text, accepted = QInputDialog.getText(
            self,
            "Rechnungsstorno",
            f"Stornobuchungsdatum innerhalb {fiscal_year.display_name} (TT.MM.JJJJ):",
            text=default_date.strftime("%d.%m.%Y"),
        )
        if not accepted:
            return
        try:
            booking_date = parse_german_date(date_text)
            if not fiscal_year.contains(booking_date):
                raise ValueError(
                    "Das Stornobuchungsdatum liegt außerhalb des geöffneten Geschäftsjahrs."
                )
        except (TypeError, ValueError) as error:
            QMessageBox.warning(self, "Ungültiges Buchungsdatum", str(error))
            return
        try:
            assessment = service.assess_payment_history(
                company_id=self._company_id,
                fiscal_year=fiscal_year,
                open_item_id=item.open_item_id,
                proposed_booking_date=booking_date,
            )
        except (TypeError, ValueError) as error:
            QMessageBox.warning(self, "Rechnung nicht stornierbar", str(error))
            return
        reason, accepted = QInputDialog.getText(
            self,
            "Stornogrund",
            "Bitte geben Sie den verpflichtenden Grund für das Rechnungsstorno ein:",
        )
        if not accepted or not reason.strip():
            if accepted:
                QMessageBox.warning(
                    self, "Stornogrund fehlt", "Ein Stornogrund ist erforderlich."
                )
            return
        lines = "\n".join(
            f"{line.account_number} · "
            f"{'Haben' if line.side.value == 'DEBIT' else 'Soll'} · "
            f"{_money(line.amount)} €"
            for line in preview.original_booking.lines
        )
        paid_amount = assessment.effective_payment_amount
        credit_label = (
            "Lieferantenguthaben"
            if item.kind is OpenItemKind.SUPPLIER_PAYABLE
            else "Kundenguthaben"
        )
        credit_description = (
            f"Entstehendes {credit_label}: {_money(paid_amount)} €"
            if paid_amount > Decimal("0.00")
            else "Es entsteht kein Partnerguthaben."
        )
        prompt = (
            f"{preview.partner_name} · Rechnung {preview.invoice_number}\n"
            f"Stornodatum: {_date(booking_date)}\n"
            f"Ursprünglicher Rechnungsbetrag: {_money(assessment.invoice_amount)} €\n"
            f"Wirksam bezahlt: {_money(paid_amount)} €\n"
            f"Noch offener Rechnungsbetrag: {_money(assessment.open_amount)} €\n"
            f"{credit_description}\n\n"
            f"Gegenbuchung (Soll/Haben gespiegelt):\n{lines}\n\n"
            "Die Rechnung wird vollständig storniert und der Rechnungs-OP geschlossen. "
            "Bereits erfolgte Zahlungen werden nicht rückgängig gemacht. "
            "Es entsteht keine Bank- oder Kassenbewegung.\n"
            f"Grund: {reason.strip()}\n\nJetzt verbindlich stornieren?"
        )
        if QMessageBox.question(
            self,
            "Rechnung vollständig stornieren",
            prompt,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        ) != QMessageBox.StandardButton.Yes:
            return
        try:
            service.cancel_invoice(
                company_id=self._company_id,
                fiscal_year=fiscal_year,
                open_item_id=item.open_item_id,
                booking_date=booking_date,
                reason=reason,
                confirmed=True,
            )
        except Exception as error:
            QMessageBox.warning(
                self, "Rechnungsstorno fehlgeschlagen", str(error)
            )
            return
        self.refresh()
        if self._on_cancelled is not None:
            self._on_cancelled()


def _sum(values) -> Decimal:
    return sum(values, start=Decimal("0.00"))


def _money(value: Decimal) -> str:
    return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _date(value: date | None) -> str:
    return value.strftime("%d.%m.%Y") if value is not None else "—"

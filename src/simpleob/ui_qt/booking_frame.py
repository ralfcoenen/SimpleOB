"""PySide6-Eingabemaske für laufende Buchungen."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation

from PySide6.QtCore import QEvent, QObject, Qt, QTimer
from PySide6.QtGui import QFontMetrics, QKeyEvent
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QCompleter,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from simpleob.amount_input import format_german_amount
from simpleob.date_input import GermanDateEdit
from simpleob.domain.account import Account
from simpleob.domain.account_display import account_display_name, account_name_with_role
from simpleob.domain.booking import Booking
from simpleob.domain.booking_line import BookingLine
from simpleob.domain.entry_side import EntrySide
from simpleob.domain.money import ZERO


@dataclass(slots=True)
class _BookingRow:
    """Hält die Eingabeelemente einer Buchungszeile."""

    account_entry: QLineEdit
    name_item: QTableWidgetItem
    debit_entry: QLineEdit
    credit_entry: QLineEdit
    contribution_checkbox: QCheckBox
    remove_button: QPushButton
    completer: QCompleter

class BookingFrame(QWidget):
    """Erfasst einfache und mehrzeilige laufende Buchungen."""

    _ACCOUNT_COLUMN = 0
    _NAME_COLUMN = 1
    _DEBIT_COLUMN = 2
    _CREDIT_COLUMN = 3
    _CONTRIBUTION_COLUMN = 4
    _REMOVE_COLUMN = 5

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        accounts: tuple[Account, ...],
        equity_contribution_account_numbers: frozenset[str],
        on_booking_created: Callable[
            [Booking, tuple[int, ...]],
            None,
        ],
    ) -> None:
        super().__init__(parent)

        self._accounts = accounts
        self._equity_contribution_account_numbers = (
            equity_contribution_account_numbers
        )
        self._on_booking_created = on_booking_created
        self._enabled = True

        self._accounts_by_display_name = {
            self._account_display_name(account): account
            for account in accounts
        }
        self._account_display_names = tuple(
            self._accounts_by_display_name
        )

        self._rows: list[_BookingRow] = []

        self._create_ui()

    def _create_ui(self) -> None:
        """Erzeugt die Buchungsmaske."""

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        form = QVBoxLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(4)

        header_row = QHBoxLayout()
        header_row.setSpacing(6)

        self._booking_date_entry = GermanDateEdit(value=date.today())
        self._booking_date_entry.setMinimumWidth(120)
        self._booking_date_entry.setMaximumWidth(140)
        date_label = QLabel("Datum")
        date_label.setBuddy(self._booking_date_entry)
        header_row.addWidget(date_label)
        header_row.addWidget(self._booking_date_entry)
        header_row.addSpacing(12)

        self._voucher_no_entry = QLineEdit()
        self._voucher_no_entry.setMinimumWidth(140)
        self._voucher_no_entry.setMaximumWidth(220)
        voucher_no_label = QLabel("Belegnummer")
        voucher_no_label.setBuddy(self._voucher_no_entry)
        header_row.addWidget(voucher_no_label)
        header_row.addWidget(self._voucher_no_entry)
        header_row.addStretch()
        form.addLayout(header_row)

        self._description_entry = QLineEdit()
        description_label = QLabel("Buchungstext")
        description_label.setBuddy(self._description_entry)
        description_row = QHBoxLayout()
        description_row.setSpacing(6)
        description_row.addWidget(description_label)
        description_row.addWidget(self._description_entry, 1)
        form.addLayout(description_row)

        layout.addLayout(form)

        self._booking_table = QTableWidget()
        self._booking_table.setColumnCount(6)
        self._booking_table.setHorizontalHeaderLabels(
            (
                "Konto",
                "Kontoname",
                "Soll",
                "Haben",
                "Einlage",
                "",
            )
        )
        self._booking_table.verticalHeader().setVisible(False)
        self._booking_table.setAlternatingRowColors(True)
        self._booking_table.setSelectionMode(
            QTableWidget.SelectionMode.NoSelection
        )
        self._booking_table.setFocusPolicy(
            Qt.FocusPolicy.NoFocus
        )

        header = self._booking_table.horizontalHeader()
        header.setSectionResizeMode(
            self._ACCOUNT_COLUMN,
            QHeaderView.ResizeMode.ResizeToContents,
        )
        header.setSectionResizeMode(
            self._NAME_COLUMN,
            QHeaderView.ResizeMode.Stretch,
        )
        header.setSectionResizeMode(
            self._DEBIT_COLUMN,
            QHeaderView.ResizeMode.ResizeToContents,
        )
        header.setSectionResizeMode(
            self._CREDIT_COLUMN,
            QHeaderView.ResizeMode.ResizeToContents,
        )
        header.setSectionResizeMode(
            self._CONTRIBUTION_COLUMN,
            QHeaderView.ResizeMode.ResizeToContents,
        )
        header.setSectionResizeMode(
            self._REMOVE_COLUMN,
            QHeaderView.ResizeMode.ResizeToContents,
        )

        self._booking_table.setMinimumHeight(135)
        layout.addWidget(self._booking_table)

        totals_layout = QHBoxLayout()
        totals_layout.addStretch()

        totals_layout.addWidget(QLabel("Soll:"))

        self._debit_total_label = QLabel("0,00")
        self._debit_total_label.setMinimumWidth(84)
        self._debit_total_label.setAlignment(
            Qt.AlignmentFlag.AlignRight
        )
        totals_layout.addWidget(
            self._debit_total_label
        )

        totals_layout.addSpacing(12)
        totals_layout.addWidget(QLabel("Haben:"))

        self._credit_total_label = QLabel("0,00")
        self._credit_total_label.setMinimumWidth(84)
        self._credit_total_label.setAlignment(
            Qt.AlignmentFlag.AlignRight
        )
        totals_layout.addWidget(
            self._credit_total_label
        )

        totals_layout.addSpacing(12)
        totals_layout.addWidget(QLabel("Differenz:"))

        self._difference_label = QLabel("0,00")
        self._difference_label.setMinimumWidth(84)
        self._difference_label.setAlignment(
            Qt.AlignmentFlag.AlignRight
        )
        totals_layout.addWidget(
            self._difference_label
        )

        layout.addLayout(totals_layout)

        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self._booking_button = QPushButton(
            "Buchung übernehmen"
        )
        self._booking_button.setEnabled(False)
        self._booking_button.clicked.connect(
            self._create_booking
        )
        button_layout.addWidget(
            self._booking_button
        )

        layout.addLayout(button_layout)

        self._status_label = QLabel()
        layout.addWidget(self._status_label)

        self._booking_date_entry.textChanged.connect(
            self._on_form_changed
        )
        self._voucher_no_entry.textChanged.connect(
            self._on_form_changed
        )
        self._description_entry.textChanged.connect(
            self._on_form_changed
        )

        self._append_empty_row()
        self._on_form_changed()

    def set_enabled(
        self,
        enabled: bool,
    ) -> None:
        """Aktiviert oder sperrt die Buchungserfassung."""

        self._enabled = enabled

        self._booking_date_entry.setEnabled(enabled)
        self._voucher_no_entry.setEnabled(enabled)
        self._description_entry.setEnabled(enabled)
        self._booking_table.setEnabled(enabled)

        if enabled:
            self._on_form_changed()
        else:
            self._booking_button.setEnabled(False)
            self._status_label.setText(
                "Das Geschäftsjahr ist abgeschlossen. "
                "Buchungen sind nicht mehr möglich."
            )

    def update_accounts(
        self,
        *,
        accounts: tuple[Account, ...],
        equity_contribution_account_numbers: frozenset[str],
    ) -> None:
        """Aktualisiert die Kontenauswahl, ohne Eingaben zu verwerfen."""

        old_accounts_by_display_name = self._accounts_by_display_name
        old_accounts_by_number = {
            account.number: account for account in self._accounts
        }
        self._accounts = accounts
        self._accounts_by_display_name = {
            self._account_display_name(account): account
            for account in accounts
        }
        self._account_display_names = tuple(self._accounts_by_display_name)
        self._equity_contribution_account_numbers = (
            equity_contribution_account_numbers
        )

        for row in self._rows:
            old_text = row.account_entry.text()
            old_account = old_accounts_by_display_name.get(old_text)
            if old_account is None:
                old_account = old_accounts_by_number.get(old_text.strip())
            completer = QCompleter(
                self._account_display_names,
                row.account_entry,
            )
            completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            completer.setFilterMode(Qt.MatchFlag.MatchContains)
            completer.setCompletionMode(
                QCompleter.CompletionMode.PopupCompletion
            )
            completer.setMaxVisibleItems(12)
            self._configure_account_completer_popup(
                row.account_entry,
                completer,
            )
            row.account_entry.setCompleter(completer)
            row.completer = completer
            current_account = next(
                (
                    account
                    for account in accounts
                    if old_account is not None
                    and account.number == old_account.number
                ),
                None,
            )
            row.account_entry.setText(
                current_account.number
                if current_account is not None
                else old_text
            )
            self._on_account_changed(row)

    def _append_empty_row(self) -> None:
        """Fügt am Tabellenende eine leere Buchungszeile hinzu."""

        row_index = self._booking_table.rowCount()
        self._booking_table.insertRow(row_index)

        account_entry = QLineEdit()

        completer = QCompleter(
            self._account_display_names,
            account_entry,
        )
        completer.setCaseSensitivity(
            Qt.CaseSensitivity.CaseInsensitive
        )
        completer.setFilterMode(
            Qt.MatchFlag.MatchContains
        )
        completer.setCompletionMode(
            QCompleter.CompletionMode.PopupCompletion
        )
        completer.setMaxVisibleItems(12)
        self._configure_account_completer_popup(
            account_entry,
            completer,
        )

        account_entry.setCompleter(completer)

        name_item = QTableWidgetItem("")
        name_item.setFlags(
            name_item.flags()
            & ~Qt.ItemFlag.ItemIsEditable
        )

        debit_entry = self._create_amount_entry()
        credit_entry = self._create_amount_entry()

        contribution_checkbox = QCheckBox()
        contribution_checkbox.setEnabled(False)
        contribution_checkbox.setToolTip(
            "Diese Habenzeile als Einlage "
            "für den Betriebsvermögensvergleich kennzeichnen."
        )

        remove_button = QPushButton("×")
        remove_button.setMaximumWidth(36)
        remove_button.setToolTip(
            "Buchungszeile entfernen"
        )
        remove_button.setFocusPolicy(
            Qt.FocusPolicy.NoFocus
        )

        booking_row = _BookingRow(
            account_entry=account_entry,
            name_item=name_item,
            debit_entry=debit_entry,
            credit_entry=credit_entry,
            contribution_checkbox=contribution_checkbox,
            remove_button=remove_button,
            completer=completer,
        )

        self._rows.append(booking_row)

        self._booking_table.setCellWidget(
            row_index,
            self._ACCOUNT_COLUMN,
            account_entry,
        )
        self._booking_table.setItem(
            row_index,
            self._NAME_COLUMN,
            name_item,
        )
        self._booking_table.setCellWidget(
            row_index,
            self._DEBIT_COLUMN,
            debit_entry,
        )
        self._booking_table.setCellWidget(
            row_index,
            self._CREDIT_COLUMN,
            credit_entry,
        )
        self._booking_table.setCellWidget(
            row_index,
            self._CONTRIBUTION_COLUMN,
            contribution_checkbox,
        )
        self._booking_table.setCellWidget(
            row_index,
            self._REMOVE_COLUMN,
            remove_button,
        )

        account_entry.textChanged.connect(
            lambda _text, row=booking_row:
            self._on_account_changed(row)
        )

        completer.activated.connect(
            lambda text, row=booking_row:
            self._on_completion_activated(
                row,
                text,
            )
        )

        account_entry.installEventFilter(self)
        completer.popup().installEventFilter(self)
        completer.popup().viewport().installEventFilter(self)
        debit_entry.installEventFilter(self)
        credit_entry.installEventFilter(self)

        debit_entry.textChanged.connect(
            lambda _text, entry=debit_entry:
            self._mark_amount_entry_unformatted(entry)
        )
        credit_entry.textChanged.connect(
            lambda _text, entry=credit_entry:
            self._mark_amount_entry_unformatted(entry)
        )
        debit_entry.textChanged.connect(
            lambda _text, row=booking_row:
            self._on_amount_changed(row)
        )
        credit_entry.textChanged.connect(
            lambda _text, row=booking_row:
            self._on_amount_changed(row)
        )

        remove_button.clicked.connect(
            lambda _checked=False, row=booking_row:
            self._remove_row(row)
        )

    def _configure_account_completer_popup(
        self,
        account_entry: QLineEdit,
        completer: QCompleter,
    ) -> None:
        """Gibt dem Konto-Popup Platz für Kontonummer und Kontoname."""

        popup = completer.popup()
        font_metrics = QFontMetrics(popup.font())
        longest_entry_width = max(
            (
                font_metrics.horizontalAdvance(display_name)
                for display_name in self._account_display_names
            ),
            default=0,
        )
        vertical_scrollbar_width = (
            popup.verticalScrollBar().sizeHint().width()
        )
        desired_width = max(
            450,
            longest_entry_width
            + vertical_scrollbar_width
            + popup.frameWidth() * 2
            + 16,
        )

        screen = account_entry.screen() or QApplication.primaryScreen()
        if screen is not None:
            available_width = max(
                1,
                screen.availableGeometry().width() - 4,
            )
            desired_width = min(desired_width, available_width)
            popup.setMaximumWidth(available_width)

        popup.setMinimumWidth(desired_width)
        popup.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        popup.setTextElideMode(Qt.TextElideMode.ElideNone)

    def _create_amount_entry(self) -> QLineEdit:
        """Erzeugt ein Betragsfeld für Soll oder Haben."""

        entry = QLineEdit()
        entry.setMinimumWidth(100)
        entry.setMaximumWidth(140)
        entry.setAlignment(
            Qt.AlignmentFlag.AlignRight
        )
        entry.setPlaceholderText("0,00")
        entry.setProperty("amountNormalized", False)
        entry.editingFinished.connect(
            lambda entry=entry:
            self._normalize_amount_entry(entry)
        )

        return entry

    def create_amount_entry(self) -> QLineEdit:
        """Erzeugt ein wiederverwendbares Betragsfeld mit Buchungsmaskenlogik."""
        return self._create_amount_entry()

    def _normalize_amount_entry(
        self,
        entry: QLineEdit,
    ) -> None:
        """Normalisiert eine gültige Betragseingabe."""

        value = entry.text().strip()

        if not value:
            return

        if entry.property("amountNormalized"):
            return

        try:
            normalized = format_german_amount(
                self._parse_amount_value(value)
            )
        except ValueError:
            return

        entry.setText(normalized)
        entry.setProperty("amountNormalized", True)

    def focus_booking_date(self) -> None:
        """Fokussiert das Datum und markiert den vorhandenen Wert."""

        if not self._enabled or not self.isVisible():
            return
        self._booking_date_entry.setFocus()
        self._booking_date_entry.selectAll()

    @staticmethod
    def _mark_amount_entry_unformatted(
        entry: QLineEdit,
    ) -> None:
        """Kennzeichnet manuell geänderten Feldinhalt als rohe Eingabe."""

        entry.setProperty("amountNormalized", False)

    def _update_contribution_checkbox(
        self,
        row: _BookingRow,
    ) -> None:
        """Aktualisiert die Einlagenkennzeichnung einer Buchungszeile."""

        account = self._resolve_account(
            row.account_entry.text()
        )

        is_eligible = (
            account is not None
            and account.number
            in self._equity_contribution_account_numbers
            and bool(row.credit_entry.text().strip())
            and not bool(row.debit_entry.text().strip())
        )

        row.contribution_checkbox.setEnabled(
            is_eligible
        )

        if not is_eligible:
            row.contribution_checkbox.setChecked(False)

    def _on_account_changed(
        self,
        row: _BookingRow,
    ) -> None:
        """Aktualisiert den Kontonamen einer Buchungszeile."""

        account = self._resolve_account(
            row.account_entry.text()
        )

        row.name_item.setText(
            account_name_with_role(account)
            if account is not None
            else ""
        )

        self._update_contribution_checkbox(row)
        self._ensure_trailing_empty_row()
        self._on_form_changed()

    def _on_completion_activated(
        self,
        row: _BookingRow,
        text: str,
    ) -> None:
        """Übernimmt einen Completer-Treffer und springt zu Soll."""

        account = self._resolve_account(text)

        if account is None:
            return

        row.account_entry.setText(
            account.number
        )
        row.name_item.setText(account_name_with_role(account))

        self._update_contribution_checkbox(row)

        self._ensure_trailing_empty_row()
        self._on_form_changed()

        row.debit_entry.setFocus()

    def eventFilter(
        self,
        watched: QObject,
        event: QEvent,
    ) -> bool:
        """Steuert Tab und Enter in den Buchungszeilen."""

        if event.type() == QEvent.Type.Show:
            row = self._row_for_widget(watched)
            if row is not None and watched is row.completer.popup():
                self._keep_completer_popup_on_screen(
                    row.completer.popup(),
                    row.account_entry,
                )
                QTimer.singleShot(
                    0,
                    lambda popup=row.completer.popup(),
                    entry=row.account_entry:
                    self._keep_completer_popup_on_screen(
                        popup,
                        entry,
                    ),
                )

        if (
            event.type() == QEvent.Type.KeyPress
            and isinstance(event, QKeyEvent)
        ):
            row = self._row_for_widget(watched)
            if row is not None and watched is row.account_entry:
                QTimer.singleShot(
                    0,
                    lambda popup=row.completer.popup(),
                    entry=row.account_entry:
                    self._keep_completer_popup_on_screen(
                        popup,
                        entry,
                    )
                    if popup.isVisible()
                    else None,
                )

        if (
            event.type() != QEvent.Type.KeyPress
            or not isinstance(event, QKeyEvent)
        ):
            return super().eventFilter(
                watched,
                event,
            )

        row = self._row_for_widget(watched)

        if row is None:
            return super().eventFilter(
                watched,
                event,
            )

        popup = row.completer.popup()
        popup_viewport = popup.viewport()

        if watched in (
            popup,
            popup_viewport,
        ):
            if event.key() == Qt.Key.Key_Tab:
                current_index = popup.currentIndex()

                if current_index.isValid():
                    completion = current_index.data()

                    if isinstance(completion, str):
                        account = self._resolve_account(
                            completion
                        )

                        if account is not None:
                            popup.hide()

                            row.account_entry.setText(
                                account.number
                            )
                            row.name_item.setText(account_name_with_role(account))

                            self._ensure_trailing_empty_row()
                            self._on_form_changed()

                            row.debit_entry.setFocus()
                            return True

                popup.hide()
                row.account_entry.setFocus()
                return True

            return super().eventFilter(
                watched,
                event,
            )

        if event.key() in (
            Qt.Key.Key_Return,
            Qt.Key.Key_Enter,
        ):
            if watched is row.account_entry:
                if popup.isVisible():
                    return super().eventFilter(
                        watched,
                        event,
                    )

                account = self._resolve_account(
                    row.account_entry.text()
                )

                if account is not None:
                    row.account_entry.setText(
                        account.number
                    )
                    row.name_item.setText(account_name_with_role(account))

                    self._ensure_trailing_empty_row()
                    self._on_form_changed()

                    row.debit_entry.setFocus()
                    return True

            return super().eventFilter(
                watched,
                event,
            )

        if event.key() == Qt.Key.Key_Tab:
            return self._move_to_next_booking_field(
                row,
                watched,
            )

        if event.key() == Qt.Key.Key_Backtab:
            if (
                watched is row.account_entry
                and popup.isVisible()
            ):
                popup.hide()

            return self._move_to_previous_booking_field(
                row,
                watched,
            )

        return super().eventFilter(
            watched,
            event,
        )

    @staticmethod
    def _keep_completer_popup_on_screen(
        popup: QWidget,
        account_entry: QLineEdit,
    ) -> None:
        """Verschiebt und begrenzt das Completer-Popup auf den Arbeitsbereich."""

        screen = account_entry.screen() or popup.screen()
        if screen is None:
            return

        available = screen.availableGeometry()
        available_width = max(1, available.width() - 4)
        available_height = max(1, available.height() - 4)
        frame = popup.frameGeometry()
        frame_width = frame.width()
        frame_height = frame.height()
        if frame_width > available_width:
            popup.resize(
                max(1, popup.width() - frame_width + available_width),
                popup.height(),
            )
        if frame_height > available_height:
            popup.resize(
                popup.width(),
                max(1, popup.height() - frame_height + available_height),
            )

        frame = popup.frameGeometry()
        left = max(
            available.left(),
            min(frame.left(), available.left() + available_width - frame.width()),
        )
        top = max(
            available.top(),
            min(frame.top(), available.top() + available_height - frame.height()),
        )
        popup.move(left, top)

    def _row_for_widget(
        self,
        widget: QObject,
    ) -> _BookingRow | None:
        """Ermittelt die Buchungszeile eines Eingabefeldes."""

        for row in self._rows:
            if widget in (
                row.account_entry,
                row.completer.popup(),
                row.completer.popup().viewport(),
                row.debit_entry,
                row.credit_entry,
            ):
                return row

        return None

    def _move_to_next_booking_field(
        self,
        row: _BookingRow,
        widget: QObject,
    ) -> bool:
        """Setzt den Fokus auf das nächste Buchungsfeld."""

        if widget is row.account_entry:
            if row.debit_entry.isEnabled():
                row.debit_entry.setFocus()
            elif row.credit_entry.isEnabled():
                row.credit_entry.setFocus()
            else:
                self._focus_next_account(row)

            return True

        if widget is row.debit_entry:
            if row.credit_entry.isEnabled():
                row.credit_entry.setFocus()
            else:
                self._focus_next_account(row)

            return True

        if widget is row.credit_entry:
            self._focus_next_account(row)
            return True

        return False

    def _move_to_previous_booking_field(
        self,
        row: _BookingRow,
        widget: QObject,
    ) -> bool:
        """Setzt den Fokus auf das vorherige Buchungsfeld."""

        if widget is row.credit_entry:
            if row.debit_entry.isEnabled():
                row.debit_entry.setFocus()
            else:
                row.account_entry.setFocus()

            return True

        if widget is row.debit_entry:
            row.account_entry.setFocus()
            return True

        if widget is row.account_entry:
            self._focus_previous_amount(row)
            return True

        return False

    def _focus_next_account(
        self,
        row: _BookingRow,
    ) -> None:
        """Setzt den Fokus auf das Konto der nächsten Zeile."""

        try:
            row_index = self._rows.index(row)
        except ValueError:
            return

        if row_index + 1 >= len(self._rows):
            self._ensure_trailing_empty_row()

        if row_index + 1 >= len(self._rows):
            return

        self._rows[
            row_index + 1
        ].account_entry.setFocus()

    def _focus_previous_amount(
        self,
        row: _BookingRow,
    ) -> None:
        """Setzt den Fokus auf den Betrag der vorherigen Zeile."""

        try:
            row_index = self._rows.index(row)
        except ValueError:
            return

        if row_index == 0:
            self._description_entry.setFocus()
            return

        previous_row = self._rows[row_index - 1]

        if previous_row.credit_entry.isEnabled():
            previous_row.credit_entry.setFocus()
        elif previous_row.debit_entry.isEnabled():
            previous_row.debit_entry.setFocus()
        else:
            previous_row.account_entry.setFocus()

    def _on_amount_changed(
        self,
        row: _BookingRow,
    ) -> None:
        """Steuert Soll/Haben und aktualisiert die Buchung."""

        row.debit_entry.setEnabled(self._enabled)
        row.credit_entry.setEnabled(self._enabled)

        self._update_contribution_checkbox(row)
        self._ensure_trailing_empty_row()
        self._on_form_changed()


    def _remove_row(
        self,
        row: _BookingRow,
    ) -> None:
        """Entfernt eine Buchungszeile."""

        if row not in self._rows:
            return

        row_index = self._rows.index(row)

        self._rows.pop(row_index)
        self._booking_table.removeRow(
            row_index
        )

        if not self._rows:
            self._append_empty_row()

        self._ensure_trailing_empty_row()
        self._on_form_changed()

    def _ensure_trailing_empty_row(self) -> None:
        """Hält genau eine leere Eingabezeile am Tabellenende vor."""

        if not self._rows:
            self._append_empty_row()
            return

        last_row = self._rows[-1]

        if not self._row_is_empty(last_row):
            self._append_empty_row()

    def _row_is_empty(
        self,
        row: _BookingRow,
    ) -> bool:
        """Prüft, ob eine Tabellenzeile vollständig leer ist."""

        return (
            not row.account_entry.text().strip()
            and not row.debit_entry.text().strip()
            and not row.credit_entry.text().strip()
        )

    def _on_form_changed(
        self,
        *_args: object,
    ) -> None:
        """Prüft die Vollständigkeit der Buchungsmaske."""

        debit_total = ZERO
        credit_total = ZERO
        valid_lines = 0
        debit_lines = 0
        credit_lines = 0
        rows_valid = True

        for row in self._rows:
            if self._row_is_empty(row):
                continue

            account = self._resolve_account(
                row.account_entry.text()
            )

            debit_text = (
                row.debit_entry.text().strip()
            )
            credit_text = (
                row.credit_entry.text().strip()
            )

            if account is None:
                rows_valid = False
                continue

            if bool(debit_text) == bool(credit_text):
                rows_valid = False
                continue

            try:
                if debit_text:
                    amount = self._parse_amount(
                        debit_text,
                        normalized=bool(
                            row.debit_entry.property("amountNormalized")
                        ),
                    )
                    debit_total += amount
                    debit_lines += 1
                else:
                    amount = self._parse_amount(
                        credit_text,
                        normalized=bool(
                            row.credit_entry.property("amountNormalized")
                        ),
                    )
                    credit_total += amount
                    credit_lines += 1
            except ValueError:
                rows_valid = False
                continue

            valid_lines += 1

        difference = debit_total - credit_total

        self._debit_total_label.setText(
            self._format_amount(debit_total)
        )
        self._credit_total_label.setText(
            self._format_amount(credit_total)
        )
        self._difference_label.setText(
            self._format_amount(difference)
        )

        if not self._enabled:
            self._booking_button.setEnabled(False)
            return

        valid = rows_valid

        try:
            self._booking_date_entry.date_value()
        except ValueError:
            valid = False

        if not self._description_entry.text().strip():
            valid = False

        if valid_lines < 2:
            valid = False

        if debit_lines < 1:
            valid = False

        if credit_lines < 1:
            valid = False

        if debit_total != credit_total:
            valid = False

        self._booking_button.setEnabled(valid)
        self._status_label.clear()

    def _create_booking(self) -> None:
        """Erzeugt die Buchung aus den Tabellenzeilen."""

        if not self._enabled:
            return

        try:
            booking_date = self._booking_date_entry.date_value()
        except ValueError:
            return

        self._booking_date_entry.set_date(booking_date)

        for row in self._rows:
            self._normalize_amount_entry(row.debit_entry)
            self._normalize_amount_entry(row.credit_entry)

        lines: list[BookingLine] = []
        equity_contribution_line_positions: list[int] = []

        for row in self._rows:
            if self._row_is_empty(row):
                continue

            account = self._resolve_account(
                row.account_entry.text()
            )

            if account is None:
                return

            debit_text = (
                row.debit_entry.text().strip()
            )
            credit_text = (
                row.credit_entry.text().strip()
            )

            try:
                if debit_text and not credit_text:
                    lines.append(
                        BookingLine(
                            account_number=account.number,
                            side=EntrySide.DEBIT,
                            amount=self._parse_amount(
                                debit_text,
                                normalized=bool(
                                    row.debit_entry.property("amountNormalized")
                                ),
                            ),
                        )
                    )
                elif credit_text and not debit_text:
                    line_position = len(lines)

                    lines.append(
                        BookingLine(
                            account_number=account.number,
                            side=EntrySide.CREDIT,
                            amount=self._parse_amount(
                                credit_text,
                                normalized=bool(
                                    row.credit_entry.property("amountNormalized")
                                ),
                            ),
                        )
                    )

                    if row.contribution_checkbox.isChecked():
                        equity_contribution_line_positions.append(
                            line_position
                        )
                else:
                    return
            except ValueError:
                return

        voucher_no = (
            self._voucher_no_entry.text().strip()
            or None
        )
        description = (
            self._description_entry.text().strip()
        )

        try:
            booking = Booking(
                booking_date=booking_date,
                voucher_no=voucher_no,
                description=description,
                lines=tuple(lines),
            )
        except ValueError:
            return

        self._on_booking_created(
            booking,
            tuple(equity_contribution_line_positions),
        )

        self._clear()

        self._status_label.setText(
            "Buchung wurde übernommen."
        )
        self.focus_booking_date()

    def _resolve_account(
        self,
        value: str,
    ) -> Account | None:
        """Ermittelt eindeutig das ausgewählte Konto."""

        normalized = value.strip()

        if not normalized:
            return None

        direct_match = self._accounts_by_display_name.get(
            normalized
        )

        if direct_match is not None:
            return direct_match

        number_matches = tuple(
            account
            for account in self._accounts
            if account.number == normalized
        )

        if len(number_matches) == 1:
            return number_matches[0]

        search_value = normalized.casefold()

        text_matches = tuple(
            account
            for account in self._accounts
            if search_value
            in self._account_display_name(account).casefold()
        )

        if len(text_matches) == 1:
            return text_matches[0]

        return None

    def _clear(self) -> None:
        """Leert die Buchung für die nächste Erfassung."""

        self._voucher_no_entry.clear()
        self._description_entry.clear()

        self._clear_rows()
        self._append_empty_row()

        self._on_form_changed()

    def _clear_rows(self) -> None:
        """Entfernt alle Buchungszeilen."""

        self._rows.clear()
        self._booking_table.setRowCount(0)

    @staticmethod
    def _account_display_name(
        account: Account,
    ) -> str:
        """Liefert die lesbare Kontendarstellung."""

        return account_display_name(account)

    @staticmethod
    def _parse_amount(
        value: str,
        *,
        normalized: bool = False,
    ) -> Decimal:
        """Wandelt einen deutschen Geldbetrag in Decimal um."""

        text = value.strip()

        if not text:
            raise ValueError(
                "Der Buchungsbetrag fehlt."
            )

        amount = BookingFrame._parse_amount_value(
            text,
            normalized=normalized,
        )

        if amount <= ZERO:
            raise ValueError(
                "Der Buchungsbetrag muss größer als 0,00 sein."
            )

        return amount.quantize(
            Decimal("0.01")
        )

    @staticmethod
    def _parse_amount_value(
        value: str,
        *,
        normalized: bool = False,
    ) -> Decimal:
        """Liest Ziffern als Cent und Kommawerte als ausdrückliche Beträge."""

        text = value.strip()
        if not text:
            raise ValueError("Der Betrag darf nicht leer sein.")

        try:
            if "," in text:
                amount = Decimal(
                    text.replace(".", "").replace(",", ".")
                )
            elif not normalized and text.lstrip("+-").isdigit():
                amount = Decimal(text) / Decimal("100")
            else:
                amount = Decimal(text.replace(".", ""))
        except InvalidOperation as exc:
            raise ValueError("Ungültiger Geldbetrag.") from exc

        return amount.quantize(Decimal("0.01"))

    @staticmethod
    def _format_amount(
        amount: Decimal,
    ) -> str:
        """Formatiert einen Geldbetrag deutsch."""

        formatted = f"{amount:,.2f}"

        return (
            formatted
            .replace(",", "\0")
            .replace(".", ",")
            .replace("\0", ".")
        )

"""PySide6-Eingabemaske für laufende Buchungen."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import (
    QCheckBox,
    QCompleter,
    QFormLayout,
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

from openbilanz.amount_input import normalize_german_amount
from openbilanz.date_input import (
    normalize_german_date,
    parse_german_date,
)
from openbilanz.domain.account import Account
from openbilanz.domain.booking import Booking
from openbilanz.domain.booking_line import BookingLine
from openbilanz.domain.entry_side import EntrySide
from openbilanz.domain.money import ZERO


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

        form = QFormLayout()
        form.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow
        )

        self._booking_date_entry = QLineEdit(
            date.today().strftime("%d.%m.%Y")
        )
        self._booking_date_entry.setMaximumWidth(140)
        self._booking_date_entry.editingFinished.connect(
            self._normalize_booking_date
        )
        form.addRow(
            "Datum",
            self._booking_date_entry,
        )

        self._voucher_no_entry = QLineEdit()
        self._voucher_no_entry.setMaximumWidth(220)
        form.addRow(
            "Belegnummer",
            self._voucher_no_entry,
        )

        self._description_entry = QLineEdit()
        form.addRow(
            "Buchungstext",
            self._description_entry,
        )

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

        self._booking_table.setMinimumHeight(220)
        layout.addWidget(self._booking_table)

        totals_layout = QHBoxLayout()
        totals_layout.addStretch()

        totals_layout.addWidget(QLabel("Soll:"))

        self._debit_total_label = QLabel("0,00")
        self._debit_total_label.setMinimumWidth(100)
        self._debit_total_label.setAlignment(
            Qt.AlignmentFlag.AlignRight
        )
        totals_layout.addWidget(
            self._debit_total_label
        )

        totals_layout.addSpacing(20)
        totals_layout.addWidget(QLabel("Haben:"))

        self._credit_total_label = QLabel("0,00")
        self._credit_total_label.setMinimumWidth(100)
        self._credit_total_label.setAlignment(
            Qt.AlignmentFlag.AlignRight
        )
        totals_layout.addWidget(
            self._credit_total_label
        )

        totals_layout.addSpacing(20)
        totals_layout.addWidget(QLabel("Differenz:"))

        self._difference_label = QLabel("0,00")
        self._difference_label.setMinimumWidth(100)
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

        layout.addStretch()

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

    def _create_amount_entry(self) -> QLineEdit:
        """Erzeugt ein Betragsfeld für Soll oder Haben."""

        entry = QLineEdit()
        entry.setMaximumWidth(160)
        entry.setAlignment(
            Qt.AlignmentFlag.AlignRight
        )
        entry.setPlaceholderText("0,00")
        entry.editingFinished.connect(
            lambda entry=entry:
            self._normalize_amount_entry(entry)
        )

        return entry

    def _normalize_amount_entry(
        self,
        entry: QLineEdit,
    ) -> None:
        """Normalisiert eine gültige Betragseingabe."""

        value = entry.text().strip()

        if not value:
            return

        try:
            normalized = normalize_german_amount(
                value
            )
        except ValueError:
            return

        entry.setText(normalized)

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
            account.name
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
        row.name_item.setText(
            account.name
        )

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
                            row.name_item.setText(
                                account.name
                            )

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
                    row.name_item.setText(
                        account.name
                    )

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

        debit_has_value = bool(
            row.debit_entry.text().strip()
        )
        credit_has_value = bool(
            row.credit_entry.text().strip()
        )

        if debit_has_value:
            row.credit_entry.setEnabled(False)
        elif credit_has_value:
            row.debit_entry.setEnabled(False)
        else:
            row.debit_entry.setEnabled(
                self._enabled
            )
            row.credit_entry.setEnabled(
                self._enabled
            )

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
                        debit_text
                    )
                    debit_total += amount
                    debit_lines += 1
                else:
                    amount = self._parse_amount(
                        credit_text
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
            self._parse_booking_date(
                self._booking_date_entry.text()
            )
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
            booking_date = self._parse_booking_date(
                self._booking_date_entry.text()
            )
        except ValueError:
            return

        self._booking_date_entry.setText(
            booking_date.strftime("%d.%m.%Y")
        )

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
                                debit_text
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
                                credit_text
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

        self._voucher_no_entry.setFocus()

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

        return f"{account.number} – {account.name}"

    @staticmethod
    def _parse_booking_date(
        value: str,
    ):
        """Liest eine deutsche Datumseingabe."""

        return parse_german_date(
            value
        )

    @staticmethod
    def _parse_amount(
        value: str,
    ) -> Decimal:
        """Wandelt einen deutschen Geldbetrag in Decimal um."""

        normalized = value.strip()

        if not normalized:
            raise ValueError(
                "Der Buchungsbetrag fehlt."
            )

        normalized = normalized.replace(".", "")
        normalized = normalized.replace(",", ".")

        try:
            amount = Decimal(normalized)
        except InvalidOperation as exc:
            raise ValueError(
                "Ungültiger Geldbetrag."
            ) from exc

        if amount <= ZERO:
            raise ValueError(
                "Der Buchungsbetrag muss größer als 0,00 sein."
            )

        return amount.quantize(
            Decimal("0.01")
        )

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

    def _normalize_booking_date(self) -> None:
        """Normalisiert das Buchungsdatum beim Verlassen des Feldes."""

        value = self._booking_date_entry.text().strip()

        if not value:
            return

        try:
            normalized = normalize_german_date(
                value
            )
        except ValueError:
            return

        self._booking_date_entry.setText(
            normalized
        )

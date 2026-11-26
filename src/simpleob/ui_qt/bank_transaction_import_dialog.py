"""Dialog zur Prüfung und bestätigten Übernahme von Bankumsätzen."""

from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from simpleob.amount_input import format_german_amount
from simpleob.domain.account import Account
from simpleob.domain.account_display import account_display_name
from simpleob.domain.bank_booking_proposal import (
    BankBookingProposal,
    CounterBookingLineProposal,
    build_booking_proposals,
)
from simpleob.domain.bank_transaction import (
    BankTransaction,
    TransactionImportStatus,
)
from simpleob.domain.entry_side import EntrySide
from simpleob.importers.bank_csv_errors import BankCsvImportError
from simpleob.importers.qonto_csv_importer import QontoCsvImporter
from simpleob.ui_qt.booking_frame import BookingFrame


class CounterBookingLinesDialog(QDialog):
    """Bearbeitet mehrere Gegenbuchungszeilen mit Decimal-Summenprüfung."""

    def __init__(
        self,
        *,
        parent: QWidget,
        bank_amount: Decimal,
        accounts: tuple[Account, ...],
        lines: tuple[CounterBookingLineProposal, ...],
        amount_entry_factory: Callable[[], QLineEdit],
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Gegenbuchungszeilen aufteilen")
        available = self.screen().availableGeometry()
        minimum_width = min(560, available.width())
        minimum_height = min(320, available.height())
        self.setMinimumSize(minimum_width, minimum_height)
        self.resize(
            min(820, max(minimum_width, available.width() - 48)),
            min(440, max(minimum_height, available.height() - 60)),
        )
        self.setSizeGripEnabled(True)
        self._bank_amount = abs(bank_amount)
        self._accounts = accounts
        self._amount_entry_factory = amount_entry_factory
        self._rows: list[dict[str, QWidget]] = []
        self._counter_lines: tuple[CounterBookingLineProposal, ...] | None = None

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"Bankbetrag: {format_german_amount(self._bank_amount)} €"))
        self._table = QTableWidget(0, 3, self)
        self._table.setHorizontalHeaderLabels(("Gegenkonto", "Teilbetrag (€)", ""))
        self._table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._table.setColumnWidth(0, 430)
        self._table.setColumnWidth(1, 150)
        self._table.setColumnWidth(2, 120)
        self._table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self._table)

        row_buttons = QHBoxLayout()
        self._add_line_button = QPushButton("Gegenbuchungszeile hinzufügen")
        self._add_line_button.clicked.connect(self._add_line)
        row_buttons.addWidget(self._add_line_button)
        row_buttons.addStretch(1)
        layout.addLayout(row_buttons)

        self._sum_label = QLabel()
        self._sum_label.setWordWrap(True)
        layout.addWidget(self._sum_label)
        self._validation_label = QLabel()
        self._validation_label.setWordWrap(True)
        self._validation_label.setStyleSheet("color: #9b1c1c; font-weight: bold;")
        layout.addWidget(self._validation_label)

        self._buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self._buttons.accepted.connect(self._accept_if_valid)
        self._buttons.rejected.connect(self.reject)
        layout.addWidget(self._buttons)

        for line in lines:
            self._append_line(line.account_number, format_german_amount(line.amount))
        self._refresh_totals()

    @property
    def counter_lines(self) -> tuple[CounterBookingLineProposal, ...] | None:
        """Zeilen nur nach gültiger Bestätigung; bei Abbruch bleibt None erhalten."""
        return self._counter_lines

    def _append_line(self, account_number: str | None, amount: str) -> None:
        row = self._table.rowCount()
        self._table.insertRow(row)
        account_combo = QComboBox()
        account_combo.addItem("Konto auswählen …", None)
        for account in sorted(self._accounts, key=lambda item: item.number):
            account_combo.addItem(account_display_name(account), account.number)
        if account_number is not None:
            selected = account_combo.findData(account_number)
            if selected >= 0:
                account_combo.setCurrentIndex(selected)
        account_combo.currentIndexChanged.connect(self._refresh_totals)
        self._table.setCellWidget(row, 0, account_combo)

        amount_edit = self._amount_entry_factory()
        amount_edit.setText(amount)
        amount_edit.setProperty("amountNormalized", True)
        amount_edit.setPlaceholderText("z. B. 100,00")
        amount_edit.textChanged.connect(
            lambda _text, entry=amount_edit:
            BookingFrame._mark_amount_entry_unformatted(entry)
        )
        amount_edit.textChanged.connect(self._refresh_totals)
        self._table.setCellWidget(row, 1, amount_edit)

        remove_button = QPushButton("Entfernen")
        state = {"account": account_combo, "amount": amount_edit, "remove": remove_button}
        remove_button.clicked.connect(lambda _checked=False, item=state: self._remove_line(item))
        self._table.setCellWidget(row, 2, remove_button)
        self._rows.append(state)
        self._refresh_totals()

    def _add_line(self) -> None:
        remaining = self._bank_amount - self._current_total()
        self._append_line(None, format_german_amount(max(remaining, Decimal("0.00"))))

    def _remove_line(self, state: dict[str, QWidget]) -> None:
        if len(self._rows) <= 1:
            return
        row = self._rows.index(state)
        self._rows.pop(row)
        self._table.removeRow(row)
        self._refresh_totals()

    def _current_total(self) -> Decimal:
        total = Decimal("0.00")
        for state in self._rows:
            try:
                total += _parse_amount_entry(state["amount"])
            except ValueError:
                continue
        return total

    def _refresh_totals(self, *_args) -> None:
        total = self._current_total()
        difference = self._bank_amount - total
        self._sum_label.setText(
            f"Zugeordnet: {format_german_amount(total)} €  |  "
            f"Bankbetrag: {format_german_amount(self._bank_amount)} €  |  "
            f"Differenz: {format_german_amount(difference)} €"
        )
        errors: list[str] = []
        if not self._rows:
            errors.append("Mindestens eine Gegenbuchungszeile ist erforderlich.")
        for index, state in enumerate(self._rows, start=1):
            if state["account"].currentData() is None:
                errors.append(f"Für Gegenzeile {index} wurde kein Konto ausgewählt.")
            try:
                amount = _parse_amount_entry(state["amount"])
            except ValueError:
                errors.append(f"Der Betrag in Gegenzeile {index} ist ungültig.")
            else:
                if amount <= Decimal("0.00"):
                    errors.append(f"Der Betrag in Gegenzeile {index} muss größer als 0,00 € sein.")
        if difference != Decimal("0.00"):
            if difference > 0:
                errors.append(f"Es fehlen {format_german_amount(difference)} €.")
            else:
                errors.append(f"Die Aufteilung überschreitet den Bankbetrag um {format_german_amount(-difference)} €.")
        self._validation_label.setText("\n".join(errors))
        self._buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(not errors)
        for state in self._rows:
            state["remove"].setEnabled(len(self._rows) > 1)

    def _accept_if_valid(self) -> None:
        self._refresh_totals()
        if self._validation_label.text():
            return
        self._counter_lines = tuple(
            CounterBookingLineProposal(
                state["account"].currentData(),
                _parse_amount_entry(state["amount"]),
            )
            for state in self._rows
        )
        self.accept()


class BankTransactionImportDialog(QDialog):
    """Liest das synthetische Testformat und zeigt editierbare Vorschläge."""

    _COLUMNS = ("Übernehmen", "Buchungsdatum", "Zahlungspartner", "Referenz",
                "Betrag", "Gegenkonto", "Buchungstext", "Importstatus")

    def __init__(
        self,
        *,
        parent: QWidget,
        accounts: tuple[Account, ...],
        amount_entry_factory: Callable[[], QLineEdit],
        bank_account_numbers: frozenset[str],
        duplicate_lookup: Callable[[BankTransaction], object | None],
        post_proposal: Callable[..., object],
        journal=(),
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Bankumsätze importieren")
        self.resize(1250, 650)
        self._accounts = tuple(account for account in accounts if account.is_active)
        self._amount_entry_factory = amount_entry_factory
        self._account_by_number = {account.number: account for account in self._accounts}
        self._bank_account_numbers = bank_account_numbers
        self._duplicate_lookup = duplicate_lookup
        self._post_proposal = post_proposal
        self._journal = tuple(journal)
        self._proposals: dict[int, BankBookingProposal] = {}
        self._transactions: dict[int, BankTransaction] = {}
        self._row_blocked_reasons: dict[int, str] = {}
        self._counter_combos: dict[int, QComboBox] = {}
        self._counter_summary_labels: dict[int, QLabel] = {}
        self._counter_split_buttons: dict[int, QPushButton] = {}
        self._errors: tuple[str, ...] = ()
        self._success_count = 0

        layout = QVBoxLayout(self)
        self._synthetic_notice = QLabel(
            "Hinweis: Der Parser unterstützt derzeit ausschließlich ein synthetisches "
            "Testformat. Eine Kompatibilität mit dem originalen Qonto-Export ist nicht bestätigt."
        )
        self._synthetic_notice.setWordWrap(True)
        layout.addWidget(self._synthetic_notice)

        file_row = QHBoxLayout()
        self._file_name = QLabel("Keine Datei ausgewählt")
        self._choose_file_button = QPushButton("CSV-Datei auswählen …")
        self._choose_file_button.clicked.connect(self._choose_file)
        file_row.addWidget(self._choose_file_button)
        file_row.addWidget(self._file_name, 1)
        layout.addLayout(file_row)

        bank_row = QHBoxLayout()
        bank_row.addWidget(QLabel("Bank-Sachkonto:"))
        self._bank_account_combo = QComboBox()
        self._bank_account_combo.addItem("Bitte auswählen", None)
        for number in sorted(bank_account_numbers):
            account = self._account_by_number.get(number)
            if account is not None:
                self._bank_account_combo.addItem(account_display_name(account), number)
        self._bank_account_combo.currentIndexChanged.connect(self._bank_account_changed)
        bank_row.addWidget(self._bank_account_combo, 1)
        layout.addLayout(bank_row)

        self._summary = QLabel("Noch keine Umsätze eingelesen.")
        self._summary.setWordWrap(True)
        layout.addWidget(self._summary)
        self._error_label = QLabel()
        self._error_label.setWordWrap(True)
        self._error_label.setStyleSheet("color: #9b1c1c;")
        layout.addWidget(self._error_label)

        self._table = QTableWidget(0, len(self._COLUMNS), self)
        self._table.setHorizontalHeaderLabels(self._COLUMNS)
        self._table.setAlternatingRowColors(True)
        self._table.setWordWrap(True)
        self._table.setMinimumHeight(300)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.setColumnWidth(0, 85)
        self._table.setColumnWidth(1, 110)
        self._table.setColumnWidth(2, 180)
        self._table.setColumnWidth(3, 180)
        self._table.setColumnWidth(4, 110)
        self._table.setColumnWidth(5, 350)
        self._table.setColumnWidth(6, 220)
        layout.addWidget(self._table, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        self._post_button = QPushButton("Ausgewählte Umsätze buchen …")
        self._post_button.setEnabled(False)
        self._post_button.clicked.connect(self._confirm_selected)
        buttons.addButton(self._post_button, QDialogButtonBox.ButtonRole.AcceptRole)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    @property
    def success_count(self) -> int:
        """Anzahl der in dieser Dialogsitzung erfolgreich übernommenen Umsätze."""
        return self._success_count

    @property
    def transactions(self) -> tuple[BankTransaction, ...]:
        return tuple(self._transactions[row] for row in sorted(self._transactions))

    def load_csv(self, path: Path) -> None:
        """Liest eine Datei ausschließlich über den vorhandenen Parser."""
        self._table.setRowCount(0)
        self._proposals.clear()
        self._transactions.clear()
        self._row_blocked_reasons.clear()
        self._errors = ()
        self._file_name.setText(path.name)
        try:
            transactions = QontoCsvImporter().load(path)
        except BankCsvImportError as exc:
            self._errors = exc.errors
            self._error_label.setText("\n".join(exc.errors))
            self._summary.setText(
                "Die Datei konnte wegen Importfehlern nicht vollständig eingelesen "
                f"werden; {len(exc.errors)} zeilenbezogene Importfehler."
            )
            self._update_post_enabled()
            return

        self._error_label.clear()
        proposal_by_id = {
            proposal.transaction.external_transaction_id: proposal
            for proposal in build_booking_proposals(transactions)
        }
        ready_count = 0
        duplicate_count = 0
        duplicate_check_failures = 0
        for transaction in transactions:
            row = self._table.rowCount()
            self._table.insertRow(row)
            self._transactions[row] = transaction
            proposal = proposal_by_id.get(transaction.external_transaction_id)
            is_ready = transaction.import_validation_status is TransactionImportStatus.READY
            duplicate_id = None
            if is_ready:
                ready_count += 1
                try:
                    duplicate_id = self._duplicate_lookup(transaction)
                except Exception as exc:  # Ein fehlgeschlagener Check darf keine Buchung freigeben.
                    duplicate_id = f"Prüfung fehlgeschlagen: {exc}"
                    duplicate_check_failures += 1
                if duplicate_id is not None:
                    if not str(duplicate_id).startswith("Prüfung fehlgeschlagen:"):
                        duplicate_count += 1
            if proposal is not None:
                self._proposals[row] = proposal
            self._add_row(row, transaction, proposal, duplicate_id)

        invalid_count = len(transactions) - ready_count
        self._summary.setText(
            f"{len(transactions)} Umsätze eingelesen; "
            f"{ready_count - duplicate_count - duplicate_check_failures} "
            f"buchbar; {invalid_count} ungültig oder nicht abgewickelt; "
            f"{duplicate_count} bereits übernommen; "
            f"{duplicate_check_failures} Duplikatprüfungen fehlgeschlagen."
        )
        self._update_post_enabled()

    def _choose_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Bankumsätze auswählen",
            "",
            "CSV-Dateien (*.csv);;Alle Dateien (*)",
        )
        if path:
            self.load_csv(Path(path))

    def _add_row(
        self,
        row: int,
        transaction: BankTransaction,
        proposal: BankBookingProposal | None,
        duplicate_id: object | None,
    ) -> None:
        selectable = proposal is not None and duplicate_id is None
        checkbox = QCheckBox()
        checkbox.setEnabled(selectable)
        checkbox.stateChanged.connect(lambda _state: self._update_post_enabled())
        check_holder = QWidget()
        check_layout = QHBoxLayout(check_holder)
        check_layout.setContentsMargins(0, 0, 0, 0)
        check_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        check_layout.addWidget(checkbox)
        self._table.setCellWidget(row, 0, check_holder)

        date_edit = QDateEdit(QDate(transaction.booking_date.year,
                                    transaction.booking_date.month,
                                    transaction.booking_date.day))
        date_edit.setDisplayFormat("dd.MM.yyyy")
        date_edit.setCalendarPopup(True)
        date_edit.setEnabled(selectable)
        self._table.setCellWidget(row, 1, date_edit)
        if proposal is not None:
            date_edit.dateChanged.connect(
                lambda value, item=proposal, row_index=row:
                self._edit_date(item, value, row_index)
            )

        self._set_text(row, 2, transaction.counterparty or "")
        self._set_text(row, 3, transaction.reference or "")
        self._set_text(row, 4, format_german_amount(transaction.amount))

        contra = QComboBox()
        contra.addItem("Konto auswählen …", None)
        contra_accounts = sorted(
            self._accounts,
            key=lambda account: account.number,
        )
        for account in contra_accounts:
            contra.addItem(account_display_name(account), account.number)
        contra.setEnabled(selectable)
        if proposal is not None and proposal.counter_lines:
            initial_account = proposal.counter_lines[0].account_number
            if initial_account is not None:
                index = contra.findData(initial_account)
                if index >= 0:
                    contra.setCurrentIndex(index)
        if proposal is not None:
            self._counter_combos[row] = contra
            contra.currentIndexChanged.connect(
                lambda _index, item=proposal, combo=contra, row_index=row:
                self._edit_counter_account(item, combo, row_index)
            )
        split_button = QPushButton("Aufteilen …")
        split_button.setEnabled(selectable)
        if proposal is not None:
            split_button.clicked.connect(
                lambda _checked=False, item=proposal, row_index=row:
                self._edit_counter_lines(item, row_index)
            )
            self._counter_split_buttons[row] = split_button
        summary = QLabel()
        summary.setWordWrap(True)
        if proposal is not None:
            self._counter_summary_labels[row] = summary
        contra_layout = QVBoxLayout()
        first_line_layout = QHBoxLayout()
        first_line_layout.addWidget(contra, 1)
        first_line_layout.addWidget(split_button)
        contra_layout.addLayout(first_line_layout)
        contra_layout.addWidget(summary)
        contra_holder = QWidget()
        contra_holder.setLayout(contra_layout)
        self._table.setCellWidget(row, 5, contra_holder)
        # The cell contains a combo, a button and a status label in a vertical
        # layout; QTableWidget's default 30 px section clips them to a few px.
        self._table.setRowHeight(row, 76)

        description = QLineEdit(proposal.description if proposal is not None else "")
        description.setEnabled(selectable)
        self._table.setCellWidget(row, 6, description)
        if proposal is not None:
            description.textChanged.connect(
                lambda value, item=proposal, row_index=row:
                self._edit_description(item, value, row_index)
            )

        if duplicate_id is not None:
            reason = (
                f"Bereits übernommen (Buchung {duplicate_id})"
                if not str(duplicate_id).startswith("Prüfung fehlgeschlagen:")
                else str(duplicate_id)
            )
            self._row_blocked_reasons[row] = reason
        elif proposal is None:
            reason = f"Nicht abgewickelt (Status: {transaction.transaction_status})"
        else:
            reason = "Vorschlag prüfen"
        self._set_text(row, 7, reason)
        self._refresh_counter_display(row)
        self._refresh_row_status(row)

    def _refresh_row_status(self, row: int) -> None:
        proposal = self._proposals.get(row)
        if proposal is None:
            return
        if row in self._row_blocked_reasons:
            self._set_text(row, 7, self._row_blocked_reasons[row])
            return
        reason = "; ".join(proposal.validation_errors) or "Bereit zur Übernahme"
        difference = abs(proposal.transaction.amount) - sum(
            (line.amount for line in proposal.counter_lines), Decimal("0.00")
        )
        if difference != Decimal("0.00"):
            reason += f" Aufteilungsdifferenz: {format_german_amount(difference)} €."
        if self._may_match_manual_booking(row):
            reason += "; mögliche manuelle Doppelbuchung prüfen"
        self._set_text(row, 7, reason)
        checkbox = self._checkbox(row)
        if checkbox is not None:
            checkbox.setEnabled(not proposal.validation_errors)
            if proposal.validation_errors:
                checkbox.setChecked(False)
        self._update_post_enabled()

    def _edit_counter_account(
        self, proposal: BankBookingProposal, combo: QComboBox, row: int
    ) -> None:
        existing = proposal.counter_lines
        if existing:
            proposal.counter_lines = (
                CounterBookingLineProposal(combo.currentData(), existing[0].amount),
                *existing[1:],
            )
        else:
            proposal.counter_lines = (
                CounterBookingLineProposal(combo.currentData(), abs(proposal.transaction.amount)),
            )
        self._refresh_counter_display(row)
        self._refresh_row_status(row)

    def _edit_counter_lines(self, proposal: BankBookingProposal, row: int) -> None:
        dialog = CounterBookingLinesDialog(
            parent=self,
            bank_amount=proposal.transaction.amount,
            accounts=self._accounts,
            lines=proposal.counter_lines,
            amount_entry_factory=self._amount_entry_factory,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted or dialog.counter_lines is None:
            return
        proposal.counter_lines = dialog.counter_lines
        combo = self._counter_combos[row]
        combo.blockSignals(True)
        first_account = proposal.counter_lines[0].account_number
        combo.setCurrentIndex(combo.findData(first_account) if first_account else 0)
        combo.blockSignals(False)
        self._refresh_counter_display(row)
        self._refresh_row_status(row)

    def _refresh_counter_display(self, row: int) -> None:
        proposal = self._proposals.get(row)
        label = self._counter_summary_labels.get(row)
        if proposal is None or label is None:
            return
        total = sum((line.amount for line in proposal.counter_lines), Decimal("0.00"))
        difference = abs(proposal.transaction.amount) - total
        label.setText(
            f"{len(proposal.counter_lines)} Zeile(n); zugeordnet "
            f"{format_german_amount(total)} €; Rest {format_german_amount(difference)} €"
        )

    def _edit_description(self, proposal: BankBookingProposal, value: str, row: int) -> None:
        proposal.description = value
        self._refresh_row_status(row)

    def _edit_date(self, proposal: BankBookingProposal, value: QDate, row: int) -> None:
        proposal.booking_date = date(value.year(), value.month(), value.day())
        self._refresh_row_status(row)

    def _may_match_manual_booking(self, row: int) -> bool:
        transaction = self._transactions[row]
        bank_number = self._bank_account_combo.currentData()
        if not bank_number:
            return False
        proposal = self._proposals.get(row)
        comparison_date = proposal.booking_date if proposal is not None else transaction.booking_date
        for booking in self._journal:
            if booking.booking_date != comparison_date:
                continue
            if any(
                line.account_number == bank_number
                and line.amount == abs(transaction.amount)
                and line.side is (
                    EntrySide.DEBIT if transaction.amount > 0 else EntrySide.CREDIT
                )
                for line in booking.lines
            ):
                return True
        return False

    def _bank_account_changed(self, _index: int) -> None:
        account_number = self._bank_account_combo.currentData()
        for row, proposal in self._proposals.items():
            proposal.bank_account_number = account_number
            self._refresh_row_status(row)

    def _confirm_selected(self) -> None:
        selected = [
            (row, self._proposals[row])
            for row in sorted(self._proposals)
            if (checkbox := self._checkbox(row)) is not None
            and checkbox.isChecked()
            and self._proposals[row].is_valid
        ]
        if not selected:
            return
        answer = QMessageBox.question(
            self,
            "Bankumsätze buchen",
            f"Sollen {len(selected)} ausgewählte Bankumsätze jetzt als Buchungen "
            "im Hauptbuch gespeichert werden?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        for row, proposal in selected:
            try:
                booking = self._post_proposal(proposal, confirmed=True)
            except Exception as exc:
                self._set_text(row, 7, f"Fehler: {exc}")
                checkbox = self._checkbox(row)
                if checkbox is not None:
                    checkbox.setChecked(False)
                    checkbox.setEnabled(False)
            else:
                self._success_count += 1
                self._set_text(row, 7, f"Übernommen (Buchung {booking.booking_id})")
                checkbox = self._checkbox(row)
                if checkbox is not None:
                    checkbox.setChecked(False)
                    checkbox.setEnabled(False)
                for column in (1, 5, 6):
                    widget = self._table.cellWidget(row, column)
                    if widget is not None:
                        widget.setEnabled(False)
        self._update_post_enabled()
        if self._success_count:
            QMessageBox.information(
                self,
                "Übernahme abgeschlossen",
                f"{self._success_count} Bankumsätze wurden erfolgreich übernommen. "
                "Fehler sind in der jeweiligen Tabellenzeile markiert.",
            )

    def _update_post_enabled(self) -> None:
        bank_selected = self._bank_account_combo.currentData() is not None
        has_selected = any(
            (checkbox := self._checkbox(row)) is not None
            and checkbox.isChecked()
            and self._proposals[row].is_valid
            for row in self._proposals
        )
        self._post_button.setEnabled(bank_selected and has_selected)

    def _checkbox(self, row: int) -> QCheckBox | None:
        holder = self._table.cellWidget(row, 0)
        return holder.findChild(QCheckBox) if holder is not None else None

    def _set_text(self, row: int, column: int, text: str) -> None:
        item = QTableWidgetItem(text)
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self._table.setItem(row, column, item)


def _parse_amount_entry(entry: QLineEdit) -> Decimal:
    """Liest mit der bestehenden Buchungsmaskenlogik als Decimal."""
    return BookingFrame._parse_amount(
        entry.text(),
        normalized=bool(entry.property("amountNormalized")),
    )

"""PySide6-Dialog zur Erfassung der Eröffnungsbilanz."""

from decimal import Decimal, InvalidOperation

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from simpleob.amount_input import normalize_german_amount
from simpleob.domain.account import Account
from simpleob.domain.account_type import AccountType
from simpleob.domain.entry_side import EntrySide
from simpleob.domain.opening_balance import OpeningBalance
from simpleob.domain.opening_balance_item import OpeningBalanceItem


class OpeningBalanceDialog(QDialog):
    """Erfasst die Anfangsbestände einer Buchhaltung."""

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        accounts: tuple[Account, ...],
        excluded_account_numbers: set[str],
    ) -> None:
        super().__init__(parent)

        self.setWindowTitle("Eröffnungsbilanz")
        self.resize(800, 550)
        self.setMinimumSize(650, 450)

        self._accounts = self._filter_accounts(
            accounts=accounts,
            excluded_account_numbers=excluded_account_numbers,
        )
        self._accounts_by_display = {
            str(account): account
            for account in self._accounts
        }

        self._items: list[OpeningBalanceItem] = []

        self.result: OpeningBalance | None = None

        self._create_ui()
        self._update_totals()

    @staticmethod
    def _filter_accounts(
        *,
        accounts: tuple[Account, ...],
        excluded_account_numbers: set[str],
    ) -> tuple[Account, ...]:
        """Filtert die für die Eröffnungsbilanz zulässigen Konten."""

        return tuple(
            account
            for account in accounts
            if (
                account.is_active
                and account.number not in excluded_account_numbers
                and account.account_type
                in (
                    AccountType.ASSET,
                    AccountType.LIABILITY,
                    AccountType.EQUITY,
                )
            )
        )

    def _create_ui(self) -> None:
        """Erzeugt die Benutzeroberfläche."""

        layout = QVBoxLayout(self)

        title_label = QLabel("Eröffnungsbilanz")
        title_label.setStyleSheet(
            "font-size: 20px; font-weight: bold;"
        )
        layout.addWidget(title_label)

        info_label = QLabel(
            "Erfassen Sie nur Konten mit einem Anfangsbestand.\n"
            "Die Eingaben werden erst mit „Übernehmen“ verbucht.\n"
            "Bei Abbruch oder Schließen gehen alle Eingaben verloren. "
            "Eine spätere Fortsetzung ist nicht möglich."
        )
        info_label.setWordWrap(True)

        layout.addWidget(info_label)

        entry_layout = QHBoxLayout()

        account_layout = QVBoxLayout()
        account_layout.addWidget(QLabel("Konto"))

        self._account_combo = QComboBox()
        self._account_combo.addItem("")

        for account in self._accounts:
            self._account_combo.addItem(str(account))

        account_layout.addWidget(self._account_combo)
        entry_layout.addLayout(account_layout, 1)

        debit_layout = QVBoxLayout()
        debit_layout.addWidget(QLabel("Sollsaldo"))
        self._debit_entry = self._create_amount_entry()
        debit_layout.addWidget(self._debit_entry)
        entry_layout.addLayout(debit_layout)

        credit_layout = QVBoxLayout()
        credit_layout.addWidget(QLabel("Habensaldo"))
        self._credit_entry = self._create_amount_entry()
        credit_layout.addWidget(self._credit_entry)
        entry_layout.addLayout(credit_layout)

        add_button_layout = QVBoxLayout()
        add_button_layout.addWidget(QLabel(" "))

        add_button = QPushButton("Hinzufügen")
        add_button.clicked.connect(self._add_item)
        add_button_layout.addWidget(add_button)

        entry_layout.addLayout(add_button_layout)

        layout.addLayout(entry_layout)

        self._item_table = QTableWidget()
        self._item_table.setColumnCount(4)
        self._item_table.setHorizontalHeaderLabels(
            (
                "Konto",
                "Bezeichnung",
                "Sollsaldo",
                "Habensaldo",
            )
        )
        self._item_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self._item_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self._item_table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )

        header = self._item_table.horizontalHeader()
        header.setSectionResizeMode(
            0,
            QHeaderView.ResizeMode.ResizeToContents,
        )
        header.setSectionResizeMode(
            1,
            QHeaderView.ResizeMode.Stretch,
        )
        for column in (2, 3):
            header.setSectionResizeMode(
                column,
                QHeaderView.ResizeMode.ResizeToContents,
            )

        layout.addWidget(self._item_table, 1)

        remove_button = QPushButton("Position entfernen")
        remove_button.clicked.connect(self._remove_item)
        layout.addWidget(remove_button)

        self._debit_total_label = QLabel("Soll: 0,00 €")
        self._debit_total_label.setAlignment(
            Qt.AlignmentFlag.AlignRight
        )
        layout.addWidget(self._debit_total_label)

        self._credit_total_label = QLabel(
            "Haben: 0,00 €"
        )
        self._credit_total_label.setAlignment(
            Qt.AlignmentFlag.AlignRight
        )
        layout.addWidget(self._credit_total_label)

        self._difference_label = QLabel(
            "Differenz: 0,00 €"
        )
        self._difference_label.setAlignment(
            Qt.AlignmentFlag.AlignRight
        )
        layout.addWidget(self._difference_label)

        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        self._accept_button = QPushButton("Übernehmen")
        self._accept_button.clicked.connect(self._accept)
        self._accept_button.setEnabled(False)
        buttons_layout.addWidget(self._accept_button)

        cancel_button = QPushButton("Abbrechen")
        cancel_button.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_button)

        layout.addLayout(buttons_layout)

    def _add_item(self) -> None:
        """Fügt eine Eröffnungsposition hinzu."""

        account_display = (
            self._account_combo.currentText().strip()
        )

        if not account_display:
            QMessageBox.critical(
                self,
                "Eröffnungsbilanz",
                "Bitte wählen Sie ein Konto aus.",
            )
            return

        account = self._accounts_by_display[
            account_display
        ]

        if any(
            item.account.number == account.number
            for item in self._items
        ):
            QMessageBox.critical(
                self,
                "Eröffnungsbilanz",
                "Das Konto wurde bereits erfasst.",
            )
            return

        try:
            debit_amount = self._parse_amount(
                self._debit_entry.text()
            )
            credit_amount = self._parse_amount(
                self._credit_entry.text()
            )
        except ValueError as exc:
            QMessageBox.critical(
                self,
                "Eröffnungsbilanz",
                str(exc),
            )
            return

        if (
            debit_amount > Decimal("0.00")
            and credit_amount > Decimal("0.00")
        ):
            QMessageBox.critical(
                self,
                "Eröffnungsbilanz",
                "Geben Sie für ein Konto entweder einen Sollsaldo "
                "oder einen Habensaldo ein.",
            )
            return

        if (
            debit_amount == Decimal("0.00")
            and credit_amount == Decimal("0.00")
        ):
            QMessageBox.critical(
                self,
                "Eröffnungsbilanz",
                "Geben Sie einen Soll- oder Habensaldo größer als 0,00 € ein.",
            )
            return

        side = (
            EntrySide.DEBIT
            if debit_amount > Decimal("0.00")
            else EntrySide.CREDIT
        )
        amount = (
            debit_amount
            if side is EntrySide.DEBIT
            else credit_amount
        )

        item = OpeningBalanceItem(
            account=account,
            amount=amount,
            side=side,
        )
        self._items.append(item)

        row = self._item_table.rowCount()
        self._item_table.insertRow(row)

        account_item = QTableWidgetItem(account.number)
        name_item = QTableWidgetItem(account.name)
        debit_item = QTableWidgetItem(
            self._format_amount(amount)
            if side is EntrySide.DEBIT
            else ""
        )
        credit_item = QTableWidgetItem(
            self._format_amount(amount)
            if side is EntrySide.CREDIT
            else ""
        )
        for amount_item in (debit_item, credit_item):
            amount_item.setTextAlignment(
                Qt.AlignmentFlag.AlignRight
                | Qt.AlignmentFlag.AlignVCenter
            )

        self._item_table.setItem(
            row,
            0,
            account_item,
        )
        self._item_table.setItem(
            row,
            1,
            name_item,
        )
        self._item_table.setItem(
            row,
            2,
            debit_item,
        )
        self._item_table.setItem(
            row,
            3,
            credit_item,
        )

        self._account_combo.setCurrentIndex(0)
        self._debit_entry.clear()
        self._credit_entry.clear()

        self._update_totals()

    def _remove_item(self) -> None:
        """Entfernt die ausgewählte Eröffnungsposition."""

        row = self._item_table.currentRow()

        if row < 0:
            return

        account_item = self._item_table.item(
            row,
            0,
        )

        if account_item is None:
            return

        account_number = account_item.text()

        self._items = [
            item
            for item in self._items
            if item.account.number != account_number
        ]

        self._item_table.removeRow(row)

        self._update_totals()

    def _update_totals(self) -> None:
        """Berechnet Soll-, Haben- und Differenzsumme neu."""

        opening_balance = OpeningBalance(
            items=tuple(self._items),
        )

        total_debits = opening_balance.total_debits
        total_credits = opening_balance.total_credits
        difference = total_debits - total_credits

        self._debit_total_label.setText(
            "Soll: "
            f"{self._format_amount(total_debits)} €"
        )
        self._credit_total_label.setText(
            "Haben: "
            f"{self._format_amount(total_credits)} €"
        )
        self._difference_label.setText(
            "Differenz: "
            f"{self._format_amount(difference)} €"
        )

        self._accept_button.setEnabled(
            bool(self._items)
            and opening_balance.is_balanced
        )

    def _normalize_amount_entry(self, entry: QLineEdit) -> None:
        """Normalisiert den eingegebenen Anfangsbestand."""

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

    def _create_amount_entry(self) -> QLineEdit:
        entry = QLineEdit()
        entry.setAlignment(Qt.AlignmentFlag.AlignRight)
        entry.setMaximumWidth(150)
        entry.setPlaceholderText("0,00")
        entry.editingFinished.connect(
            lambda current_entry=entry: self._normalize_amount_entry(
                current_entry
            )
        )
        return entry

    @staticmethod
    def _parse_amount(
        value: str,
    ) -> Decimal:
        """Wandelt eine deutsche Betragseingabe in Decimal um."""

        normalized = value.strip()

        if not normalized:
            return Decimal("0.00")

        normalized = normalized.replace(".", "")
        normalized = normalized.replace(",", ".")

        try:
            amount = Decimal(normalized)
        except InvalidOperation as exc:
            raise ValueError(
                "Ungültiger Geldbetrag."
            ) from exc

        if amount < Decimal("0.00"):
            raise ValueError(
                "Negative Beträge sind nicht zulässig."
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
            .replace(",", "X")
            .replace(".", ",")
            .replace("X", ".")
        )

    def _accept(self) -> None:
        """Übernimmt die erfasste Eröffnungsbilanz."""

        opening_balance = OpeningBalance(
            items=tuple(self._items),
        )

        if not opening_balance.is_balanced:
            return

        self.result = opening_balance
        self.accept()

    def reject(self) -> None:
        """Fragt vor dem Verwerfen erfasster Positionen nach."""

        if self._items:
            answer = QMessageBox.question(
                self,
                "Eröffnungsbilanz abbrechen?",
                (
                    "Die bisher erfassten Positionen "
                    "werden nicht gespeichert.\n\n"
                    "Möchten Sie die Eingaben verwerfen?"
                ),
                (
                    QMessageBox.StandardButton.Yes
                    | QMessageBox.StandardButton.No
                ),
                QMessageBox.StandardButton.No,
            )

            if answer != QMessageBox.StandardButton.Yes:
                return

        super().reject()

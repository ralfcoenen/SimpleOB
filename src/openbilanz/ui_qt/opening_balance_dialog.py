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

from openbilanz.domain.account import Account
from openbilanz.domain.account_type import AccountType
from openbilanz.domain.opening_balance import OpeningBalance
from openbilanz.domain.opening_balance_item import OpeningBalanceItem


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
            "Erfassen Sie nur die Konten, "
            "für die ein Anfangsbestand vorhanden ist."
        )
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

        amount_layout = QVBoxLayout()
        amount_layout.addWidget(QLabel("Anfangsbestand"))

        self._amount_entry = QLineEdit()
        self._amount_entry.setAlignment(
            Qt.AlignmentFlag.AlignRight
        )
        self._amount_entry.setMaximumWidth(180)
        amount_layout.addWidget(self._amount_entry)

        entry_layout.addLayout(amount_layout)

        add_button_layout = QVBoxLayout()
        add_button_layout.addWidget(QLabel(" "))

        add_button = QPushButton("Hinzufügen")
        add_button.clicked.connect(self._add_item)
        add_button_layout.addWidget(add_button)

        entry_layout.addLayout(add_button_layout)

        layout.addLayout(entry_layout)

        self._item_table = QTableWidget()
        self._item_table.setColumnCount(3)
        self._item_table.setHorizontalHeaderLabels(
            (
                "Konto",
                "Bezeichnung",
                "Anfangsbestand",
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
        header.setSectionResizeMode(
            2,
            QHeaderView.ResizeMode.ResizeToContents,
        )

        layout.addWidget(self._item_table, 1)

        remove_button = QPushButton("Position entfernen")
        remove_button.clicked.connect(self._remove_item)
        layout.addWidget(remove_button)

        self._assets_label = QLabel("Aktiva: 0,00 €")
        self._assets_label.setAlignment(
            Qt.AlignmentFlag.AlignRight
        )
        layout.addWidget(self._assets_label)

        self._liabilities_label = QLabel(
            "Passiva: 0,00 €"
        )
        self._liabilities_label.setAlignment(
            Qt.AlignmentFlag.AlignRight
        )
        layout.addWidget(self._liabilities_label)

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
            amount = self._parse_amount(
                self._amount_entry.text()
            )
        except ValueError as exc:
            QMessageBox.critical(
                self,
                "Eröffnungsbilanz",
                str(exc),
            )
            return

        if amount == Decimal("0.00"):
            QMessageBox.critical(
                self,
                "Eröffnungsbilanz",
                "Der Anfangsbestand muss größer als 0,00 € sein.",
            )
            return

        item = OpeningBalanceItem(
            account=account,
            amount=amount,
        )
        self._items.append(item)

        row = self._item_table.rowCount()
        self._item_table.insertRow(row)

        account_item = QTableWidgetItem(account.number)
        name_item = QTableWidgetItem(account.name)
        amount_item = QTableWidgetItem(
            self._format_amount(amount)
        )
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
            amount_item,
        )

        self._account_combo.setCurrentIndex(0)
        self._amount_entry.clear()

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
        """Berechnet Aktiva, Passiva und Differenz neu."""

        opening_balance = OpeningBalance(
            items=tuple(self._items),
        )

        total_assets = opening_balance.total_assets
        total_liabilities = (
            opening_balance.total_liabilities_and_equity
        )
        difference = total_assets - total_liabilities

        self._assets_label.setText(
            "Aktiva: "
            f"{self._format_amount(total_assets)} €"
        )
        self._liabilities_label.setText(
            "Passiva: "
            f"{self._format_amount(total_liabilities)} €"
        )
        self._difference_label.setText(
            "Differenz: "
            f"{self._format_amount(difference)} €"
        )

        self._accept_button.setEnabled(
            bool(self._items)
            and opening_balance.is_balanced
        )

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

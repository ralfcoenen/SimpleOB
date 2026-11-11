"""Tabellarische Vorschau für die Umsatzsteuerverrechnung."""

from decimal import Decimal

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QHeaderView,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from simpleob.amount_input import format_german_amount
from simpleob.domain.booking import Booking
from simpleob.domain.money import ZERO
from simpleob.services.vat_reconciliation_service import (
    VatReconciliationProposal,
)


class VatReconciliationPreviewDialog(QDialog):
    """Zeigt Kontensalden und Buchungsvorschläge zur Prüfung an."""

    def __init__(
        self,
        parent,
        *,
        proposal: VatReconciliationProposal,
        clearing_account_number: str,
    ) -> None:
        super().__init__(parent)
        self._proposal = proposal
        self._clearing_account_number = clearing_account_number
        self.setWindowTitle("Umsatzsteuerverrechnung · Vorschau")

        available = self._available_geometry(parent)
        max_width = max(320, min(1100, available.width() - 48))
        max_height = max(300, min(700, available.height() - 100))
        self.setMaximumSize(max_width, max_height)
        self.setMinimumSize(min(660, max_width), min(460, max_height))
        self.resize(min(940, max_width), min(560, max_height))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 16)
        layout.setSpacing(10)

        heading = QLabel("Umsatzsteuerverrechnung")
        heading.setObjectName("vatReconciliationHeading")
        heading.setStyleSheet("font-size: 18px; font-weight: 600;")
        year = QLabel(f"Geschäftsjahr {proposal.fiscal_year.display_name}")
        year.setObjectName("vatReconciliationFiscalYear")
        layout.addWidget(heading)
        layout.addWidget(year)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(2, 4, 2, 4)
        content_layout.setSpacing(12)

        content_layout.addWidget(QLabel("Beteiligte Konten und Salden"))
        self.account_table = QTableWidget(0, 5, content)
        self.account_table.setObjectName("vatReconciliationAccounts")
        self.account_table.setHorizontalHeaderLabels(
            ("Konto", "Kontobezeichnung", "Sollsaldo", "Habensaldo", "Eröffnungsanteil")
        )
        self._prepare_table(self.account_table)
        self._populate_account_table(proposal)
        content_layout.addWidget(self.account_table)

        content_layout.addWidget(QLabel("Vorgeschlagene Buchungssätze"))
        self.booking_table = QTableWidget(0, 3, content)
        self.booking_table.setObjectName("vatReconciliationBookings")
        self.booking_table.setHorizontalHeaderLabels(
            ("Sollkonto", "Habenkonto", "Betrag")
        )
        self._prepare_table(self.booking_table)
        self._populate_booking_table(proposal)
        content_layout.addWidget(self.booking_table)

        self.result_label = QLabel(
            self._result_text(proposal.resulting_clearing_balance)
        )
        self.result_label.setObjectName("vatReconciliationResult")
        self.result_label.setWordWrap(True)
        self.result_label.setStyleSheet(
            "font-size: 17px; font-weight: 700; padding: 10px; "
            "border: 1px solid palette(mid); border-radius: 4px;"
        )
        content_layout.addWidget(self.result_label)

        existing_balance = format_german_amount(proposal.existing_clearing_balance)
        self.existing_balance_label = QLabel(
            f"Bisheriger Saldo Konto {clearing_account_number}: "
            f"{existing_balance} € (Soll positiv, Haben negativ)"
        )
        self.existing_balance_label.setWordWrap(True)
        content_layout.addWidget(self.existing_balance_label)

        self.hint_label = QLabel(
            "Die Berechnung verwendet ausschließlich vorhandene "
            "Hauptbuchsalden. Bitte prüfen Sie selbst die sachliche und "
            "zeitliche Zuordnung der Vorauszahlungen und Erstattungen "
            "zum angezeigten Geschäftsjahr. Das Geschäftsjahr bleibt "
            "nach dieser Verrechnung offen. Werden anschließend weitere "
            "umsatzsteuerrelevante Buchungen vorgenommen, kann eine "
            "erneute Umsatzsteuerverrechnung erforderlich sein."
        )
        self.hint_label.setObjectName("vatReconciliationResponsibilityHint")
        self.hint_label.setWordWrap(True)
        self.hint_label.setStyleSheet(
            "padding: 9px; background: palette(alternate-base); "
            "border: 1px solid palette(mid); border-radius: 4px;"
        )
        content_layout.addWidget(self.hint_label)
        content_layout.addStretch(1)
        scroll.setWidget(content)
        layout.addWidget(scroll, 1)

        buttons = QDialogButtonBox(self)
        self.cancel_button = QPushButton("Abbrechen", buttons)
        self.apply_button = QPushButton("Buchungen übernehmen", buttons)
        self.apply_button.setObjectName("vatReconciliationApply")
        self.apply_button.setEnabled(bool(proposal.bookings))
        buttons.addButton(
            self.cancel_button,
            QDialogButtonBox.ButtonRole.RejectRole,
        )
        buttons.addButton(
            self.apply_button,
            QDialogButtonBox.ButtonRole.AcceptRole,
        )
        self.cancel_button.clicked.connect(self.reject)
        self.apply_button.clicked.connect(self.accept)
        layout.addWidget(buttons)

    @staticmethod
    def _available_geometry(parent):
        screen = parent.screen() if parent is not None else None
        if screen is None:
            screen = QApplication.primaryScreen()
        if screen is None:
            return QSize(1024, 768)
        return screen.availableGeometry()

    @staticmethod
    def _prepare_table(table: QTableWidget) -> None:
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        table.setWordWrap(False)
        table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setMinimumSectionSize(75)
        table.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )

    def _populate_account_table(self, proposal: VatReconciliationProposal) -> None:
        self.account_table.setRowCount(len(proposal.account_balances))
        for row, balance in enumerate(proposal.account_balances):
            opening = self._opening_text(balance.opening_balance)
            values = (
                balance.account_number,
                balance.account_name,
                self._money(balance.debit_balance),
                self._money(balance.credit_balance),
                opening,
            )
            self._insert_row(self.account_table, row, values, numeric_columns={2, 3, 4})
        header = self.account_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for column in (2, 3, 4):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        self._fit_table_height(self.account_table)

    def _populate_booking_table(self, proposal: VatReconciliationProposal) -> None:
        account_names = {
            balance.account_number: balance.account_name
            for balance in proposal.account_balances
        }
        rows: list[tuple[str, str, Decimal]] = []
        for booking in proposal.bookings:
            rows.extend(self._booking_rows(booking, account_names))
        self.booking_table.setRowCount(len(rows))
        for row, (debit, credit, amount) in enumerate(rows):
            self._insert_row(
                self.booking_table,
                row,
                (debit, credit, self._money(amount)),
                numeric_columns={2},
            )
        header = self.booking_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self._fit_table_height(self.booking_table)

    @staticmethod
    def _booking_rows(
        booking: Booking,
        account_names: dict[str, str],
    ) -> list[tuple[str, str, Decimal]]:
        debits = [[line.account_number, line.amount] for line in booking.debit_lines]
        credits = [[line.account_number, line.amount] for line in booking.credit_lines]
        rows: list[tuple[str, str, Decimal]] = []
        debit_index = credit_index = 0
        while debit_index < len(debits) and credit_index < len(credits):
            debit_number, debit_remaining = debits[debit_index]
            credit_number, credit_remaining = credits[credit_index]
            amount = min(debit_remaining, credit_remaining)
            rows.append(
                (
                    VatReconciliationPreviewDialog._account_label(
                        debit_number, account_names
                    ),
                    VatReconciliationPreviewDialog._account_label(
                        credit_number, account_names
                    ),
                    amount,
                )
            )
            debits[debit_index][1] -= amount
            credits[credit_index][1] -= amount
            if debits[debit_index][1] == ZERO:
                debit_index += 1
            if credits[credit_index][1] == ZERO:
                credit_index += 1
        return rows

    @staticmethod
    def _account_label(number: str, account_names: dict[str, str]) -> str:
        name = account_names.get(number)
        return f"{number} · {name}" if name else number

    @staticmethod
    def _insert_row(
        table: QTableWidget,
        row: int,
        values: tuple[str, ...],
        *,
        numeric_columns: set[int],
    ) -> None:
        for column, value in enumerate(values):
            item = QTableWidgetItem(value)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            item.setToolTip(value)
            if column in numeric_columns:
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                )
            table.setItem(row, column, item)

    @staticmethod
    def _fit_table_height(table: QTableWidget) -> None:
        table.resizeRowsToContents()
        header_height = table.horizontalHeader().sizeHint().height()
        row_height = sum(table.rowHeight(row) for row in range(table.rowCount()))
        table.setFixedHeight(header_height + row_height + 8)

    @staticmethod
    def _money(amount: Decimal) -> str:
        return f"{format_german_amount(amount)} €"

    @classmethod
    def _opening_text(cls, amount: Decimal) -> str:
        if amount == ZERO:
            return "—"
        side = "Soll" if amount > ZERO else "Haben"
        return f"{format_german_amount(abs(amount))} € {side}"

    def _result_text(self, amount: Decimal) -> str:
        if amount > ZERO:
            label = "Umsatzsteuerforderung"
            formatted = self._money(amount)
            side = "Sollsaldo"
        elif amount < ZERO:
            label = "Umsatzsteuerverbindlichkeit"
            formatted = self._money(-amount)
            side = "Habensaldo"
        else:
            return "Nullsaldo · keine Forderung und keine Verbindlichkeit"
        return f"{label} auf Konto {self._clearing_account_number}: {formatted} {side}"

"""Dialog zur Erfassung einer Zahlung auf einen oder mehrere Rechnungs-OPs."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHeaderView,
    QLineEdit,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from simpleob.amount_input import parse_german_amount
from simpleob.date_input import parse_german_date
from simpleob.domain.open_item_payment import PaymentDirection
from simpleob.services.open_item_payment_service import OpenItemPaymentService


class OpenItemPaymentDialog(QDialog):
    """Erfasst eine einzelne Zahlung mit ausdrücklichen OP-Zuordnungen."""

    def __init__(
        self,
        parent,
        *,
        company_id: UUID,
        fiscal_year,
        service: OpenItemPaymentService,
        accounts: tuple,
    ) -> None:
        super().__init__(parent)
        self._company_id = company_id
        self._fiscal_year = fiscal_year
        self._service = service
        self._invoices = service.list_open_invoices(company_id)
        self._partner_choices: list[tuple[PaymentDirection, UUID]] = []
        self._visible_invoices = ()
        self.setWindowTitle("Zahlung auf Rechnungen erfassen")
        self.resize(780, 520)

        form = QFormLayout()
        self._direction_box = QComboBox()
        self._direction_box.addItem(
            "Kundenzahlung", PaymentDirection.CUSTOMER_RECEIPT.value
        )
        self._direction_box.addItem(
            "Lieferantenzahlung", PaymentDirection.SUPPLIER_PAYMENT.value
        )
        form.addRow("Zahlungsrichtung", self._direction_box)

        self._partner_box = QComboBox()
        form.addRow("Geschäftspartner", self._partner_box)

        permitted_accounts = service.payment_account_numbers(company_id)
        self._account_box = QComboBox()
        for account in accounts:
            if account.is_active and account.number in permitted_accounts:
                self._account_box.addItem(
                    f"{account.number} – {account.name}", account.number
                )
        form.addRow("Bank-/Kassenkonto", self._account_box)

        today = date.today().strftime("%d.%m.%Y")
        self._payment_date = QLineEdit(today)
        self._booking_date = QLineEdit(today)
        self._amount = QLineEdit()
        self._amount.setPlaceholderText("0,00")
        self._voucher = QLineEdit()
        self._description = QLineEdit()
        form.addRow("Tatsächliches Zahlungsdatum", self._payment_date)
        form.addRow("Buchungsdatum", self._booking_date)
        form.addRow("Zahlungsbetrag gesamt", self._amount)
        form.addRow("Belegnummer (optional)", self._voucher)
        form.addRow("Buchungstext (optional)", self._description)

        self._allocations_table = QTableWidget(0, 3)
        self._allocations_table.setHorizontalHeaderLabels(
            ("Rechnung", "Offener Betrag", "Zuordnungsbetrag")
        )
        self._allocations_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self._allocations_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        self._allocations_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.ResizeToContents
        )

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._post_payment)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self._allocations_table)
        layout.addWidget(buttons)
        self._buttons = buttons
        self._direction_box.currentIndexChanged.connect(self._refresh_partners)
        self._partner_box.currentIndexChanged.connect(self._refresh_invoice_rows)
        self._refresh_partners()
        self._buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(
            bool(self._invoices) and self._account_box.count() > 0
        )

    def _refresh_partners(self, *_args: object) -> None:
        direction = PaymentDirection(self._direction_box.currentData())
        choices: dict[UUID, str] = {}
        for invoice in self._invoices:
            if invoice.direction is direction:
                choices[invoice.partner_id] = invoice.partner_name
        self._partner_choices = sorted(
            ((direction, partner_id) for partner_id in choices),
            key=lambda choice: choices[choice[1]].casefold(),
        )
        self._partner_box.blockSignals(True)
        self._partner_box.clear()
        for direction, partner_id in self._partner_choices:
            self._partner_box.addItem(choices[partner_id], partner_id)
        self._partner_box.blockSignals(False)
        self._refresh_invoice_rows()

    def _refresh_invoice_rows(self, *_args: object) -> None:
        direction = PaymentDirection(self._direction_box.currentData())
        partner_id = UUID(str(self._partner_box.currentData())) if self._partner_box.count() else None
        self._visible_invoices = tuple(
            invoice
            for invoice in self._invoices
            if invoice.direction is direction and invoice.partner_id == partner_id
        )
        self._allocations_table.setRowCount(len(self._visible_invoices))
        for row, invoice in enumerate(self._visible_invoices):
            label = f"{invoice.document_number} – {invoice.document_date:%d.%m.%Y}"
            self._allocations_table.setItem(row, 0, QTableWidgetItem(label))
            self._allocations_table.setItem(
                row, 1, QTableWidgetItem(f"{invoice.open_amount:.2f} EUR")
            )
            amount_item = QTableWidgetItem()
            amount_item.setData(Qt.ItemDataRole.UserRole, invoice.open_item_id)
            amount_item.setToolTip("Zuordnungsbetrag für diese Rechnung eingeben")
            self._allocations_table.setItem(row, 2, amount_item)

    def _read_allocations(self) -> tuple[tuple[UUID, Decimal], ...]:
        allocations = []
        for row in range(self._allocations_table.rowCount()):
            item = self._allocations_table.item(row, 2)
            if item is None or not item.text().strip():
                continue
            allocation_amount = parse_german_amount(item.text())
            if allocation_amount <= 0:
                raise ValueError("Zuordnungsbeträge müssen größer als 0,00 sein.")
            allocations.append(
                (
                    UUID(str(item.data(Qt.ItemDataRole.UserRole))),
                    allocation_amount,
                )
            )
        if not allocations:
            raise ValueError("Mindestens eine Rechnung muss zugeordnet werden.")
        return tuple(allocations)

    def _post_payment(self) -> None:
        try:
            amount: Decimal = parse_german_amount(self._amount.text())
            allocations = self._read_allocations()
            allocation_total = sum(
                (allocation for _, allocation in allocations), start=Decimal("0.00")
            )
            if allocation_total != amount:
                raise ValueError(
                    f"Die Zuordnungen ergeben {allocation_total:.2f} EUR; "
                    f"der Zahlungsbetrag beträgt {amount:.2f} EUR."
                )
            invoices_by_id = {
                invoice.open_item_id: invoice for invoice in self._visible_invoices
            }
            lines = "\n".join(
                f"{invoices_by_id[open_item_id].document_number}: "
                f"{allocation:.2f} EUR"
                for open_item_id, allocation in allocations
            )
            confirmation = QMessageBox.question(
                self,
                "Zahlung bestätigen",
                f"Zahlung über {amount:.2f} EUR buchen und wie folgt zuordnen?\n\n{lines}",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if confirmation != QMessageBox.StandardButton.Yes:
                return
            self._service.post_payment_allocations(
                company_id=self._company_id,
                fiscal_year=self._fiscal_year,
                partner_id=UUID(str(self._partner_box.currentData())),
                direction=PaymentDirection(self._direction_box.currentData()),
                amount=amount,
                allocations=allocations,
                payment_date=parse_german_date(self._payment_date.text()),
                booking_date=parse_german_date(self._booking_date.text()),
                cash_bank_account_number=self._account_box.currentData(),
                voucher_no=self._voucher.text() or None,
                description=self._description.text() or None,
            )
        except Exception as exc:
            QMessageBox.critical(self, "Zahlung nicht gebucht", str(exc))
            return
        self.accept()

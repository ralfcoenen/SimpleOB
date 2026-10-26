"""Dialog zur Erfassung einer Zahlung auf einen Rechnungs-OP."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
)

from simpleob.amount_input import parse_german_amount
from simpleob.date_input import parse_german_date
from simpleob.domain.open_item_payment import (
    PaymentDirection,
)
from simpleob.services.open_item_payment_service import OpenItemPaymentService


class OpenItemPaymentDialog(QDialog):
    """Erfasst eine einzelne Zahlung zu einer offenen Rechnung."""

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
        self.setWindowTitle("Zahlung auf Rechnung erfassen")
        self.resize(560, 220)

        form = QFormLayout()
        self._invoice_box = QComboBox()
        for invoice in self._invoices:
            kind = (
                "Kundenrechnung"
                if invoice.direction is PaymentDirection.CUSTOMER_RECEIPT
                else "Lieferantenrechnung"
            )
            label = (
                f"{kind}: {invoice.document_number} – {invoice.partner_name} – "
                f"offen {invoice.open_amount:.2f} EUR"
            )
            self._invoice_box.addItem(label, invoice.open_item_id)
        form.addRow("Rechnungs-OP", self._invoice_box)

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
        form.addRow("Zahlungsbetrag", self._amount)
        form.addRow("Belegnummer (optional)", self._voucher)
        form.addRow("Buchungstext (optional)", self._description)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._post_payment)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)
        self._buttons = buttons
        self._buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(
            bool(self._invoices) and self._account_box.count() > 0
        )

    def _post_payment(self) -> None:
        try:
            invoice_id = self._invoice_box.currentData()
            invoice = next(
                item for item in self._invoices if item.open_item_id == invoice_id
            )
            amount: Decimal = parse_german_amount(self._amount.text())
            self._service.post_payment(
                company_id=self._company_id,
                fiscal_year=self._fiscal_year,
                partner_id=invoice.partner_id,
                open_item_id=invoice.open_item_id,
                direction=invoice.direction,
                amount=amount,
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

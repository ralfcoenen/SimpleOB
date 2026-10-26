"""Dialog für eine manuelle Verrechnung von Rechnungs- und Guthaben-OP."""

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
from simpleob.database.business_partner_repository import BusinessPartnerRepository
from simpleob.date_input import parse_german_date
from simpleob.domain.open_item_offset import OffsetDirection
from simpleob.services.open_item_offset_service import OpenItemOffsetService


class OpenItemOffsetDialog(QDialog):
    """Erfasst und bestätigt eine Verrechnung zweier einzelner OPs."""

    def __init__(
        self,
        parent,
        *,
        company_id: UUID,
        fiscal_year,
        service: OpenItemOffsetService,
        partner_repository: BusinessPartnerRepository,
    ) -> None:
        super().__init__(parent)
        self._company_id = company_id
        self._fiscal_year = fiscal_year
        self._service = service
        self._partner_repository = partner_repository
        self.setWindowTitle("Guthaben mit Rechnung verrechnen")
        self.resize(640, 280)

        form = QFormLayout()
        self._direction_box = QComboBox()
        self._direction_box.addItem("Kundenguthaben", OffsetDirection.CUSTOMER.value)
        self._direction_box.addItem("Lieferantenguthaben", OffsetDirection.SUPPLIER.value)
        self._partner_box = QComboBox()
        self._invoice_box = QComboBox()
        self._credit_box = QComboBox()
        self._amount = QLineEdit()
        self._amount.setPlaceholderText("0,00")
        today = date.today().strftime("%d.%m.%Y")
        self._settlement_date = QLineEdit(today)
        self._booking_date = QLineEdit(today)
        self._description = QLineEdit()

        form.addRow("Guthabenart", self._direction_box)
        form.addRow("Geschäftspartner", self._partner_box)
        form.addRow("Rechnungs-OP", self._invoice_box)
        form.addRow("Guthaben-OP", self._credit_box)
        form.addRow("Verrechnungsbetrag", self._amount)
        form.addRow("Verrechnungsdatum", self._settlement_date)
        form.addRow("Buchungsdatum", self._booking_date)
        form.addRow("Buchungstext (optional)", self._description)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._post_offset)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)
        self._buttons = buttons
        self._direction_box.currentIndexChanged.connect(self._refresh_partners)
        self._partner_box.currentIndexChanged.connect(self._refresh_open_items)
        self._refresh_partners()

    def _refresh_partners(self, *_args: object) -> None:
        direction = OffsetDirection(self._direction_box.currentData())
        is_customer = direction is OffsetDirection.CUSTOMER
        partners = self._partner_repository.list_for_company(
            self._company_id,
            customers_only=is_customer,
            suppliers_only=not is_customer,
        )
        self._partner_box.blockSignals(True)
        self._partner_box.clear()
        for partner in partners:
            self._partner_box.addItem(partner.name, str(partner.partner_id))
        self._partner_box.blockSignals(False)
        self._refresh_open_items()

    def _refresh_open_items(self, *_args: object) -> None:
        self._invoice_box.clear()
        self._credit_box.clear()
        self._buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)
        partner_value = self._partner_box.currentData()
        if partner_value is None:
            return
        partner_id = UUID(str(partner_value))
        direction = OffsetDirection(self._direction_box.currentData())
        invoices = self._service.list_open_invoices(
            company_id=self._company_id,
            partner_id=partner_id,
            direction=direction,
        )
        credits = self._service.list_open_credits(
            company_id=self._company_id,
            partner_id=partner_id,
            direction=direction,
        )
        for invoice in invoices:
            self._invoice_box.addItem(
                f"{invoice.document_number} – offen {invoice.open_amount:.2f} EUR",
                str(invoice.open_item_id),
            )
        for credit in credits:
            self._credit_box.addItem(
                f"{credit.document_number} – verfügbar {credit.available_amount:.2f} EUR",
                str(credit.open_item_id),
            )
        self._buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(
            bool(invoices) and bool(credits)
        )

    def _post_offset(self) -> None:
        try:
            amount: Decimal = parse_german_amount(self._amount.text())
            invoice_label = self._invoice_box.currentText()
            credit_label = self._credit_box.currentText()
            confirmation = QMessageBox.question(
                self,
                "Verrechnung bestätigen",
                f"{amount:.2f} EUR vom Guthaben „{credit_label}“ mit "
                f"„{invoice_label}“ verrechnen?\n\n"
                "Es wird eine Umbuchung zwischen den OP-Konten erzeugt; "
                "es entsteht keine Bank- oder Kassenbewegung.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if confirmation != QMessageBox.StandardButton.Yes:
                return
            self._service.post_offset(
                company_id=self._company_id,
                fiscal_year=self._fiscal_year,
                partner_id=UUID(str(self._partner_box.currentData())),
                direction=OffsetDirection(self._direction_box.currentData()),
                invoice_open_item_id=UUID(str(self._invoice_box.currentData())),
                credit_open_item_id=UUID(str(self._credit_box.currentData())),
                amount=amount,
                settlement_date=parse_german_date(self._settlement_date.text()),
                booking_date=parse_german_date(self._booking_date.text()),
                description=self._description.text() or None,
            )
        except Exception as exc:
            QMessageBox.critical(self, "Verrechnung nicht gebucht", str(exc))
            return
        self.accept()

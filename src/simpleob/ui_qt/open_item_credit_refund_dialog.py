"""Dialog zum Auszahlen oder Erstatten eines konkreten Guthaben-OPs."""

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

from simpleob.amount_input import format_german_amount, parse_german_amount
from simpleob.database.business_partner_repository import BusinessPartnerRepository
from simpleob.date_input import GermanDateEdit, format_german_date
from simpleob.domain.open_item_offset import CreditOffsetSummary, OffsetDirection
from simpleob.services.open_item_credit_refund_service import (
    OpenItemCreditRefundService,
)
from simpleob.services.open_item_offset_service import OpenItemOffsetService


class OpenItemCreditRefundDialog(QDialog):
    """Erfasst eine bestätigte Rückerstattung für genau einen Guthaben-OP."""

    def __init__(
        self,
        parent,
        *,
        company_id: UUID,
        fiscal_year,
        service: OpenItemCreditRefundService,
        offset_service: OpenItemOffsetService,
        partner_repository: BusinessPartnerRepository,
        accounts: tuple,
    ) -> None:
        super().__init__(parent)
        self._company_id = company_id
        self._fiscal_year = fiscal_year
        self._service = service
        self._offset_service = offset_service
        self._partner_repository = partner_repository
        self._credits: dict[str, CreditOffsetSummary] = {}
        self.setWindowTitle("Guthaben erstatten")
        self.resize(700, 360)

        form = QFormLayout()
        self._direction_box = QComboBox()
        self._direction_box.addItem("Kundenguthaben auszahlen", OffsetDirection.CUSTOMER.value)
        self._direction_box.addItem("Lieferantenerstattung erfassen", OffsetDirection.SUPPLIER.value)
        self._partner_box = QComboBox()
        self._credit_box = QComboBox()
        self._account_box = QComboBox()
        allowed_accounts = service.cash_bank_account_numbers(company_id)
        for account in accounts:
            if account.is_active and account.number in allowed_accounts:
                self._account_box.addItem(
                    f"{account.number} – {account.name}", account.number
                )

        self._amount = QLineEdit()
        self._amount.setPlaceholderText("0,00")
        self._refund_date = GermanDateEdit(value=date.today())
        self._booking_date = GermanDateEdit(value=date.today())
        form.addRow("Geschäftsvorfall", self._direction_box)
        form.addRow("Geschäftspartner", self._partner_box)
        form.addRow("Offenes Guthaben", self._credit_box)
        form.addRow("Bank-/Kassenkonto", self._account_box)
        form.addRow("Rückerstattungsbetrag", self._amount)
        form.addRow("Tatsächliches Zahlungs-/Erstattungsdatum", self._refund_date)
        form.addRow("Hauptbuch-Buchungsdatum", self._booking_date)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._post_refund)
        buttons.rejected.connect(self.reject)
        self._ok_button = buttons.button(QDialogButtonBox.StandardButton.Ok)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)
        self._direction_box.currentIndexChanged.connect(self._refresh_partners)
        self._partner_box.currentIndexChanged.connect(self._refresh_credits)
        self._amount.textChanged.connect(self._update_submit_state)
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
        self._refresh_credits()

    def _refresh_credits(self, *_args: object) -> None:
        self._credit_box.clear()
        self._credits.clear()
        partner_value = self._partner_box.currentData()
        if partner_value is None:
            self._update_submit_state()
            return
        direction = OffsetDirection(self._direction_box.currentData())
        credits = self._offset_service.list_open_credits(
            company_id=self._company_id,
            partner_id=UUID(str(partner_value)),
            direction=direction,
        )
        for credit in credits:
            key = str(credit.open_item_id)
            self._credits[key] = credit
            origin = (
                "Rechnungsstorno"
                if credit.document_number.startswith("Storno ")
                else "Gutschrift"
            )
            self._credit_box.addItem(
                f"{origin} {credit.document_number.removeprefix('Storno ')} · "
                f"verfügbar {format_german_amount(credit.available_amount)} EUR",
                key,
            )
        self._update_submit_state()

    def _update_submit_state(self, *_args: object) -> None:
        self._ok_button.setEnabled(
            self._partner_box.count() > 0
            and self._credit_box.count() > 0
            and self._account_box.count() > 0
        )

    def _post_refund(self) -> None:
        try:
            partner_id = self._partner_box.currentData()
            credit_id = self._credit_box.currentData()
            account_number = self._account_box.currentData()
            if partner_id is None or credit_id is None:
                raise ValueError("Bitte einen Geschäftspartner und ein Guthaben auswählen.")
            if account_number is None:
                raise ValueError("Bitte ein aktives Bank- oder Kassenkonto auswählen.")
            credit = self._credits.get(str(credit_id))
            if credit is None:
                raise ValueError("Das ausgewählte offene Guthaben ist nicht mehr verfügbar.")
            amount = parse_german_amount(self._amount.text())
            if amount <= Decimal("0.00"):
                raise ValueError("Der Rückerstattungsbetrag muss größer als 0,00 sein.")
            if amount > credit.available_amount:
                raise ValueError(
                    "Der Rückerstattungsbetrag übersteigt den verfügbaren Rest "
                    f"von {format_german_amount(credit.available_amount)} EUR."
                )
            refund_date = self._refund_date.date_value()
            booking_date = self._booking_date.date_value()
            direction = OffsetDirection(self._direction_box.currentData())
            partner_name = self._partner_box.currentText()
            account_label = self._account_box.currentText()
            scenario = (
                "Kundenguthaben auszahlen"
                if direction is OffsetDirection.CUSTOMER
                else "Lieferantenerstattung erfassen"
            )
            origin = (
                "Rechnungsstorno"
                if credit.document_number.startswith("Storno ")
                else "Gutschrift"
            )
            confirmation = QMessageBox.question(
                self,
                "Rückerstattung bestätigen",
                f"{scenario}\n"
                f"Geschäftspartner: {partner_name}\n"
                f"Guthaben-OP: {origin} {credit.document_number.removeprefix('Storno ')} "
                f"(verfügbar {format_german_amount(credit.available_amount)} EUR)\n"
                f"Rückerstattungsbetrag: {format_german_amount(amount)} EUR\n"
                f"Bank-/Kassenkonto: {account_label}\n"
                f"Tatsächliches Zahlungs-/Erstattungsdatum: {format_german_date(refund_date)}\n"
                f"Buchungsdatum: {format_german_date(booking_date)}\n\n"
                "Die Rückerstattung wird dem ausgewählten Guthaben-OP zugeordnet.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if confirmation != QMessageBox.StandardButton.Yes:
                return
            self._service.post_refund(
                company_id=self._company_id,
                fiscal_year=self._fiscal_year,
                partner_id=UUID(str(partner_id)),
                open_item_id=UUID(str(credit_id)),
                direction=direction,
                amount=amount,
                refund_date=refund_date,
                booking_date=booking_date,
                cash_bank_account_number=str(account_number),
            )
        except Exception as exc:
            QMessageBox.critical(self, "Rückerstattung nicht gebucht", str(exc))
            return
        self.accept()

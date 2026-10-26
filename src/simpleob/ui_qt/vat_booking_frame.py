"""PySide6-Eingabemaske für Rechnungen mit Umsatzsteuer."""

from collections.abc import Callable
from datetime import date
from decimal import Decimal, InvalidOperation
from uuid import UUID

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from simpleob.amount_input import normalize_german_amount
from simpleob.database.business_partner_repository import BusinessPartnerRepository
from simpleob.date_input import (
    normalize_german_date,
    parse_german_date,
)
from simpleob.domain.account import Account
from simpleob.domain.account_type import AccountType
from simpleob.domain.booking import Booking
from simpleob.domain.payable_invoice import DuplicateSupplierInvoiceError
from simpleob.domain.vat_accounts import VatAccounts
from simpleob.domain.vat_booking_item import VatBookingItem
from simpleob.services.vat_booking_service import (
    VatBookingService,
)
from simpleob.ui_qt.business_partner_dialog import BusinessPartnerDialog

_INPUT_INVOICE = "Eingangsrechnung"
_OUTPUT_INVOICE = "Ausgangsrechnung"
_CUSTOMER_CREDIT_NOTE = "Kundengutschrift"
_SUPPLIER_CREDIT_NOTE = "Lieferantengutschrift"

_TAX_RATES = ("0 %", "7 %", "19 %")


class VatBookingFrame(QWidget):
    """Erfasst Eingangs- und Ausgangsrechnungen mit Umsatzsteuer."""

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        accounts: tuple[Account, ...],
        vat_accounts: VatAccounts,
        on_booking_created: Callable[[Booking], None],
        company_id: UUID | None = None,
        partner_repository: BusinessPartnerRepository | None = None,
        on_receivable_invoice_created: Callable[..., None] | None = None,
        on_payable_invoice_created: Callable[..., None] | None = None,
    ) -> None:
        super().__init__(parent)

        self._accounts = accounts
        self._vat_accounts = vat_accounts
        self._on_booking_created = on_booking_created
        self._vat_booking_service = VatBookingService()
        self._enabled = True
        self._company_id = company_id
        self._partner_repository = partner_repository
        self._on_receivable_invoice_created = on_receivable_invoice_created
        self._on_payable_invoice_created = on_payable_invoice_created

        self._accounts_by_display_name = {
            self._account_display_name(account): account
            for account in accounts
        }

        self._accounts_by_number = {
            account.number: account
            for account in accounts
        }

        self._account_display_names = tuple(
            self._accounts_by_display_name
        )

        self._position_rows: list[dict[str, object]] = []

        self._create_ui()

    def _create_ui(self) -> None:
        """Erzeugt die Rechnungserfassung."""

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        form = QFormLayout()
        form.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow
        )

        self._invoice_type_box = QComboBox()
        self._invoice_type_box.addItems(
            (
                _INPUT_INVOICE,
                _OUTPUT_INVOICE,
                _CUSTOMER_CREDIT_NOTE,
                _SUPPLIER_CREDIT_NOTE,
            )
        )
        self._invoice_type_box.setCurrentText(
            _INPUT_INVOICE
        )
        form.addRow(
            "Rechnungsart",
            self._invoice_type_box,
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
        self._voucher_no_label = QLabel("Belegnummer")
        form.addRow(self._voucher_no_label, self._voucher_no_entry)

        self._on_account = QCheckBox("Rechnung auf Ziel")
        self._on_account.setVisible(False)
        self._on_account_label = QLabel("Forderung")
        form.addRow(self._on_account_label, self._on_account)
        self._partner_box = QComboBox()
        self._partner_box.setVisible(False)
        self._partner_add_button = QPushButton("Geschäftspartner verwalten")
        self._partner_add_button.setVisible(False)
        partner_row = QHBoxLayout()
        partner_row.addWidget(self._partner_box)
        partner_row.addWidget(self._partner_add_button)
        self._partner_label = QLabel("Geschäftspartner")
        form.addRow(self._partner_label, partner_row)
        self._due_date_entry = QLineEdit(date.today().strftime("%d.%m.%Y"))
        self._due_date_entry.setMaximumWidth(140)
        self._due_date_entry.setVisible(False)
        form.addRow("Fällig am", self._due_date_entry)
        self._refresh_customer_list()
        self._partner_add_button.clicked.connect(self._manage_partners)

        self._description_entry = QLineEdit()
        form.addRow(
            "Buchungstext",
            self._description_entry,
        )

        self._counter_account_box = QComboBox()
        self._counter_account_box.setEditable(True)
        self._counter_account_box.addItems(
            self._account_display_names
        )
        self._counter_account_box.setCurrentIndex(-1)
        self._counter_account_box.setInsertPolicy(
            QComboBox.InsertPolicy.NoInsert
        )
        form.addRow(
            "Gegenkonto",
            self._counter_account_box,
        )

        layout.addLayout(form)

        positions_label = QLabel(
            "Rechnungspositionen"
        )
        positions_label.setStyleSheet(
            "font-weight: bold;"
        )
        layout.addWidget(positions_label)

        self._positions_widget = QWidget()
        self._positions_layout = QGridLayout(
            self._positions_widget
        )
        self._positions_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        self._positions_layout.addWidget(
            QLabel("Sachkonto"),
            0,
            0,
        )

        gross_label = QLabel("Brutto")
        gross_label.setAlignment(
            Qt.AlignmentFlag.AlignRight
        )
        self._positions_layout.addWidget(
            gross_label,
            0,
            1,
        )

        self._positions_layout.addWidget(
            QLabel("USt"),
            0,
            2,
        )

        layout.addWidget(
            self._positions_widget
        )

        self._add_position_row()

        button_layout = QHBoxLayout()

        self._add_position_button = QPushButton(
            "Position hinzufügen"
        )
        self._add_position_button.clicked.connect(
            self._add_position_row
        )
        button_layout.addWidget(
            self._add_position_button
        )

        self._remove_position_button = QPushButton(
            "Letzte Position entfernen"
        )
        self._remove_position_button.clicked.connect(
            self._remove_position_row
        )
        button_layout.addWidget(
            self._remove_position_button
        )

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
        layout.addWidget(
            self._status_label
        )

        layout.addStretch()

        self._invoice_type_box.currentTextChanged.connect(
            self._on_form_changed
        )
        self._invoice_type_box.currentTextChanged.connect(
            self._on_invoice_type_changed
        )
        self._on_account.toggled.connect(self._update_invoice_fields)
        self._on_account.toggled.connect(self._on_form_changed)
        self._partner_box.currentIndexChanged.connect(self._on_form_changed)
        self._voucher_no_entry.textChanged.connect(self._on_form_changed)
        self._due_date_entry.textChanged.connect(self._on_form_changed)
        self._booking_date_entry.textChanged.connect(
            self._on_form_changed
        )
        self._description_entry.textChanged.connect(
            self._on_form_changed
        )
        self._counter_account_box.currentTextChanged.connect(
            self._on_form_changed
        )

        self._update_remove_button()
        self._update_invoice_fields()

    def _refresh_customer_list(self) -> None:
        self._partner_box.clear()
        if self._partner_repository is None or self._company_id is None:
            self._partner_box.setEnabled(False)
            return
        is_output = self._invoice_type_box.currentText() == _OUTPUT_INVOICE
        partners = self._partner_repository.list_for_company(
            self._company_id,
            customers_only=is_output,
            suppliers_only=not is_output,
        )
        for partner in partners:
            self._partner_box.addItem(partner.name, partner.partner_id)

    def _on_invoice_type_changed(self, *_args: object) -> None:
        self._on_account.setChecked(False)
        self._refresh_customer_list()
        self._update_invoice_fields()

    def _manage_partners(self) -> None:
        if self._partner_repository is None or self._company_id is None:
            return
        dialog = BusinessPartnerDialog(
            self, company_id=self._company_id, repository=self._partner_repository
        )
        dialog.exec()
        self._refresh_customer_list()
        self._on_form_changed()

    def _update_invoice_fields(self, *_args: object) -> None:
        output_invoice = self._invoice_type_box.currentText() == _OUTPUT_INVOICE
        input_invoice = self._invoice_type_box.currentText() == _INPUT_INVOICE
        available = (
            output_invoice and self._on_receivable_invoice_created is not None
        ) or (input_invoice and self._on_payable_invoice_created is not None)
        self._on_account.setVisible(available)
        target = available and self._on_account.isChecked()
        self._on_account.setText(
            "Ausgangsrechnung auf Ziel"
            if output_invoice
            else "Eingangsrechnung auf Ziel"
        )
        self._on_account_label.setText(
            "Forderung" if output_invoice else "Verbindlichkeit"
        )
        self._partner_label.setText("Kunde" if output_invoice else "Lieferant")
        self._voucher_no_label.setText(
            "Rechnungsnummer" if target else "Belegnummer"
        )
        self._partner_box.setVisible(target)
        self._partner_add_button.setVisible(target and self._partner_repository is not None)
        self._due_date_entry.setVisible(target)
        self._counter_account_box.setEnabled(self._enabled and not target)
        self._on_form_changed()

    def _add_position_row(self) -> None:
        """Fügt eine Rechnungsposition hinzu."""

        account_box = QComboBox()
        account_box.setEditable(True)
        account_box.addItems(
            self._account_display_names
        )
        account_box.setCurrentIndex(-1)
        account_box.setInsertPolicy(
            QComboBox.InsertPolicy.NoInsert
        )

        amount_entry = QLineEdit()
        amount_entry.setAlignment(
            Qt.AlignmentFlag.AlignRight
        )
        amount_entry.setMaximumWidth(140)
        amount_entry.setPlaceholderText(
            "0,00"
        )
        amount_entry.editingFinished.connect(
            lambda entry=amount_entry:
            self._normalize_amount_entry(entry)
        )

        tax_rate_box = QComboBox()
        tax_rate_box.addItems(
            _TAX_RATES
        )
        tax_rate_box.setCurrentText(
            "19 %"
        )
        tax_rate_box.setMaximumWidth(100)

        row_index = len(
            self._position_rows
        ) + 1

        self._positions_layout.addWidget(
            account_box,
            row_index,
            0,
        )
        self._positions_layout.addWidget(
            amount_entry,
            row_index,
            1,
        )
        self._positions_layout.addWidget(
            tax_rate_box,
            row_index,
            2,
        )

        row = {
            "account_box": account_box,
            "amount_entry": amount_entry,
            "tax_rate_box": tax_rate_box,
        }

        self._position_rows.append(row)

        account_box.currentTextChanged.connect(
            self._on_form_changed
        )
        amount_entry.textChanged.connect(
            self._on_form_changed
        )
        tax_rate_box.currentTextChanged.connect(
            self._on_form_changed
        )

        self._update_remove_button()

        if hasattr(
            self,
            "_booking_button",
        ):
            self._on_form_changed()

    def _remove_position_row(self) -> None:
        """Entfernt die letzte Rechnungsposition."""

        if len(self._position_rows) <= 1:
            return

        row = self._position_rows.pop()

        for widget_name in (
            "account_box",
            "amount_entry",
            "tax_rate_box",
        ):
            widget = row[widget_name]

            if isinstance(widget, QWidget):
                self._positions_layout.removeWidget(
                    widget
                )
                widget.deleteLater()

        self._update_remove_button()
        self._on_form_changed()

    def _update_remove_button(self) -> None:
        """Aktualisiert den Entfernen-Schalter."""

        if not hasattr(
            self,
            "_remove_position_button",
        ):
            return

        self._remove_position_button.setEnabled(
            self._enabled
            and len(self._position_rows) > 1
        )

    def set_enabled(
        self,
        enabled: bool,
    ) -> None:
        """Aktiviert oder sperrt die Rechnungserfassung."""

        self._enabled = enabled

        self._invoice_type_box.setEnabled(enabled)
        self._booking_date_entry.setEnabled(enabled)
        self._voucher_no_entry.setEnabled(enabled)
        self._description_entry.setEnabled(enabled)
        self._counter_account_box.setEnabled(enabled)
        self._on_account.setEnabled(enabled)
        self._partner_box.setEnabled(enabled)
        self._partner_add_button.setEnabled(enabled)
        self._due_date_entry.setEnabled(enabled)

        for row in self._position_rows:
            row["account_box"].setEnabled(enabled)
            row["amount_entry"].setEnabled(enabled)
            row["tax_rate_box"].setEnabled(enabled)

        self._add_position_button.setEnabled(
            enabled
        )

        self._update_remove_button()
        self._update_invoice_fields()

        if enabled:
            self._on_form_changed()
        else:
            self._booking_button.setEnabled(False)
            self._status_label.setText(
                "Das Geschäftsjahr ist abgeschlossen. "
                "Buchungen sind nicht mehr möglich."
            )

    def _on_form_changed(
        self,
        *_args: object,
    ) -> None:
        """Prüft die Vollständigkeit der Rechnungserfassung."""

        if not self._enabled:
            self._booking_button.setEnabled(False)
            return

        valid = True

        try:
            self._parse_booking_date(
                self._booking_date_entry.text()
            )
        except ValueError:
            valid = False

        if not self._description_entry.text().strip():
            valid = False

        target_invoice = self._is_target_invoice()
        counter_account = self._resolve_account(
            self._counter_account_box.currentText()
        )

        if counter_account is None and not target_invoice:
            valid = False

        if target_invoice:
            if self._partner_box.currentData() is None:
                valid = False
            if not self._voucher_no_entry.text().strip():
                valid = False
            try:
                self._parse_booking_date(self._due_date_entry.text())
            except ValueError:
                valid = False

        invoice_type = (
            self._invoice_type_box.currentText()
        )

        for row in self._position_rows:
            account_box = row["account_box"]
            amount_entry = row["amount_entry"]
            tax_rate_box = row["tax_rate_box"]

            account = self._resolve_account(
                account_box.currentText()
            )

            if account is None:
                valid = False

            if (
                account is not None
                and invoice_type
                in (
                    _INPUT_INVOICE,
                    _SUPPLIER_CREDIT_NOTE,
                )
                and account.account_type
                not in (
                    AccountType.EXPENSE,
                    AccountType.ASSET,
                )
            ):
                valid = False

            if (
                account is not None
                and invoice_type in (
                    _OUTPUT_INVOICE,
                    _CUSTOMER_CREDIT_NOTE,
                )
                and account.account_type
                is not AccountType.REVENUE
            ):
                valid = False

            try:
                self._parse_amount(
                    amount_entry.text()
                )
            except ValueError:
                valid = False

            try:
                self._parse_tax_rate(
                    tax_rate_box.currentText()
                )
            except ValueError:
                valid = False

            if (
                not target_invoice
                and counter_account is not None
                and account is not None
                and counter_account.number
                == account.number
            ):
                valid = False

        self._booking_button.setEnabled(
            valid
        )

        self._status_label.clear()

    def _is_target_invoice(self) -> bool:
        invoice_type = self._invoice_type_box.currentText()
        return self._on_account.isChecked() and (
            (
                invoice_type == _OUTPUT_INVOICE
                and self._on_receivable_invoice_created is not None
            )
            or (
                invoice_type == _INPUT_INVOICE
                and self._on_payable_invoice_created is not None
            )
        )

    def _create_booking(self) -> None:
        """Erzeugt die Buchung aus der Rechnung."""

        if not self._enabled:
            return

        target_invoice = self._is_target_invoice()

        counter_account = self._resolve_account(
            self._counter_account_box.currentText()
        )

        if counter_account is None and not target_invoice:
            return

        try:
            booking_date = self._parse_booking_date(
                self._booking_date_entry.text()
            )

            items = tuple(
                VatBookingItem(
                    account_number=account.number,
                    gross_amount=self._parse_amount(
                        row["amount_entry"].text()
                    ),
                    tax_rate=self._parse_tax_rate(
                        row["tax_rate_box"].currentText()
                    ),
                )
                for row in self._position_rows
                if (
                    account := self._resolve_account(
                        row["account_box"].currentText()
                    )
                )
                is not None
            )
        except ValueError:
            return

        if len(items) != len(
            self._position_rows
        ):
            return

        if target_invoice:
            try:
                due_date = self._parse_booking_date(self._due_date_entry.text())
                partner_id = self._partner_box.currentData()
                if not isinstance(partner_id, UUID):
                    return
                common_arguments = {
                    "partner_id": partner_id,
                    "invoice_number": self._voucher_no_entry.text().strip(),
                    "booking_date": booking_date,
                    "due_date": due_date,
                    "items": items,
                    "description": self._description_entry.text().strip() or None,
                }
                if self._invoice_type_box.currentText() == _INPUT_INVOICE:
                    self._submit_payable_invoice(common_arguments)
                else:
                    assert self._on_receivable_invoice_created is not None
                    self._on_receivable_invoice_created(**common_arguments)
            except Exception as exc:
                self._status_label.setText(str(exc))
                return
            self._clear()
            self._status_label.setText(
                "Rechnung und offener Posten wurden übernommen."
            )
            return

        voucher_no = (
            self._voucher_no_entry.text().strip()
            or None
        )

        description = (
            self._description_entry.text().strip()
            or None
        )

        invoice_type = (
            self._invoice_type_box.currentText()
        )

        if invoice_type == _INPUT_INVOICE:
            booking = (
                self._vat_booking_service
                .build_input_booking(
                    booking_date=booking_date,
                    counter_account_number=(
                        counter_account.number
                    ),
                    items=items,
                    vat_accounts=self._vat_accounts,
                    voucher_no=voucher_no,
                    description=description,
                )
            )

        elif invoice_type == _OUTPUT_INVOICE:
            booking = (
                self._vat_booking_service
                .build_output_booking(
                    booking_date=booking_date,
                    counter_account_number=(
                        counter_account.number
                    ),
                    items=items,
                    vat_accounts=self._vat_accounts,
                    voucher_no=voucher_no,
                    description=description,
                )
            )

        elif invoice_type == _CUSTOMER_CREDIT_NOTE:
            booking = (
                self._vat_booking_service
                .build_customer_credit_note(
                    booking_date=booking_date,
                    counter_account_number=(
                        counter_account.number
                    ),
                    items=items,
                    vat_accounts=self._vat_accounts,
                    voucher_no=voucher_no,
                    description=description,
                )
            )

        elif invoice_type == _SUPPLIER_CREDIT_NOTE:
            booking = (
                self._vat_booking_service
                .build_supplier_credit_note(
                    booking_date=booking_date,
                    counter_account_number=(
                        counter_account.number
                    ),
                    items=items,
                    vat_accounts=self._vat_accounts,
                    voucher_no=voucher_no,
                    description=description,
                )
            )

        else:
            return

        self._on_booking_created(
            booking
        )

        self._clear()

        self._status_label.setText(
            "Buchung wurde übernommen."
        )

    def _submit_payable_invoice(
        self,
        common_arguments: dict[str, object],
    ) -> None:
        callback = self._on_payable_invoice_created
        if callback is None:
            raise ValueError("Die OP-Verwaltung ist nicht verfügbar.")
        try:
            callback(**common_arguments, duplicate_reason=None)
        except DuplicateSupplierInvoiceError as duplicate:
            QMessageBox.warning(
                self,
                "Rechnungsnummer bereits erfasst",
                str(duplicate),
            )
            reason, accepted = QInputDialog.getText(
                self,
                "Erneute Erfassung begründen",
                "Begründung für die erneute Erfassung:",
            )
            if not accepted:
                raise ValueError("Die erneute Erfassung wurde abgebrochen.")
            if not reason.strip():
                raise ValueError("Eine Begründung darf nicht leer sein.")
            callback(**common_arguments, duplicate_reason=reason.strip())

    def _clear(self) -> None:
        """Leert die Rechnungspositionen nach der Buchung."""

        self._voucher_no_entry.clear()
        self._description_entry.clear()

        self._counter_account_box.setCurrentIndex(
            -1
        )

        while len(self._position_rows) > 1:
            self._remove_position_row()

        row = self._position_rows[0]

        row["account_box"].setCurrentIndex(-1)
        row["amount_entry"].clear()
        row["tax_rate_box"].setCurrentText(
            "19 %"
        )

    def _resolve_account(
        self,
        value: str,
    ) -> Account | None:
        """Ermittelt das ausgewählte Konto."""

        normalized = value.strip()

        if not normalized:
            return None

        direct_match = (
            self._accounts_by_display_name.get(
                normalized
            )
        )

        if direct_match is not None:
            return direct_match

        return self._accounts_by_number.get(
            normalized
        )

    @staticmethod
    def _account_display_name(
        account: Account,
    ) -> str:
        """Liefert die Anzeige eines Kontos."""

        return str(account)

    @staticmethod
    def _parse_booking_date(
        value: str,
    ) -> date:
        """Liest ein deutsches Buchungsdatum."""

        return parse_german_date(
            value
        )

    def _normalize_amount_entry(
        self,
        entry: QLineEdit,
    ) -> None:
        """Normalisiert eine Betragseingabe."""

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

    @staticmethod
    def _parse_amount(
        value: str,
    ) -> Decimal:
        """Liest einen positiven Bruttobetrag."""

        normalized = (
            value.strip()
            .replace(".", "")
            .replace(",", ".")
        )

        try:
            amount = Decimal(
                normalized
            )
        except InvalidOperation as exc:
            raise ValueError(
                "Ungültiger Betrag."
            ) from exc

        if amount <= Decimal("0"):
            raise ValueError(
                "Der Betrag muss größer als 0 sein."
            )

        return amount

    @staticmethod
    def _parse_tax_rate(
        value: str,
    ) -> int:
        """Liest einen unterstützten Umsatzsteuersatz."""

        normalized = (
            value.strip()
            .removesuffix("%")
            .strip()
        )

        try:
            tax_rate = int(
                normalized
            )
        except ValueError as exc:
            raise ValueError(
                "Ungültiger Umsatzsteuersatz."
            ) from exc

        if tax_rate not in (0, 7, 19):
            raise ValueError(
                "Der Umsatzsteuersatz muss "
                "0, 7 oder 19 Prozent betragen."
            )

        return tax_rate

    def _normalize_booking_date(self) -> None:
        """Normalisiert das Buchungsdatum."""

        try:
            normalized = (
                normalize_german_date(
                    self._booking_date_entry.text()
                )
            )
        except ValueError:
            return

        self._booking_date_entry.setText(
            normalized
        )

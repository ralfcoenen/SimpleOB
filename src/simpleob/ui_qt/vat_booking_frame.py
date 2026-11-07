"""PySide6-Eingabemaske für Rechnungen mit Umsatzsteuer."""

from collections.abc import Callable
from datetime import date
from decimal import Decimal, InvalidOperation
from uuid import UUID

from PySide6.QtCore import Qt
from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from simpleob.amount_input import format_german_amount, normalize_german_amount
from simpleob.database.business_partner_repository import BusinessPartnerRepository
from simpleob.date_input import GermanDateEdit
from simpleob.domain.account import Account
from simpleob.domain.account_type import AccountType
from simpleob.domain.booking import Booking
from simpleob.domain.credit_note import (
    CreditNoteKind,
    DuplicateSupplierCreditNoteError,
)
from simpleob.domain.kr_monitoring import KrMonitoringSummary
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
_BOOKING_COLUMNS_BREAKPOINT = 1050


class ResponsiveBookingSplitter(QSplitter):
    """Zeigt Buchung und Umsatzüberwachung passend zur Fensterbreite an."""

    def __init__(self) -> None:
        super().__init__(Qt.Orientation.Horizontal)
        self.setChildrenCollapsible(False)
        self.setStretchFactor(0, 3)
        self.setStretchFactor(1, 2)

    def resizeEvent(self, event: QResizeEvent) -> None:
        orientation = (
            Qt.Orientation.Vertical
            if self.width() < _BOOKING_COLUMNS_BREAKPOINT
            else Qt.Orientation.Horizontal
        )
        changed = self.orientation() != orientation
        if changed:
            self.setOrientation(orientation)
        super().resizeEvent(event)
        if changed and orientation == Qt.Orientation.Horizontal:
            width = max(1, self.width())
            self.setSizes([round(width * 0.6), round(width * 0.4)])


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
        on_credit_note_created: Callable[..., None] | None = None,
        kr_summary_provider: Callable[[], KrMonitoringSummary] | None = None,
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
        self._on_credit_note_created = on_credit_note_created
        self._kr_summary_provider = kr_summary_provider

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
        self._last_kr_warning_key: tuple[object, ...] | None = None

        self._create_ui()

    def _create_ui(self) -> None:
        """Erzeugt die Rechnungserfassung."""

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        form = QVBoxLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(4)

        self._invoice_type_label = QLabel("Rechnungsart")
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
        self._invoice_type_box.setMaximumWidth(260)
        self._invoice_type_label.setBuddy(self._invoice_type_box)
        header_row = QHBoxLayout()
        header_row.setSpacing(6)
        header_row.addWidget(self._invoice_type_label)
        header_row.addWidget(self._invoice_type_box)

        self._booking_date_label = QLabel("Datum")
        self._booking_date_entry = GermanDateEdit(value=date.today())
        self._booking_date_entry.setMinimumWidth(120)
        self._booking_date_entry.setMaximumWidth(140)
        self._booking_date_label.setBuddy(self._booking_date_entry)
        header_row.addSpacing(12)
        header_row.addWidget(self._booking_date_label)
        header_row.addWidget(self._booking_date_entry)
        header_row.addStretch()
        form.addLayout(header_row)

        self._voucher_no_entry = QLineEdit()
        self._voucher_no_entry.setMinimumWidth(140)
        self._voucher_no_entry.setMaximumWidth(220)
        self._voucher_no_label = QLabel("Belegnummer")
        self._voucher_no_label.setBuddy(self._voucher_no_entry)

        self._on_account = QCheckBox("Rechnung auf Ziel")
        self._on_account.setVisible(False)
        self._on_account_label = QLabel("Forderung")
        self._on_account_label.setBuddy(self._on_account)
        invoice_reference_row = QHBoxLayout()
        invoice_reference_row.setSpacing(6)
        invoice_reference_row.addWidget(self._voucher_no_label)
        invoice_reference_row.addWidget(self._voucher_no_entry)
        invoice_reference_row.addSpacing(12)
        invoice_reference_row.addWidget(self._on_account_label)
        invoice_reference_row.addWidget(self._on_account)
        invoice_reference_row.addStretch()
        form.addLayout(invoice_reference_row)
        self._partner_box = QComboBox()
        self._partner_box.setVisible(False)
        self._partner_add_button = QPushButton("Geschäftspartner verwalten")
        self._partner_add_button.setVisible(False)
        self._partner_label = QLabel("Geschäftspartner")
        self._partner_label.setBuddy(self._partner_box)
        partner_row = QHBoxLayout()
        partner_row.setSpacing(6)
        partner_row.addWidget(self._partner_label)
        partner_row.addWidget(self._partner_box, 1)
        partner_row.addWidget(self._partner_add_button)
        form.addLayout(partner_row)

        self._due_date_label = QLabel("Fällig am")
        self._due_date_entry = GermanDateEdit(value=date.today())
        self._due_date_entry.setMinimumWidth(120)
        self._due_date_entry.setMaximumWidth(140)
        self._due_date_entry.setVisible(False)
        self._due_date_label.setBuddy(self._due_date_entry)

        self._original_invoice_number_entry = QLineEdit()
        self._original_invoice_number_entry.setMinimumWidth(140)
        self._original_invoice_number_entry.setMaximumWidth(220)
        self._original_invoice_number_entry.setVisible(False)
        self._original_invoice_number_label = QLabel(
            "Rechnungsbezug (optional)"
        )
        self._original_invoice_number_label.setBuddy(
            self._original_invoice_number_entry
        )
        document_detail_row = QHBoxLayout()
        document_detail_row.setSpacing(6)
        document_detail_row.addWidget(self._due_date_label)
        document_detail_row.addWidget(self._due_date_entry)
        document_detail_row.addSpacing(12)
        document_detail_row.addWidget(self._original_invoice_number_label)
        document_detail_row.addWidget(self._original_invoice_number_entry)
        document_detail_row.addStretch()
        form.addLayout(document_detail_row)
        self._refresh_customer_list()
        self._partner_add_button.clicked.connect(self._manage_partners)

        self._description_entry = QLineEdit()
        self._description_label = QLabel("Buchungstext")
        self._description_label.setBuddy(self._description_entry)
        description_row = QHBoxLayout()
        description_row.setSpacing(6)
        description_row.addWidget(self._description_label)
        description_row.addWidget(self._description_entry, 1)
        form.addLayout(description_row)

        self._counter_account_box = QComboBox()
        self._counter_account_box.setEditable(True)
        self._counter_account_box.addItems(
            self._account_display_names
        )
        self._counter_account_box.setCurrentIndex(-1)
        self._counter_account_box.setInsertPolicy(
            QComboBox.InsertPolicy.NoInsert
        )
        self._counter_account_label = QLabel("Gegenkonto")
        self._counter_account_label.setBuddy(self._counter_account_box)
        counter_account_row = QHBoxLayout()
        counter_account_row.setSpacing(6)
        counter_account_row.addWidget(self._counter_account_label)
        counter_account_row.addWidget(self._counter_account_box, 1)
        form.addLayout(counter_account_row)

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
        self._positions_layout.setContentsMargins(0, 0, 0, 0)
        self._positions_layout.setHorizontalSpacing(8)
        self._positions_layout.setVerticalSpacing(4)

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

        self._create_kr_summary()

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
        self._original_invoice_number_entry.textChanged.connect(
            self._on_form_changed
        )
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
        self.refresh_kr_summary()

    def _create_kr_summary(self) -> None:
        box = QGroupBox("Umsatzüberwachung – vereinnahmte Kundenzahlungen")
        grid = QGridLayout(box)
        grid.setContentsMargins(8, 6, 8, 6)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(2)
        grid.addWidget(QLabel("Position"), 0, 0)
        self._kr_previous_year_label = QLabel("Vorjahr")
        self._kr_current_year_label = QLabel("Laufendes Jahr")
        grid.addWidget(self._kr_previous_year_label, 0, 1)
        grid.addWidget(self._kr_current_year_label, 0, 2)
        self._kr_value_labels: dict[str, tuple[QLabel, QLabel]] = {}
        for row, (key, caption) in enumerate(
            (
                ("payments", "Kundenzahlungen"),
                ("refunds", "Kundenrückerstattungen"),
                ("external", "Externe Umsatzergänzung"),
                ("balance", "Saldo inkl. Ergänzung"),
                ("limit", "Umsatzgrenze"),
            ),
            start=1,
        ):
            grid.addWidget(QLabel(caption), row, 0)
            previous = QLabel("–")
            current = QLabel("–")
            previous.setAlignment(Qt.AlignmentFlag.AlignRight)
            current.setAlignment(Qt.AlignmentFlag.AlignRight)
            grid.addWidget(previous, row, 1)
            grid.addWidget(current, row, 2)
            self._kr_value_labels[key] = (previous, current)

        self._kr_direct_revenue_warning = QLabel(
            "Direkte Erlösbuchungen vorhanden. Die Umsatzüberwachung kann unvollständig sein."
        )
        self._kr_direct_revenue_warning.setWordWrap(True)
        self._kr_direct_revenue_warning.setStyleSheet("font-weight: bold;")
        self._kr_direct_revenue_warning.hide()
        grid.addWidget(self._kr_direct_revenue_warning, 6, 0, 1, 3)
        self._kr_activity_start_warning = QLabel(
            "Beginn der Tätigkeit fehlt. Das Gründungsjahr und die passende Umsatzgrenze sind nicht bestimmbar."
        )
        self._kr_activity_start_warning.setWordWrap(True)
        self._kr_activity_start_warning.hide()
        grid.addWidget(self._kr_activity_start_warning, 7, 0, 1, 3)
        self._kr_error_label = QLabel(
            "Die Umsatzüberwachung ist derzeit nicht verfügbar."
        )
        self._kr_error_label.setWordWrap(True)
        self._kr_error_label.hide()
        grid.addWidget(self._kr_error_label, 8, 0, 1, 3)
        self._kr_scope_note = QLabel(
            "Ausgewertet werden ausschließlich OP-zugeordnete Kundenzahlungen und "
            "eindeutig zuordenbare Kundenrückerstattungen. Ausgangsrechnungen müssen "
            "dafür grundsätzlich auf Ziel erfasst werden. Direktverkäufe, Anzahlungen "
            "ohne Rechnung und nicht eindeutig erkennbare Entgeltminderungen fehlen; "
            "die Anzeige ersetzt keine vollständige steuerrechtliche Prüfung."
        )
        self._kr_scope_note.setWordWrap(True)
        grid.addWidget(self._kr_scope_note, 9, 0, 1, 3)
        self._kr_summary_box = box

    @property
    def kr_summary_widget(self) -> QGroupBox:
        """Gibt das bestehende Umsatzüberwachungs-Widget für das Layout frei."""
        return self._kr_summary_box

    def refresh_kr_summary(self) -> None:
        """Aktualisiert die informative kalenderjährliche KR-Ansicht."""
        if self._kr_summary_provider is None:
            self._kr_summary_box.hide()
            return
        try:
            summary = self._kr_summary_provider()
        except Exception:
            for labels in self._kr_value_labels.values():
                for label in labels:
                    label.setText("–")
            self._kr_direct_revenue_warning.hide()
            self._kr_activity_start_warning.hide()
            self._kr_error_label.show()
            return
        if not summary.is_visible:
            self._kr_summary_box.hide()
            return
        self._kr_summary_box.show()
        self._kr_error_label.hide()
        years = (summary.previous_year, summary.current_year)
        self._kr_previous_year_label.setText(f"Vorjahr {years[0].calendar_year}")
        self._kr_current_year_label.setText(
            f"Laufendes Jahr {years[1].calendar_year}"
        )
        values = {
            "payments": tuple(year.customer_payments for year in years),
            "refunds": tuple(year.customer_refunds for year in years),
            "external": tuple(year.external_turnover for year in years),
            "balance": tuple(year.balance for year in years),
        }
        for key, amounts in values.items():
            for label, amount in zip(
                self._kr_value_labels[key], amounts, strict=True
            ):
                label.setText(f"{format_german_amount(amount)} €")
        for label, year in zip(
            self._kr_value_labels["limit"], years, strict=True
        ):
            label.setText(
                "–" if year.limit is None else f"{format_german_amount(year.limit)} €"
            )
        self._kr_direct_revenue_warning.setVisible(
            summary.has_direct_revenue_bookings
        )
        self._kr_activity_start_warning.setVisible(
            summary.activity_start_date is None
        )

    def _refresh_customer_list(self) -> None:
        self._partner_box.clear()
        if self._partner_repository is None or self._company_id is None:
            self._partner_box.setEnabled(False)
            return
        invoice_type = self._invoice_type_box.currentText()
        is_customer = invoice_type in (
            _OUTPUT_INVOICE,
            _CUSTOMER_CREDIT_NOTE,
        )
        partners = self._partner_repository.list_for_company(
            self._company_id,
            customers_only=is_customer,
            suppliers_only=not is_customer,
        )
        for partner in partners:
            self._partner_box.addItem(partner.name, partner.partner_id)

    def _on_invoice_type_changed(self, *_args: object) -> None:
        self._last_kr_warning_key = None
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
        invoice_type = self._invoice_type_box.currentText()
        output_invoice = invoice_type == _OUTPUT_INVOICE
        input_invoice = invoice_type == _INPUT_INVOICE
        customer_credit = invoice_type == _CUSTOMER_CREDIT_NOTE
        supplier_credit = invoice_type == _SUPPLIER_CREDIT_NOTE
        target_available = (
            output_invoice and self._on_receivable_invoice_created is not None
        ) or (input_invoice and self._on_payable_invoice_created is not None)
        credit_note_available = (
            (customer_credit or supplier_credit)
            and self._on_credit_note_created is not None
        )
        target = target_available and self._on_account.isChecked()
        credit_note = credit_note_available
        document_uses_partner = target or credit_note
        self._on_account.setVisible(target_available)
        self._on_account.setText(
            "Ausgangsrechnung auf Ziel"
            if output_invoice
            else "Eingangsrechnung auf Ziel"
        )
        self._on_account_label.setText(
            "Forderung" if output_invoice else "Verbindlichkeit"
        )
        self._on_account_label.setVisible(target_available)
        self._partner_label.setText(
            "Kunde" if output_invoice or customer_credit else "Lieferant"
        )
        self._partner_label.setVisible(document_uses_partner)
        self._voucher_no_label.setText(
            "Gutschriftnummer"
            if credit_note
            else "Rechnungsnummer"
            if target
            else "Belegnummer"
        )
        self._partner_box.setVisible(document_uses_partner)
        self._partner_add_button.setVisible(
            document_uses_partner and self._partner_repository is not None
        )
        self._due_date_entry.setVisible(target)
        self._original_invoice_number_entry.setVisible(credit_note)
        self._original_invoice_number_label.setVisible(credit_note)
        self._due_date_label.setVisible(target)
        self._counter_account_box.setEnabled(
            self._enabled and not (target or credit_note)
        )
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
        amount_entry.setMinimumWidth(100)
        amount_entry.setMaximumWidth(140)
        amount_entry.setPlaceholderText(
            "0,00"
        )
        amount_entry.editingFinished.connect(
            lambda entry=amount_entry:
            self._normalize_amount_entry(entry)
        )
        amount_entry.editingFinished.connect(
            lambda entry=amount_entry: self._check_kr_invoice_threshold(entry)
        )

        tax_rate_box = QComboBox()
        tax_rate_box.addItems(
            _TAX_RATES
        )
        tax_rate_box.setCurrentText(
            "19 %"
        )
        tax_rate_box.setMinimumWidth(80)
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
        self._original_invoice_number_entry.setEnabled(enabled)

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
            self._booking_date_entry.date_value()
        except ValueError:
            valid = False

        if not self._description_entry.text().strip():
            valid = False

        target_invoice = self._is_target_invoice()
        credit_note = self._is_credit_note_creation()
        counter_account = self._resolve_account(
            self._counter_account_box.currentText()
        )

        if counter_account is None and not (target_invoice or credit_note):
            valid = False

        if target_invoice or credit_note:
            if self._partner_box.currentData() is None:
                valid = False
            if not self._voucher_no_entry.text().strip():
                valid = False
        if target_invoice:
            try:
                self._due_date_entry.date_value()
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
                not (target_invoice or credit_note)
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

    def _is_credit_note_creation(self) -> bool:
        return (
            self._invoice_type_box.currentText()
            in (_CUSTOMER_CREDIT_NOTE, _SUPPLIER_CREDIT_NOTE)
            and self._on_credit_note_created is not None
        )

    def _create_booking(self) -> None:
        """Erzeugt die Buchung aus der Rechnung."""

        if not self._enabled:
            return

        target_invoice = self._is_target_invoice()
        credit_note = self._is_credit_note_creation()

        counter_account = self._resolve_account(
            self._counter_account_box.currentText()
        )

        if counter_account is None and not (target_invoice or credit_note):
            return

        try:
            booking_date = self._booking_date_entry.date_value()

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
                due_date = self._due_date_entry.date_value()
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

        if credit_note:
            partner_id = self._partner_box.currentData()
            if not isinstance(partner_id, UUID):
                return
            is_customer_credit = (
                self._invoice_type_box.currentText() == _CUSTOMER_CREDIT_NOTE
            )
            arguments = {
                "kind": (
                    CreditNoteKind.CUSTOMER
                    if is_customer_credit
                    else CreditNoteKind.SUPPLIER
                ),
                "partner_id": partner_id,
                "note_number": self._voucher_no_entry.text().strip(),
                "note_date": booking_date,
                "items": items,
                "original_invoice_number": (
                    self._original_invoice_number_entry.text().strip() or None
                ),
                "description": self._description_entry.text().strip() or None,
            }
            try:
                self._submit_credit_note(arguments, supplier=not is_customer_credit)
            except Exception as exc:
                self._status_label.setText(str(exc))
                return
            self._clear()
            self._status_label.setText(
                "Gutschrift und Guthaben-OP wurden übernommen."
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

    def _submit_credit_note(
        self,
        arguments: dict[str, object],
        *,
        supplier: bool,
    ) -> None:
        callback = self._on_credit_note_created
        if callback is None:
            raise ValueError("Die OP-Verwaltung ist nicht verfügbar.")
        try:
            callback(**arguments, duplicate_reason=None)
        except DuplicateSupplierCreditNoteError as duplicate:
            if not supplier:
                raise
            QMessageBox.warning(
                self,
                "Gutschriftnummer bereits erfasst",
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
            callback(**arguments, duplicate_reason=reason.strip())

    def _clear(self) -> None:
        """Leert die Rechnungspositionen nach der Buchung."""

        self._last_kr_warning_key = None
        self._voucher_no_entry.clear()
        self._original_invoice_number_entry.clear()
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

    def _check_kr_invoice_threshold(self, amount_entry: QLineEdit) -> None:
        """Warnt bei einer voraussichtlichen Überschreitung durch die Rechnung."""
        if self._invoice_type_box.currentText() != _OUTPUT_INVOICE:
            self._last_kr_warning_key = None
            return

        if self._kr_summary_provider is None:
            self._last_kr_warning_key = None
            return

        try:
            self._parse_amount(amount_entry.text())
        except ValueError:
            self._last_kr_warning_key = None
            return

        # Die Maske und die OP-Auswertung arbeiten mit Bruttobeträgen.
        # Der eingegebene Bruttobetrag wird einmal angesetzt; der
        # ausgewählte Steuersatz darf ihn für die Prognose nicht erhöhen.
        entered_amounts = []
        for row in self._position_rows:
            try:
                entered_amounts.append(
                    self._parse_amount(row["amount_entry"].text())
                )
            except ValueError:
                continue
        invoice_amount = sum(entered_amounts, Decimal("0.00"))
        if invoice_amount <= Decimal("0.00"):
            self._last_kr_warning_key = None
            return

        try:
            summary = self._kr_summary_provider()
        except Exception:
            self._last_kr_warning_key = None
            return

        current_year = summary.current_year
        if (
            not summary.is_visible
            or summary.activity_start_date is None
            or current_year.limit is None
        ):
            self._last_kr_warning_key = None
            return

        current_balance = current_year.balance
        projected_turnover = current_balance + invoice_amount
        warning_key = (
            self._company_id,
            current_year.calendar_year,
            current_balance,
            invoice_amount,
            current_year.limit,
        )
        if (
            projected_turnover <= current_year.limit
            or warning_key == self._last_kr_warning_key
        ):
            self._last_kr_warning_key = warning_key
            return

        self._last_kr_warning_key = warning_key
        message = (
            "Bei vollständiger Vereinnahmung dieser Ausgangsrechnung im "
            "laufenden Kalenderjahr würde die Grenze der "
            "Kleinunternehmerregelung überschritten.\n\n"
            f"Bisheriger Umsatz: {format_german_amount(current_balance)} €\n"
            f"Neue Ausgangsrechnung: {format_german_amount(invoice_amount)} €\n"
            "Prognostizierter Umsatz: "
            f"{format_german_amount(projected_turnover)} €\n"
            "Maßgebliche Grenze: "
            f"{format_german_amount(current_year.limit)} €\n\n"
            "Bitte prüfen Sie vor der Buchung, ob für diese Rechnung "
            "Umsatzsteuer mit 19 % beziehungsweise 7 % auszuweisen ist."
        )
        QMessageBox.warning(
            self,
            "Umsatzgrenze voraussichtlich überschritten",
            message,
            QMessageBox.StandardButton.Ok,
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

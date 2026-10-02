"""PySide6-Eingabemaske für Rechnungen mit Umsatzsteuer."""

from collections.abc import Callable
from datetime import date
from decimal import Decimal, InvalidOperation

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from openbilanz.amount_input import normalize_german_amount
from openbilanz.date_input import (
    normalize_german_date,
    parse_german_date,
)
from openbilanz.domain.account import Account
from openbilanz.domain.account_type import AccountType
from openbilanz.domain.booking import Booking
from openbilanz.domain.vat_accounts import VatAccounts
from openbilanz.domain.vat_booking_item import VatBookingItem
from openbilanz.services.vat_booking_service import (
    VatBookingService,
)

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
    ) -> None:
        super().__init__(parent)

        self._accounts = accounts
        self._vat_accounts = vat_accounts
        self._on_booking_created = on_booking_created
        self._vat_booking_service = VatBookingService()
        self._enabled = True

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
        form.addRow(
            "Belegnummer",
            self._voucher_no_entry,
        )

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

        for row in self._position_rows:
            row["account_box"].setEnabled(enabled)
            row["amount_entry"].setEnabled(enabled)
            row["tax_rate_box"].setEnabled(enabled)

        self._add_position_button.setEnabled(
            enabled
        )

        self._update_remove_button()

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

        counter_account = self._resolve_account(
            self._counter_account_box.currentText()
        )

        if counter_account is None:
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
                counter_account is not None
                and account is not None
                and counter_account.number
                == account.number
            ):
                valid = False

        self._booking_button.setEnabled(
            valid
        )

        self._status_label.clear()

    def _create_booking(self) -> None:
        """Erzeugt die Buchung aus der Rechnung."""

        if not self._enabled:
            return

        counter_account = self._resolve_account(
            self._counter_account_box.currentText()
        )

        if counter_account is None:
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

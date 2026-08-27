"""Qt-Eingabemaske für Umsatzsteuerbuchungen."""

from collections.abc import Callable
from datetime import date
from decimal import Decimal, InvalidOperation

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QCompleter,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from openbilanz.domain.account import Account
from openbilanz.domain.account_type import AccountType
from openbilanz.domain.booking import Booking
from openbilanz.domain.vat_accounts import VatAccounts
from openbilanz.domain.vat_booking_item import VatBookingItem
from openbilanz.domain.vat_configuration import (
    VatConfiguration,
)
from openbilanz.services.vat_booking_service import VatBookingService
from openbilanz.ui.date_input import (
    normalize_german_date,
    parse_german_date,
)

_INPUT_INVOICE = "Eingangsrechnung"
_OUTPUT_INVOICE = "Ausgangsrechnung"
_CUSTOMER_CREDIT_NOTE = "Kundengutschrift"
_SUPPLIER_CREDIT_NOTE = "Lieferantengutschrift"

_TAX_RATES = ("0 %", "7 %", "19 %")


class VatPositionRow(QWidget):
    """Eine einzelne Rechnungsposition."""

    def __init__(
        self,
        *,
        account_display_names: tuple[str, ...],
        on_changed: Callable[[], None],
        small_business: bool,
    ) -> None:
        super().__init__()

        self._on_changed = on_changed
        self._small_business = small_business

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.account_box = QComboBox()
        self.account_box.setEditable(True)
        self.account_box.addItems(account_display_names)
        self.account_box.setCurrentIndex(-1)

        completer = QCompleter(
            account_display_names,
            self.account_box,
        )
        completer.setCaseSensitivity(
            Qt.CaseSensitivity.CaseInsensitive
        )
        completer.setFilterMode(
            Qt.MatchFlag.MatchContains
        )
        self.account_box.setCompleter(completer)

        self.amount_entry = QLineEdit()
        self.amount_entry.setMaximumWidth(140)
        self.amount_entry.setAlignment(
            Qt.AlignmentFlag.AlignRight
        )

        self.tax_rate_box = QComboBox()
        self.tax_rate_box.addItems(_TAX_RATES)
        self.tax_rate_box.setCurrentText(
            "0 %" if self._small_business else "19 %"
        )
        self.tax_rate_box.setMaximumWidth(90)

        layout.addWidget(self.account_box, 1)
        layout.addWidget(self.amount_entry)
        layout.addWidget(self.tax_rate_box)

        self.account_box.currentTextChanged.connect(
            self._on_changed
        )
        self.amount_entry.textChanged.connect(
            self._on_changed
        )
        self.tax_rate_box.currentTextChanged.connect(
            self._on_changed
        )

    def set_enabled(self, enabled: bool) -> None:
        self.account_box.setEnabled(enabled)
        self.amount_entry.setEnabled(enabled)
        self.tax_rate_box.setEnabled(
            enabled and not self._small_business
        )

    def clear(self) -> None:
        self.account_box.setCurrentIndex(-1)
        self.amount_entry.clear()
        self.tax_rate_box.setCurrentText(
            "0 %" if self._small_business else "19 %"
        )

class VatBookingWidget(QWidget):
    """Erfasst Rechnungen und Gutschriften mit Umsatzsteuer."""

    def __init__(
        self,
        *,
        accounts: tuple[Account, ...],
        vat_accounts: VatAccounts,
        vat_configuration: VatConfiguration,
        on_booking_created: Callable[[Booking], None],
    ) -> None:
        super().__init__()

        self._accounts = accounts
        self._vat_accounts = vat_accounts
        self._vat_configuration = vat_configuration
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

        self._position_rows: list[VatPositionRow] = []

        self._create_ui()
        self._add_position_row()
        self._update_state()

    def _create_ui(self) -> None:
        layout = QVBoxLayout(self)

        if self._vat_configuration.is_small_business:
            small_business_label = QLabel(
                "Kleinunternehmer gemäß § 19 UStG – "
                "keine Umsatzsteuerberechnung"
            )
            small_business_label.setWordWrap(True)
            layout.addWidget(small_business_label)

        form = QFormLayout()
        layout.addLayout(form)

        self._invoice_type_box = QComboBox()
        self._invoice_type_box.addItems(
            (
                _INPUT_INVOICE,
                _OUTPUT_INVOICE,
                _CUSTOMER_CREDIT_NOTE,
                _SUPPLIER_CREDIT_NOTE,
            )
        )

        self._booking_date = QLineEdit(
            date.today().strftime("%d.%m.%Y")
        )
        self._booking_date.setMaximumWidth(160)
        self._booking_date.editingFinished.connect(
            self._normalize_booking_date
        )

        self._voucher_no = QLineEdit()
        self._voucher_no.setMaximumWidth(240)

        self._description = QLineEdit()

        self._counter_account = self._create_account_box()

        form.addRow(
            "Rechnungsart",
            self._invoice_type_box,
        )
        form.addRow(
            "Datum",
            self._booking_date,
        )
        form.addRow(
            "Belegnummer",
            self._voucher_no,
        )
        form.addRow(
            "Buchungstext",
            self._description,
        )
        form.addRow(
            "Gegenkonto",
            self._counter_account,
        )

        layout.addSpacing(12)

        title = QLabel("Rechnungspositionen")
        font = title.font()
        font.setBold(True)
        title.setFont(font)
        layout.addWidget(title)

        headers = QGridLayout()

        headers.addWidget(
            QLabel("Sachkonto"),
            0,
            0,
        )
        headers.addWidget(
            QLabel("Brutto"),
            0,
            1,
        )
        headers.addWidget(
            QLabel("USt"),
            0,
            2,
        )

        headers.setColumnStretch(0, 1)

        layout.addLayout(headers)

        self._positions_layout = QVBoxLayout()
        layout.addLayout(self._positions_layout)

        buttons = QHBoxLayout()

        self._add_position_button = QPushButton(
            "Position hinzufügen"
        )
        self._add_position_button.clicked.connect(
            self._add_position_row
        )

        self._remove_position_button = QPushButton(
            "Letzte Position entfernen"
        )
        self._remove_position_button.clicked.connect(
            self._remove_position_row
        )

        self._booking_button = QPushButton(
            "Buchung übernehmen"
        )
        self._booking_button.clicked.connect(
            self._create_booking
        )

        buttons.addWidget(self._add_position_button)
        buttons.addWidget(self._remove_position_button)
        buttons.addStretch()
        buttons.addWidget(self._booking_button)

        layout.addLayout(buttons)

        self._status = QLabel()
        layout.addWidget(self._status)

        self._invoice_type_box.currentTextChanged.connect(
            self._update_state
        )
        self._booking_date.textChanged.connect(
            self._update_state
        )
        self._description.textChanged.connect(
            self._update_state
        )
        self._counter_account.currentTextChanged.connect(
            self._update_state
        )

    def _create_account_box(self) -> QComboBox:
        box = QComboBox()
        box.setEditable(True)
        box.addItems(self._account_display_names)
        box.setCurrentIndex(-1)

        completer = QCompleter(
            self._account_display_names,
            box,
        )
        completer.setCaseSensitivity(
            Qt.CaseSensitivity.CaseInsensitive
        )
        completer.setFilterMode(
            Qt.MatchFlag.MatchContains
        )

        box.setCompleter(completer)

        return box

    def _add_position_row(self) -> None:
        row = VatPositionRow(
            account_display_names=self._account_display_names,
            on_changed=self._update_state,
            small_business=(
                self._vat_configuration.is_small_business
            ),
        )

        self._position_rows.append(row)
        self._positions_layout.addWidget(row)

        row.set_enabled(self._enabled)

        self._update_remove_button()
        self._update_state()

    def _remove_position_row(self) -> None:
        if len(self._position_rows) <= 1:
            return

        row = self._position_rows.pop()

        self._positions_layout.removeWidget(row)
        row.deleteLater()

        self._update_remove_button()
        self._update_state()

    def _update_remove_button(self) -> None:
        self._remove_position_button.setEnabled(
            self._enabled
            and len(self._position_rows) > 1
        )

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled

        for widget in (
            self._invoice_type_box,
            self._booking_date,
            self._voucher_no,
            self._description,
            self._counter_account,
            self._add_position_button,
        ):
            widget.setEnabled(enabled)

        for row in self._position_rows:
            row.set_enabled(enabled)

        self._update_remove_button()

        if enabled:
            self._status.clear()
        else:
            self._status.setText(
                "Das Geschäftsjahr ist abgeschlossen. "
                "Buchungen sind nicht mehr möglich."
            )

        self._update_state()

    def _update_state(self) -> None:
        valid = self._enabled

        try:
            self._parse_booking_date(
                self._booking_date.text()
            )
        except ValueError:
            valid = False

        if not self._description.text().strip():
            valid = False

        counter_account = self._resolve_account(
            self._counter_account.currentText()
        )

        if counter_account is None:
            valid = False

        invoice_type = self._invoice_type_box.currentText()

        for row in self._position_rows:
            account = self._resolve_account(
                row.account_box.currentText()
            )

            if account is None:
                valid = False
            else:
                if invoice_type in (
                    _OUTPUT_INVOICE,
                    _CUSTOMER_CREDIT_NOTE,
                ):
                    if account.account_type is not AccountType.REVENUE:
                        valid = False

                if invoice_type in (
                    _INPUT_INVOICE,
                    _SUPPLIER_CREDIT_NOTE,
                ):
                    if account.account_type not in (
                        AccountType.EXPENSE,
                        AccountType.ASSET,
                    ):
                        valid = False

                if (
                    counter_account is not None
                    and counter_account.number == account.number
                ):
                    valid = False

            try:
                self._parse_amount(
                    row.amount_entry.text()
                )
            except ValueError:
                valid = False

            try:
                self._parse_tax_rate(
                    row.tax_rate_box.currentText()
                )
            except ValueError:
                valid = False

        self._booking_button.setEnabled(valid)

    def _create_booking(self) -> None:
        if not self._enabled:
            return

        counter_account = self._resolve_account(
            self._counter_account.currentText()
        )

        if counter_account is None:
            return

        try:
            booking_date = self._parse_booking_date(
                self._booking_date.text()
            )

            items = tuple(
                VatBookingItem(
                    account_number=account.number,
                    gross_amount=self._parse_amount(
                        row.amount_entry.text()
                    ),
                    tax_rate=self._parse_tax_rate(
                        row.tax_rate_box.currentText()
                    ),
                )
                for row in self._position_rows
                if (
                    account := self._resolve_account(
                        row.account_box.currentText()
                    )
                )
                is not None
            )

        except ValueError:
            return

        if len(items) != len(self._position_rows):
            return

        self._booking_date.setText(
            booking_date.strftime("%d.%m.%Y")
        )

        voucher_no = (
            self._voucher_no.text().strip()
            or None
        )

        description = (
            self._description.text().strip()
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

        self._on_booking_created(booking)

        self._clear()

        self._status.setText(
            "Buchung wurde übernommen."
        )

    def _clear(self) -> None:
        self._voucher_no.clear()
        self._description.clear()
        self._counter_account.setCurrentIndex(-1)

        while len(self._position_rows) > 1:
            self._remove_position_row()

        self._position_rows[0].clear()

        self._voucher_no.setFocus()

    def _resolve_account(
        self,
        value: str,
    ) -> Account | None:
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
        return str(account)

    @staticmethod
    def _parse_booking_date(
        value: str,
    ) -> date:
        return parse_german_date(value)

    @staticmethod
    def _parse_amount(
        value: str,
    ) -> Decimal:
        normalized = (
            value.strip()
            .replace(".", "")
            .replace(",", ".")
        )

        if not normalized:
            raise ValueError(
                "Der Betrag fehlt."
            )

        try:
            amount = Decimal(normalized)
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
        normalized = (
            value.strip()
            .removesuffix("%")
            .strip()
        )

        try:
            tax_rate = int(normalized)
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
        try:
            normalized = normalize_german_date(
                self._booking_date.text()
            )
        except ValueError:
            return

        self._booking_date.setText(normalized)

    def set_vat_accounts(
    self,
    vat_accounts: VatAccounts,
) -> None:
        """Aktualisiert die verwendeten Umsatzsteuerkonten."""

        self._vat_accounts = vat_accounts

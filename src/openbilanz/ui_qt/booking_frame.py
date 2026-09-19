"""PySide6-Eingabemaske für laufende Buchungen."""

from collections.abc import Callable
from datetime import date
from decimal import Decimal, InvalidOperation

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from openbilanz.domain.account import Account
from openbilanz.domain.booking import Booking
from openbilanz.domain.booking_line import BookingLine
from openbilanz.domain.entry_side import EntrySide
from openbilanz.domain.money import ZERO
from openbilanz.date_input import (
    normalize_german_date,
    parse_german_date,
)


class BookingFrame(QWidget):
    """Erfasst eine einfache laufende Buchung."""

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        accounts: tuple[Account, ...],
        on_booking_created: Callable[[Booking], None],
    ) -> None:
        super().__init__(parent)

        self._accounts = accounts
        self._on_booking_created = on_booking_created
        self._enabled = True

        self._accounts_by_display_name = {
            self._account_display_name(account): account
            for account in accounts
        }

        self._account_display_names = tuple(
            self._accounts_by_display_name
        )

        self._create_ui()

    def _create_ui(self) -> None:
        """Erzeugt die Buchungsmaske."""

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        form = QFormLayout()
        form.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow
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

        self._debit_account_box = QComboBox()
        self._debit_account_box.setEditable(True)
        self._debit_account_box.addItems(
            self._account_display_names
        )
        self._debit_account_box.setCurrentIndex(-1)
        self._debit_account_box.setInsertPolicy(
            QComboBox.InsertPolicy.NoInsert
        )
        form.addRow(
            "Sollkonto",
            self._debit_account_box,
        )

        self._credit_account_box = QComboBox()
        self._credit_account_box.setEditable(True)
        self._credit_account_box.addItems(
            self._account_display_names
        )
        self._credit_account_box.setCurrentIndex(-1)
        self._credit_account_box.setInsertPolicy(
            QComboBox.InsertPolicy.NoInsert
        )
        form.addRow(
            "Habenkonto",
            self._credit_account_box,
        )

        self._amount_entry = QLineEdit()
        self._amount_entry.setMaximumWidth(160)
        self._amount_entry.setAlignment(
            Qt.AlignmentFlag.AlignRight
        )
        form.addRow(
            "Betrag",
            self._amount_entry,
        )

        layout.addLayout(form)

        button_layout = QHBoxLayout()
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
        layout.addWidget(self._status_label)

        layout.addStretch()

        self._booking_date_entry.textChanged.connect(
            self._on_form_changed
        )
        self._voucher_no_entry.textChanged.connect(
            self._on_form_changed
        )
        self._description_entry.textChanged.connect(
            self._on_form_changed
        )
        self._amount_entry.textChanged.connect(
            self._on_form_changed
        )

        self._debit_account_box.currentTextChanged.connect(
            self._on_form_changed
        )
        self._credit_account_box.currentTextChanged.connect(
            self._on_form_changed
        )

        debit_line_edit = self._debit_account_box.lineEdit()

        if debit_line_edit is not None:
            debit_line_edit.textEdited.connect(
                self._filter_debit_accounts
            )

        credit_line_edit = self._credit_account_box.lineEdit()

        if credit_line_edit is not None:
            credit_line_edit.textEdited.connect(
                self._filter_credit_accounts
            )

        self._on_form_changed()

    def set_enabled(
        self,
        enabled: bool,
    ) -> None:
        """Aktiviert oder sperrt die Buchungserfassung."""

        self._enabled = enabled

        self._booking_date_entry.setEnabled(enabled)
        self._voucher_no_entry.setEnabled(enabled)
        self._description_entry.setEnabled(enabled)
        self._amount_entry.setEnabled(enabled)
        self._debit_account_box.setEnabled(enabled)
        self._credit_account_box.setEnabled(enabled)

        if enabled:
            self._on_form_changed()
        else:
            self._booking_button.setEnabled(False)
            self._status_label.setText(
                "Das Geschäftsjahr ist abgeschlossen. "
                "Buchungen sind nicht mehr möglich."
            )

    def _filter_debit_accounts(
        self,
        search_text: str,
    ) -> None:
        """Filtert die Sollkonten während der Eingabe."""

        self._filter_account_box(
            self._debit_account_box,
            search_text,
        )

    def _filter_credit_accounts(
        self,
        search_text: str,
    ) -> None:
        """Filtert die Habenkonten während der Eingabe."""

        self._filter_account_box(
            self._credit_account_box,
            search_text,
        )

    def _filter_account_box(
        self,
        box: QComboBox,
        search_text: str,
    ) -> None:
        """Filtert eine Konten-Combobox."""

        search_value = search_text.strip().casefold()

        if not search_value:
            matches = self._account_display_names
        else:
            matches = tuple(
                display_name
                for display_name in self._account_display_names
                if search_value in display_name.casefold()
            )

        current_text = box.currentText()

        box.blockSignals(True)
        box.clear()
        box.addItems(matches)
        box.setEditText(current_text)
        box.blockSignals(False)

        if matches:
            box.showPopup()

        self._on_form_changed()

    def _on_form_changed(
        self,
        *_args: object,
    ) -> None:
        """Prüft die Vollständigkeit der Buchungsmaske."""

        if not self._enabled:
            self._booking_button.setEnabled(False)
            return

        debit_account = self._resolve_account(
            self._debit_account_box.currentText()
        )
        credit_account = self._resolve_account(
            self._credit_account_box.currentText()
        )

        valid = True

        try:
            self._parse_booking_date(
                self._booking_date_entry.text()
            )
            self._parse_amount(
                self._amount_entry.text()
            )
        except ValueError:
            valid = False

        if not self._description_entry.text().strip():
            valid = False

        if debit_account is None:
            valid = False

        if credit_account is None:
            valid = False

        if (
            debit_account is not None
            and credit_account is not None
            and debit_account.number == credit_account.number
        ):
            valid = False

        self._booking_button.setEnabled(valid)
        self._status_label.clear()

    def _create_booking(self) -> None:
        """Erzeugt die Buchung aus den Eingaben."""

        if not self._enabled:
            return

        debit_account = self._resolve_account(
            self._debit_account_box.currentText()
        )
        credit_account = self._resolve_account(
            self._credit_account_box.currentText()
        )

        if (
            debit_account is None
            or credit_account is None
        ):
            return

        try:
            booking_date = self._parse_booking_date(
                self._booking_date_entry.text()
            )
            self._booking_date_entry.setText(
                booking_date.strftime("%d.%m.%Y")
            )
            amount = self._parse_amount(
                self._amount_entry.text()
            )
        except ValueError:
            return

        voucher_no = (
            self._voucher_no_entry.text().strip()
            or None
        )

        description = (
            self._description_entry.text().strip()
        )

        booking = Booking(
            booking_date=booking_date,
            voucher_no=voucher_no,
            description=description,
            lines=(
                BookingLine(
                    account_number=debit_account.number,
                    side=EntrySide.DEBIT,
                    amount=amount,
                ),
                BookingLine(
                    account_number=credit_account.number,
                    side=EntrySide.CREDIT,
                    amount=amount,
                ),
            ),
        )

        self._on_booking_created(booking)

        self._clear()

        self._status_label.setText(
            "Buchung wurde übernommen."
        )

    def _resolve_account(
        self,
        value: str,
    ) -> Account | None:
        """Ermittelt eindeutig das ausgewählte Konto."""

        normalized = value.strip()

        if not normalized:
            return None

        direct_match = self._accounts_by_display_name.get(
            normalized
        )

        if direct_match is not None:
            return direct_match

        number_matches = tuple(
            account
            for account in self._accounts
            if account.number == normalized
        )

        if len(number_matches) == 1:
            return number_matches[0]

        search_value = normalized.casefold()

        text_matches = tuple(
            account
            for account in self._accounts
            if search_value
            in self._account_display_name(account).casefold()
        )

        if len(text_matches) == 1:
            return text_matches[0]

        return None

    def _clear(self) -> None:
        """Leert die Buchungsfelder."""

        self._voucher_no_entry.clear()
        self._description_entry.clear()

        self._reset_account_box(
            self._debit_account_box
        )
        self._reset_account_box(
            self._credit_account_box
        )

        self._amount_entry.clear()

        self._voucher_no_entry.setFocus()

    def _reset_account_box(
        self,
        box: QComboBox,
    ) -> None:
        """Setzt eine Kontenauswahl zurück."""

        box.blockSignals(True)
        box.clear()
        box.addItems(
            self._account_display_names
        )
        box.setCurrentIndex(-1)
        box.blockSignals(False)

    @staticmethod
    def _account_display_name(
        account: Account,
    ) -> str:
        """Liefert die lesbare Kontendarstellung."""

        return f"{account.number} – {account.name}"

    @staticmethod
    def _parse_booking_date(
        value: str,
    ):
        """Liest eine deutsche Datumseingabe."""

        return parse_german_date(
            value
        )

    @staticmethod
    def _parse_amount(
        value: str,
    ) -> Decimal:
        """Wandelt einen deutschen Geldbetrag in Decimal um."""

        normalized = value.strip()

        if not normalized:
            raise ValueError(
                "Der Buchungsbetrag fehlt."
            )

        normalized = normalized.replace(".", "")
        normalized = normalized.replace(",", ".")

        try:
            amount = Decimal(normalized)
        except InvalidOperation as exc:
            raise ValueError(
                "Ungültiger Geldbetrag."
            ) from exc

        if amount <= ZERO:
            raise ValueError(
                "Der Buchungsbetrag muss größer als 0,00 sein."
            )

        return amount.quantize(
            Decimal("0.01")
        )

    def _normalize_booking_date(self) -> None:
        """Normalisiert das Buchungsdatum beim Verlassen des Feldes."""

        value = self._booking_date_entry.text().strip()

        if not value:
            return

        try:
            normalized = normalize_german_date(
                value
            )
        except ValueError:
            return

        self._booking_date_entry.setText(
            normalized
        )

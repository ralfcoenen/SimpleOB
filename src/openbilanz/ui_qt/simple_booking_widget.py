"""Qt-Eingabemaske für einfache Buchungen."""

from collections.abc import Callable
from datetime import date
from decimal import Decimal, InvalidOperation

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QCompleter,
    QFormLayout,
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
from openbilanz.ui.date_input import (
    normalize_german_date,
    parse_german_date,
)


class SimpleBookingWidget(QWidget):
    """Erfasst eine einfache laufende Buchung."""

    def __init__(
        self,
        *,
        accounts: tuple[Account, ...],
        on_booking_created: Callable[[Booking], None],
    ) -> None:
        super().__init__()

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
        self._update_state()

    def _create_ui(self) -> None:
        layout = QVBoxLayout(self)

        form = QFormLayout()
        layout.addLayout(form)

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
        self._description.setMinimumWidth(500)

        self._debit_account = self._create_account_box()
        self._credit_account = self._create_account_box()

        self._amount = QLineEdit()
        self._amount.setMaximumWidth(180)
        self._amount.setAlignment(
            Qt.AlignmentFlag.AlignRight
        )

        form.addRow("Datum", self._booking_date)
        form.addRow("Belegnummer", self._voucher_no)
        form.addRow("Buchungstext", self._description)
        form.addRow("Sollkonto", self._debit_account)
        form.addRow("Habenkonto", self._credit_account)
        form.addRow("Betrag", self._amount)

        self._booking_button = QPushButton(
            "Buchung übernehmen"
        )
        self._booking_button.clicked.connect(
            self._create_booking
        )

        layout.addWidget(
            self._booking_button,
            alignment=Qt.AlignmentFlag.AlignRight,
        )

        self._status = QLabel()
        layout.addWidget(self._status)

        for widget in (
            self._booking_date,
            self._voucher_no,
            self._description,
            self._amount,
        ):
            widget.textChanged.connect(
                self._update_state
            )

        self._debit_account.currentTextChanged.connect(
            self._update_state
        )
        self._credit_account.currentTextChanged.connect(
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

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled

        for widget in (
            self._booking_date,
            self._voucher_no,
            self._description,
            self._debit_account,
            self._credit_account,
            self._amount,
        ):
            widget.setEnabled(enabled)

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

        debit_account = self._resolve_account(
            self._debit_account.currentText()
        )
        credit_account = self._resolve_account(
            self._credit_account.currentText()
        )

        try:
            self._parse_booking_date(
                self._booking_date.text()
            )
            self._parse_amount(
                self._amount.text()
            )
        except ValueError:
            valid = False

        if not self._description.text().strip():
            valid = False

        if debit_account is None or credit_account is None:
            valid = False

        if (
            debit_account is not None
            and credit_account is not None
            and debit_account.number == credit_account.number
        ):
            valid = False

        self._booking_button.setEnabled(valid)

    def _create_booking(self) -> None:
        if not self._enabled:
            return

        debit_account = self._resolve_account(
            self._debit_account.currentText()
        )
        credit_account = self._resolve_account(
            self._credit_account.currentText()
        )

        if debit_account is None or credit_account is None:
            return

        try:
            booking_date = self._parse_booking_date(
                self._booking_date.text()
            )
            amount = self._parse_amount(
                self._amount.text()
            )
        except ValueError:
            return

        self._booking_date.setText(
            booking_date.strftime("%d.%m.%Y")
        )

        booking = Booking(
            booking_date=booking_date,
            voucher_no=(
                self._voucher_no.text().strip()
                or None
            ),
            description=self._description.text().strip(),
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

        self._status.setText(
            "Buchung wurde übernommen."
        )

    def _clear(self) -> None:
        self._voucher_no.clear()
        self._description.clear()
        self._debit_account.setCurrentIndex(-1)
        self._credit_account.setCurrentIndex(-1)
        self._amount.clear()

        self._voucher_no.setFocus()

    def _resolve_account(
        self,
        value: str,
    ) -> Account | None:
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

    @staticmethod
    def _account_display_name(account: Account) -> str:
        return f"{account.number} – {account.name}"

    @staticmethod
    def _parse_booking_date(value: str) -> date:
        return parse_german_date(value)

    @staticmethod
    def _parse_amount(value: str) -> Decimal:
        normalized = (
            value.strip()
            .replace(".", "")
            .replace(",", ".")
        )

        if not normalized:
            raise ValueError(
                "Der Buchungsbetrag fehlt."
            )

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
        value = self._booking_date.text().strip()

        if not value:
            return

        try:
            normalized = normalize_german_date(value)
        except ValueError:
            return

        self._booking_date.setText(normalized)

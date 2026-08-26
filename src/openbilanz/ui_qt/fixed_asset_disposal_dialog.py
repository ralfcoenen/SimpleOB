"""Dialog zum Verkauf eines Anlageguts."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
)

from openbilanz.domain.fixed_asset import FixedAsset
from openbilanz.domain.money import to_decimal
from openbilanz.ui.date_input import parse_german_date


@dataclass(frozen=True, slots=True)
class FixedAssetDisposalDialogResult:
    """Eingaben für einen Anlagenverkauf."""

    disposal_date: date
    net_sale_amount: Decimal
    settlement_account_number: str
    revenue_account_number: str
    book_value_expense_account_number: str


class FixedAssetDisposalDialog(QDialog):
    """Erfasst die Daten eines Anlagenverkaufs."""

    def __init__(
        self,
        *,
        fixed_asset: FixedAsset,
        settlement_accounts: tuple[
            tuple[str, str],
            ...
        ],
        revenue_accounts: tuple[
            tuple[str, str],
            ...
        ],
        expense_accounts: tuple[
            tuple[str, str],
            ...
        ],
        parent=None,
    ) -> None:
        super().__init__(parent)

        self.result: FixedAssetDisposalDialogResult | None = None

        self.setWindowTitle(
            "Anlagegut verkaufen"
        )
        self.setMinimumWidth(560)

        layout = QVBoxLayout(self)

        title = QLabel("Anlagegut verkaufen")
        font = title.font()
        font.setPointSize(16)
        font.setBold(True)
        title.setFont(font)

        layout.addWidget(title)

        layout.addWidget(
            QLabel(
                f"{fixed_asset.asset_code} – "
                f"{fixed_asset.description}"
            )
        )

        form = QFormLayout()

        self._disposal_date = QLineEdit(
            fixed_asset.acquisition_date.strftime(
                "%d.%m.%Y"
            )
        )

        self._net_sale_amount = QLineEdit()

        self._settlement_account = QComboBox()
        self._revenue_account = QComboBox()
        self._book_value_expense_account = QComboBox()

        for account_number, name in settlement_accounts:
            self._settlement_account.addItem(
                f"{account_number} – {name}",
                account_number,
            )

        for account_number, name in revenue_accounts:
            self._revenue_account.addItem(
                f"{account_number} – {name}",
                account_number,
            )

        for account_number, name in expense_accounts:
            self._book_value_expense_account.addItem(
                f"{account_number} – {name}",
                account_number,
            )

        revenue_index = self._revenue_account.findData(
            "8510"
        )

        if revenue_index >= 0:
            self._revenue_account.setCurrentIndex(
                revenue_index
            )

        expense_index = (
            self._book_value_expense_account.findData(
                "4840"
            )
        )

        if expense_index >= 0:
            self._book_value_expense_account.setCurrentIndex(
                expense_index
            )

        form.addRow(
            "Verkaufsdatum",
            self._disposal_date,
        )
        form.addRow(
            "Netto-Verkaufspreis",
            self._net_sale_amount,
        )
        form.addRow(
            "Bank/Forderung",
            self._settlement_account,
        )
        form.addRow(
            "Erlöskonto",
            self._revenue_account,
        )
        form.addRow(
            "Buchwertabgangskonto",
            self._book_value_expense_account,
        )

        layout.addLayout(form)

        layout.addWidget(
            QLabel(
                "Die Umsatzsteuer wird mit 19 % "
                "über das konfigurierte Umsatzsteuerkonto gebucht."
            )
        )

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )

        buttons.button(
            QDialogButtonBox.StandardButton.Ok
        ).setText(
            "Weiter"
        )

        buttons.accepted.connect(
            self._accept
        )
        buttons.rejected.connect(
            self.reject
        )

        layout.addWidget(buttons)

    def _accept(self) -> None:
        """Validiert die Eingaben."""

        try:
            disposal_date = parse_german_date(
                self._disposal_date.text()
            )

            net_sale_amount = to_decimal(
                self._net_sale_amount.text()
                .replace(".", "")
                .replace(",", ".")
            )
        except (ValueError, TypeError) as exc:
            QMessageBox.critical(
                self,
                "Ungültige Eingabe",
                str(exc),
            )
            return

        if net_sale_amount <= Decimal("0.00"):
            QMessageBox.critical(
                self,
                "Ungültiger Verkaufspreis",
                "Der Netto-Verkaufspreis muss "
                "größer als 0,00 sein.",
            )
            return

        settlement_account_number = (
            self._settlement_account.currentData()
        )
        revenue_account_number = (
            self._revenue_account.currentData()
        )
        book_value_expense_account_number = (
            self._book_value_expense_account.currentData()
        )

        if (
            not settlement_account_number
            or not revenue_account_number
            or not book_value_expense_account_number
        ):
            QMessageBox.critical(
                self,
                "Kontenauswahl fehlt",
                "Bitte wählen Sie alle erforderlichen Konten.",
            )
            return

        self.result = FixedAssetDisposalDialogResult(
            disposal_date=disposal_date,
            net_sale_amount=net_sale_amount,
            settlement_account_number=(
                settlement_account_number
            ),
            revenue_account_number=(
                revenue_account_number
            ),
            book_value_expense_account_number=(
                book_value_expense_account_number
            ),
        )

        self.accept()

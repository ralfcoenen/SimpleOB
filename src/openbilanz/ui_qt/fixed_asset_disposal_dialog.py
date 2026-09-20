"""PySide6-Dialog zur Erfassung eines Anlagenverkaufs."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation

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

from openbilanz.date_input import (
    normalize_german_date,
    parse_german_date,
)
from openbilanz.domain.account import Account
from openbilanz.domain.fixed_asset import FixedAsset


@dataclass(frozen=True, slots=True)
class FixedAssetDisposalInput:
    """Eingabedaten für einen Anlagenverkauf."""

    disposal_date: date
    voucher_no: str | None
    gross_proceeds: Decimal
    tax_rate: int
    counter_account_number: str


class FixedAssetDisposalDialog(QDialog):
    """Erfasst die Eingabedaten eines Anlagenverkaufs."""

    def __init__(
        self,
        parent=None,
        *,
        fixed_asset: FixedAsset,
        accounts: tuple[Account, ...],
    ) -> None:
        super().__init__(parent)

        self._fixed_asset = fixed_asset
        self._accounts = tuple(
            sorted(
                (
                    account
                    for account in accounts
                    if (
                        account.is_active
                        and account.number
                        != fixed_asset.asset_account_number
                    )
                ),
                key=lambda account: account.number,
            )
        )

        self.result: FixedAssetDisposalInput | None = None

        self.setWindowTitle(
            "SimpleOB – Anlagegut verkaufen"
        )
        self.setMinimumWidth(620)

        self._create_ui()

    def _create_ui(self) -> None:
        """Erzeugt die Benutzeroberfläche."""

        layout = QVBoxLayout(self)

        heading = QLabel("Anlagegut verkaufen")
        heading.setStyleSheet(
            "font-size: 18px; font-weight: bold;"
        )
        layout.addWidget(heading)

        asset_label = QLabel(
            f"{self._fixed_asset.asset_code} – "
            f"{self._fixed_asset.description}"
        )
        asset_label.setWordWrap(True)
        layout.addWidget(asset_label)

        form = QFormLayout()

        acquisition_cost_label = QLabel(
            self._format_amount(
                self._fixed_asset.acquisition_cost
            )
        )
        form.addRow(
            "Anschaffungskosten",
            acquisition_cost_label,
        )

        self._disposal_date_entry = QLineEdit(
            date.today().strftime("%d.%m.%Y")
        )
        self._disposal_date_entry.editingFinished.connect(
            self._normalize_disposal_date
        )
        form.addRow(
            "Abgangsdatum",
            self._disposal_date_entry,
        )

        self._voucher_no_entry = QLineEdit()
        form.addRow(
            "Belegnummer",
            self._voucher_no_entry,
        )

        self._gross_proceeds_entry = QLineEdit()
        form.addRow(
            "Verkaufspreis brutto",
            self._gross_proceeds_entry,
        )

        self._tax_rate_box = QComboBox()
        self._tax_rate_box.addItem("0 %", 0)
        self._tax_rate_box.addItem("7 %", 7)
        self._tax_rate_box.addItem("19 %", 19)
        self._tax_rate_box.setCurrentIndex(2)

        form.addRow(
            "Umsatzsteuer",
            self._tax_rate_box,
        )

        self._counter_account_box = QComboBox()

        for account in self._accounts:
            self._counter_account_box.addItem(
                f"{account.number} – {account.name}",
                account.number,
            )

        form.addRow(
            "Gegenkonto",
            self._counter_account_box,
        )

        layout.addLayout(form)

        note = QLabel(
            "Restbuchwert, Umsatzsteuer sowie Gewinn oder Verlust "
            "werden von SimpleOB berechnet, bevor die Buchung "
            "bestätigt wird."
        )
        note.setWordWrap(True)
        layout.addWidget(note)

        buttons = QDialogButtonBox()

        cancel_button = buttons.addButton(
            "Abbrechen",
            QDialogButtonBox.ButtonRole.RejectRole,
        )
        continue_button = buttons.addButton(
            "Vorschau",
            QDialogButtonBox.ButtonRole.AcceptRole,
        )

        cancel_button.clicked.connect(self.reject)
        continue_button.clicked.connect(
            self._accept_input
        )
        continue_button.setDefault(True)

        layout.addWidget(buttons)

    def _normalize_disposal_date(self) -> None:
        """Normalisiert eine gültige Datumseingabe."""

        value = self._disposal_date_entry.text().strip()

        if not value:
            return

        try:
            normalized = normalize_german_date(value)
        except ValueError:
            return

        self._disposal_date_entry.setText(normalized)

    @staticmethod
    def _parse_amount(
        value: str,
    ) -> Decimal:
        """Liest einen Geldbetrag."""

        normalized = (
            value.strip()
            .replace(".", "")
            .replace(",", ".")
        )

        try:
            amount = Decimal(normalized)
        except InvalidOperation as exc:
            raise ValueError(
                "Der Verkaufspreis ist ungültig."
            ) from exc

        if amount < Decimal("0.00"):
            raise ValueError(
                "Der Verkaufspreis darf nicht negativ sein."
            )

        return amount

    @staticmethod
    def _format_amount(
        value: Decimal,
    ) -> str:
        """Formatiert einen Geldbetrag."""

        return (
            f"{value:.2f} €"
            .replace(".", ",")
        )

    def _accept_input(self) -> None:
        """Übernimmt die eingegebenen Verkaufsdaten."""

        try:
            disposal_date = parse_german_date(
                self._disposal_date_entry.text()
            )

            self._disposal_date_entry.setText(
                disposal_date.strftime("%d.%m.%Y")
            )

            gross_proceeds = self._parse_amount(
                self._gross_proceeds_entry.text()
            )

            counter_account_number = (
                self._counter_account_box.currentData()
            )

            if not counter_account_number:
                raise ValueError(
                    "Bitte ein Gegenkonto auswählen."
                )

            tax_rate = self._tax_rate_box.currentData()

            if tax_rate not in (0, 7, 19):
                raise ValueError(
                    "Der Umsatzsteuersatz ist ungültig."
                )

            voucher_no = (
                self._voucher_no_entry.text().strip()
                or None
            )

        except (
            TypeError,
            ValueError,
        ) as exc:
            QMessageBox.critical(
                self,
                "Anlagenverkauf kann nicht vorbereitet werden",
                str(exc),
            )
            return

        self.result = FixedAssetDisposalInput(
            disposal_date=disposal_date,
            voucher_no=voucher_no,
            gross_proceeds=gross_proceeds,
            tax_rate=tax_rate,
            counter_account_number=(
                str(counter_account_number)
            ),
        )

        self.accept()

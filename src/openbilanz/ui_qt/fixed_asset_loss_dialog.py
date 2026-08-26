"""Dialog zum Ausbuchen eines Anlageguts wegen Totalverlust."""

from dataclasses import dataclass
from datetime import date

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
from openbilanz.ui.date_input import parse_german_date


@dataclass(frozen=True, slots=True)
class FixedAssetLossDialogResult:
    """Eingaben für einen Totalverlust."""

    loss_date: date
    loss_expense_account_number: str


class FixedAssetLossDialog(QDialog):
    """Erfasst Datum und Aufwandskonto eines Totalverlusts."""

    def __init__(
        self,
        *,
        fixed_asset: FixedAsset,
        expense_accounts: tuple[
            tuple[str, str],
            ...
        ],
        parent=None,
    ) -> None:
        super().__init__(parent)

        self.result: FixedAssetLossDialogResult | None = None

        self.setWindowTitle(
            "Anlagegut – Totalverlust"
        )
        self.setMinimumWidth(520)

        layout = QVBoxLayout(self)

        title = QLabel("Totalverlust ausbuchen")
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

        self._loss_date = QLineEdit(
            fixed_asset.acquisition_date.strftime(
                "%d.%m.%Y"
            )
        )

        self._expense_account = QComboBox()

        for account_number, name in expense_accounts:
            self._expense_account.addItem(
                f"{account_number} – {name}",
                account_number,
            )

        default_index = self._expense_account.findData(
            "4840"
        )

        if default_index >= 0:
            self._expense_account.setCurrentIndex(
                default_index
            )

        form.addRow(
            "Verlustdatum",
            self._loss_date,
        )
        form.addRow(
            "Aufwandskonto",
            self._expense_account,
        )

        layout.addLayout(form)

        layout.addWidget(
            QLabel(
                "Die Ausbuchung erfolgt erst nach "
                "ausdrücklicher Bestätigung."
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
            loss_date = parse_german_date(
                self._loss_date.text()
            )
        except ValueError as exc:
            QMessageBox.critical(
                self,
                "Ungültiges Verlustdatum",
                str(exc),
            )
            return

        account_number = (
            self._expense_account.currentData()
        )

        if not account_number:
            QMessageBox.critical(
                self,
                "Aufwandskonto fehlt",
                "Bitte wählen Sie ein Aufwandskonto.",
            )
            return

        self.result = FixedAssetLossDialogResult(
            loss_date=loss_date,
            loss_expense_account_number=(
                account_number
            ),
        )

        self.accept()

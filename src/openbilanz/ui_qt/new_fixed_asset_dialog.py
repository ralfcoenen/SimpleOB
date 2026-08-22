"""PySide6-Dialog zum Anlegen eines Anlageguts."""

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

from openbilanz.domain.fixed_asset import FixedAsset
from openbilanz.ui.date_input import (
    normalize_german_date,
    parse_german_date,
)


class NewFixedAssetDialog(QDialog):
    """Erfasst ein neues Anlagegut."""

    def __init__(
        self,
        *,
        company_id,
        parent=None,
    ) -> None:
        super().__init__(parent)

        self._company_id = company_id
        self.result: FixedAsset | None = None

        self.setWindowTitle(
            "OpenBilanz – Neues Anlagegut"
        )
        self.setMinimumWidth(520)

        layout = QVBoxLayout(self)

        title = QLabel("Neues Anlagegut")
        font = title.font()
        font.setPointSize(18)
        font.setBold(True)
        title.setFont(font)

        layout.addWidget(title)

        form = QFormLayout()

        self._asset_type = QComboBox()
        self._asset_type.addItems(
            (
                "Technische Anlagen und Maschinen",
                "Betriebs- und Geschäftsausstattung",
            )
        )
        self._asset_type.setCurrentText(
            "Betriebs- und Geschäftsausstattung"
        )

        self._asset_code = QLineEdit()
        self._description = QLineEdit()
        self._acquisition_date = QLineEdit()
        self._acquisition_cost = QLineEdit()
        self._depreciation_start_date = QLineEdit()
        self._useful_life_months = QLineEdit()

        form.addRow(
            "Anlagenart",
            self._asset_type,
        )
        form.addRow(
            "Anlagen-ID",
            self._asset_code,
        )
        form.addRow(
            "Bezeichnung",
            self._description,
        )
        form.addRow(
            "Anschaffungsdatum",
            self._acquisition_date,
        )
        form.addRow(
            "Anschaffungskosten",
            self._acquisition_cost,
        )
        form.addRow(
            "AfA-Beginn",
            self._depreciation_start_date,
        )
        form.addRow(
            "Nutzungsdauer in Monaten",
            self._useful_life_months,
        )
        form.addRow(
            "AfA-Konto",
            QLabel(
                "4830 – Abschreibungen auf Sachanlagen"
            ),
        )

        layout.addLayout(form)

        layout.addWidget(
            QLabel(
                "Datum: TT.MM.JJJJ · auch TTMMJJJJ "
                "oder TTMMJJ möglich · "
                "Betrag z. B. 2400,00"
            )
        )

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )

        buttons.button(
            QDialogButtonBox.StandardButton.Save
        ).setText("Anlagegut anlegen")

        buttons.button(
            QDialogButtonBox.StandardButton.Cancel
        ).setText("Abbrechen")

        buttons.accepted.connect(
            self._create_fixed_asset
        )
        buttons.rejected.connect(
            self.reject
        )

        layout.addWidget(buttons)

        self._acquisition_date.editingFinished.connect(
            lambda: self._normalize_date(
                self._acquisition_date
            )
        )
        self._depreciation_start_date.editingFinished.connect(
            lambda: self._normalize_date(
                self._depreciation_start_date
            )
        )

        self._asset_code.setFocus()

    @staticmethod
    def _normalize_date(
        entry: QLineEdit,
    ) -> None:
        value = entry.text().strip()

        if not value:
            return

        try:
            value = normalize_german_date(value)
        except ValueError:
            return

        entry.setText(value)

    @staticmethod
    def _parse_amount(
        value: str,
    ) -> Decimal:
        normalized = (
            value.strip()
            .replace(".", "")
            .replace(",", ".")
        )

        try:
            return Decimal(normalized)
        except InvalidOperation as exc:
            raise ValueError(
                "Die Anschaffungskosten sind ungültig."
            ) from exc

    def _create_fixed_asset(self) -> None:
        try:
            acquisition_date = parse_german_date(
                self._acquisition_date.text()
            )

            depreciation_start_date = parse_german_date(
                self._depreciation_start_date.text()
            )

            acquisition_cost = self._parse_amount(
                self._acquisition_cost.text()
            )

            useful_life_months = int(
                self._useful_life_months.text().strip()
            )

            asset_type = self._asset_type.currentText()

            if (
                asset_type
                == "Technische Anlagen und Maschinen"
            ):
                position_code = (
                    "HGB.266.AKTIVA.A.II.2"
                )
                asset_account_number = "0200"

            elif (
                asset_type
                == "Betriebs- und Geschäftsausstattung"
            ):
                position_code = (
                    "HGB.266.AKTIVA.A.II.3"
                )
                asset_account_number = "0400"

            else:
                raise ValueError(
                    "Die Anlagenart ist ungültig."
                )

            self.result = FixedAsset(
                company_id=self._company_id,
                asset_code=self._asset_code.text(),
                description=self._description.text(),
                position_code=position_code,
                asset_account_number=(
                    asset_account_number
                ),
                depreciation_expense_account_number=(
                    "4830"
                ),
                acquisition_date=acquisition_date,
                acquisition_cost=acquisition_cost,
                depreciation_start_date=(
                    depreciation_start_date
                ),
                useful_life_months=useful_life_months,
            )

        except (
            TypeError,
            ValueError,
        ) as exc:
            QMessageBox.critical(
                self,
                "Anlagegut kann nicht angelegt werden",
                str(exc),
            )
            return

        self.accept()

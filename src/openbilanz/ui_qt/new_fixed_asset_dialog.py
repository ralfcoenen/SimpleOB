"""PySide6-Dialog zum Anlegen eines Anlageguts."""

from dataclasses import dataclass
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


@dataclass(frozen=True, slots=True)
class FixedAssetAccountOption:
    """Ein auswählbares Anlagekonto."""

    account_number: str
    account_name: str
    position_code: str

    def __str__(self) -> str:
        return (
            f"{self.account_number} - "
            f"{self.account_name}"
        )


class NewFixedAssetDialog(QDialog):
    """Erfasst ein neues Anlagegut."""

    def __init__(
        self,
        *,
        company_id,
        asset_accounts: tuple[
            FixedAssetAccountOption,
            ...
        ],
        fixed_asset: FixedAsset | None = None,
        acquisition_linked: bool = False,
        parent=None,
    ) -> None:
        super().__init__(parent)

        self._company_id = company_id
        self._asset_accounts = asset_accounts

        if not asset_accounts:
            raise ValueError(
                "Es sind keine Anlagekonten konfiguriert."
            )
        self._fixed_asset = fixed_asset
        self._acquisition_linked = acquisition_linked
        self.result: FixedAsset | None = None

        editing = fixed_asset is not None

        self.setWindowTitle(
            "OpenBilanz – Anlagegut bearbeiten"
            if editing
            else "OpenBilanz – Neues Anlagegut"
        )

        self.setMinimumWidth(520)

        layout = QVBoxLayout(self)

        title = QLabel(
            "Anlagegut bearbeiten"
            if editing
            else "Neues Anlagegut"
        )
        font = title.font()
        font.setPointSize(18)
        font.setBold(True)
        title.setFont(font)

        layout.addWidget(title)

        form = QFormLayout()

        self._asset_type = QComboBox()

        for option in self._asset_accounts:
            self._asset_type.addItem(
                str(option),
                option,
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
        ).setText(
            "Änderungen speichern"
            if editing
            else "Anlagegut anlegen"
        )

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

        if fixed_asset is not None:
            self._populate_from_fixed_asset(
                fixed_asset
            )

            if acquisition_linked:
                self._asset_type.setEnabled(False)
                self._acquisition_date.setEnabled(False)
                self._acquisition_cost.setEnabled(False)

        self._asset_code.setFocus()

    def _populate_from_fixed_asset(
        self,
        fixed_asset: FixedAsset,
    ) -> None:
        """Übernimmt die Stammdaten eines bestehenden Anlageguts."""

        for index in range(
            self._asset_type.count()
        ):
            option = self._asset_type.itemData(
                index
            )

            if (
                option.account_number
                == fixed_asset.asset_account_number
            ):
                self._asset_type.setCurrentIndex(
                    index
                )
                break

        self._asset_code.setText(
            fixed_asset.asset_code
        )
        self._description.setText(
            fixed_asset.description
        )
        self._acquisition_date.setText(
            f"{fixed_asset.acquisition_date:%d.%m.%Y}"
        )
        self._acquisition_cost.setText(
            f"{fixed_asset.acquisition_cost:.2f}".replace(
                ".",
                ",",
            )
        )
        self._depreciation_start_date.setText(
            f"{fixed_asset.depreciation_start_date:%d.%m.%Y}"
        )
        self._useful_life_months.setText(
            str(fixed_asset.useful_life_months)
        )

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

            asset_option = (
                self._asset_type.currentData()
            )

            if not isinstance(
                asset_option,
                FixedAssetAccountOption,
            ):
                raise ValueError(
                    "Das Anlagekonto ist ungültig."
                )

            position_code = (
                asset_option.position_code
            )
            asset_account_number = (
                asset_option.account_number
            )

            if self._fixed_asset is None:
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
                    useful_life_months=(
                        useful_life_months
                    ),
                )
            else:
                self.result = FixedAsset(
                    fixed_asset_id=(
                        self._fixed_asset.fixed_asset_id
                    ),
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
                    useful_life_months=(
                        useful_life_months
                    ),
                    status=self._fixed_asset.status,
                    disposal_date=(
                        self._fixed_asset.disposal_date
                    ),
                )

        except (
            TypeError,
            ValueError,
        ) as exc:
            QMessageBox.critical(
                self,
                (
                    "Anlagegut kann nicht geändert werden"
                    if self._fixed_asset is not None
                    else "Anlagegut kann nicht angelegt werden"
                ),
                str(exc),
            )
            return

        self.accept()

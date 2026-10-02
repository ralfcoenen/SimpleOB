"""PySide6-Dialog zum Anlegen und Bearbeiten eines Anlageguts."""

from datetime import date
from decimal import Decimal, InvalidOperation
from uuid import UUID

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

from openbilanz.amount_input import normalize_german_amount
from openbilanz.date_input import (
    normalize_german_date,
    parse_german_date,
)
from openbilanz.domain.fixed_asset import FixedAsset

_TECHNICAL_EQUIPMENT = "Technische Anlagen und Maschinen"
_BUSINESS_EQUIPMENT = "Betriebs- und Geschäftsausstattung"


class NewFixedAssetDialog(QDialog):
    """Erfasst ein neues oder bearbeitet ein vorhandenes Anlagegut."""

    def __init__(
        self,
        parent=None,
        *,
        company_id: UUID,
        depreciation_expense_account_number: str,
        fixed_asset: FixedAsset | None = None,
        acquisition_linked: bool = False,
    ) -> None:
        super().__init__(parent)

        self._company_id = company_id
        self._depreciation_expense_account_number = (
            depreciation_expense_account_number
        )
        self._fixed_asset = fixed_asset
        self._acquisition_linked = acquisition_linked
        self._editing = fixed_asset is not None

        self.result: FixedAsset | None = None

        self.setWindowTitle(
            (
                "SimpleOB – Anlagegut bearbeiten"
                if self._editing
                else "SimpleOB – Anlagegut anlegen"
            )
        )
        self.setMinimumWidth(620)

        self._create_ui()

        if fixed_asset is not None:
            self._load_fixed_asset(
                fixed_asset
            )

        self._update_editing_state()

    def _create_ui(self) -> None:
        """Erzeugt die Benutzeroberfläche."""

        layout = QVBoxLayout(self)

        heading = QLabel(
            (
                "Anlagegut bearbeiten"
                if self._editing
                else "Neues Anlagegut"
            )
        )
        heading.setStyleSheet(
            "font-size: 18px; font-weight: bold;"
        )
        layout.addWidget(
            heading
        )

        form = QFormLayout()

        self._asset_code_entry = QLineEdit()
        form.addRow(
            "Anlagen-ID",
            self._asset_code_entry,
        )

        self._description_entry = QLineEdit()
        self._description_entry.setMinimumWidth(
            420
        )
        form.addRow(
            "Bezeichnung",
            self._description_entry,
        )

        self._asset_type_box = QComboBox()
        self._asset_type_box.addItems(
            (
                _TECHNICAL_EQUIPMENT,
                _BUSINESS_EQUIPMENT,
            )
        )
        form.addRow(
            "Anlagenart",
            self._asset_type_box,
        )

        self._acquisition_date_entry = QLineEdit(
            date.today().strftime("%d.%m.%Y")
        )
        self._acquisition_date_entry.editingFinished.connect(
            lambda: self._normalize_date_entry(
                self._acquisition_date_entry
            )
        )
        form.addRow(
            "Anschaffungsdatum",
            self._acquisition_date_entry,
        )

        self._acquisition_cost_entry = QLineEdit()
        self._acquisition_cost_entry.setPlaceholderText(
            "0,00"
        )
        self._acquisition_cost_entry.editingFinished.connect(
            self._normalize_acquisition_cost
        )
        form.addRow(
            "Anschaffungskosten",
            self._acquisition_cost_entry,
        )

        self._depreciation_start_date_entry = QLineEdit(
            date.today().strftime("%d.%m.%Y")
        )
        self._depreciation_start_date_entry.editingFinished.connect(
            lambda: self._normalize_date_entry(
                self._depreciation_start_date_entry
            )
        )
        form.addRow(
            "AfA-Beginn",
            self._depreciation_start_date_entry,
        )

        self._useful_life_months_entry = QLineEdit()
        form.addRow(
            "Nutzungsdauer in Monaten",
            self._useful_life_months_entry,
        )

        layout.addLayout(
            form
        )

        self._editing_note = QLabel()
        self._editing_note.setWordWrap(True)
        layout.addWidget(
            self._editing_note
        )

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(
            self._create_fixed_asset
        )
        buttons.rejected.connect(
            self.reject
        )

        layout.addWidget(
            buttons
        )

    def _update_editing_state(self) -> None:
        """Berücksichtigt Einschränkungen bei vorhandenen Anlagegütern."""

        if not self._editing:
            self._editing_note.clear()
            return

        self._asset_code_entry.setEnabled(
            False
        )

        if self._acquisition_linked:
            self._acquisition_date_entry.setEnabled(
                False
            )
            self._acquisition_cost_entry.setEnabled(
                False
            )
            self._asset_type_box.setEnabled(
                False
            )

            self._editing_note.setText(
                "Die Anschaffungsbuchung ist bereits zugeordnet. "
                "Anschaffungsdatum, Anschaffungskosten und "
                "Anlagenart können deshalb nicht mehr geändert werden."
            )
        else:
            self._editing_note.clear()

    def _load_fixed_asset(
        self,
        fixed_asset: FixedAsset,
    ) -> None:
        """Übernimmt ein vorhandenes Anlagegut in die Eingabefelder."""

        self._asset_code_entry.setText(
            fixed_asset.asset_code
        )
        self._description_entry.setText(
            fixed_asset.description
        )

        if (
            fixed_asset.position_code
            == "HGB.266.AKTIVA.A.II.2"
        ):
            self._asset_type_box.setCurrentText(
                _TECHNICAL_EQUIPMENT
            )
        elif (
            fixed_asset.position_code
            == "HGB.266.AKTIVA.A.II.3"
        ):
            self._asset_type_box.setCurrentText(
                _BUSINESS_EQUIPMENT
            )

        self._acquisition_date_entry.setText(
            fixed_asset.acquisition_date.strftime(
                "%d.%m.%Y"
            )
        )
        self._acquisition_cost_entry.setText(
            self._format_amount_for_input(
                fixed_asset.acquisition_cost
            )
        )
        self._depreciation_start_date_entry.setText(
            fixed_asset.depreciation_start_date.strftime(
                "%d.%m.%Y"
            )
        )
        self._useful_life_months_entry.setText(
            str(
                fixed_asset.useful_life_months
            )
        )

    @staticmethod
    def _format_amount_for_input(
        value: Decimal,
    ) -> str:
        """Formatiert einen Geldbetrag für das Eingabefeld."""

        return format(
            value,
            ".2f",
        ).replace(
            ".",
            ",",
        )

    @staticmethod
    def _parse_date(
        value: str,
    ):
        """Liest eine deutsche Datumseingabe."""

        return parse_german_date(
            value
        )

    def _normalize_date_entry(
        self,
        entry: QLineEdit,
    ) -> None:
        """Normalisiert eine gültige Datumseingabe."""

        value = entry.text().strip()

        if not value:
            return

        try:
            normalized = normalize_german_date(
                value
            )
        except ValueError:
            return

        entry.setText(
            normalized
        )

    def _normalize_acquisition_cost(self) -> None:
        """Normalisiert die Anschaffungskosten."""

        value = self._acquisition_cost_entry.text().strip()

        if not value:
            return

        try:
            normalized = normalize_german_amount(
                value
            )
        except ValueError:
            return

        self._acquisition_cost_entry.setText(
            normalized
        )

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
            return Decimal(
                normalized
            )
        except InvalidOperation as exc:
            raise ValueError(
                "Die Anschaffungskosten sind ungültig."
            ) from exc

    def _create_fixed_asset(self) -> None:
        """Erzeugt das neue oder geänderte Anlagegut."""

        try:
            acquisition_date = self._parse_date(
                self._acquisition_date_entry.text()
            )

            depreciation_start_date = self._parse_date(
                self._depreciation_start_date_entry.text()
            )

            self._acquisition_date_entry.setText(
                acquisition_date.strftime(
                    "%d.%m.%Y"
                )
            )
            self._depreciation_start_date_entry.setText(
                depreciation_start_date.strftime(
                    "%d.%m.%Y"
                )
            )

            acquisition_cost = self._parse_amount(
                self._acquisition_cost_entry.text()
            )

            useful_life_months_text = (
                self._useful_life_months_entry.text().strip()
            )

            if not useful_life_months_text:
                raise ValueError(
                    "Die Nutzungsdauer in Monaten muss "
                    "angegeben werden."
                )

            try:
                useful_life_months = int(
                    useful_life_months_text
                )
            except ValueError as exc:
                raise ValueError(
                    "Die Nutzungsdauer in Monaten muss "
                    "eine positive ganze Zahl sein."
                ) from exc

            if useful_life_months <= 0:
                raise ValueError(
                    "Die Nutzungsdauer in Monaten muss "
                    "eine positive ganze Zahl sein."
                )

            asset_type = (
                self._asset_type_box.currentText()
            )

            if asset_type == _TECHNICAL_EQUIPMENT:
                position_code = (
                    "HGB.266.AKTIVA.A.II.2"
                )
                asset_account_number = "0200"

            elif asset_type == _BUSINESS_EQUIPMENT:
                position_code = (
                    "HGB.266.AKTIVA.A.II.3"
                )
                asset_account_number = "0400"

            else:
                raise ValueError(
                    "Die Anlagenart ist ungültig."
                )

            fixed_asset_kwargs = {
                "company_id": self._company_id,
                "asset_code": self._asset_code_entry.text(),
                "description": self._description_entry.text(),
                "position_code": position_code,
                "asset_account_number": (
                    asset_account_number
                ),
                "depreciation_expense_account_number": (
                    self._fixed_asset.depreciation_expense_account_number
                    if self._fixed_asset is not None
                    else self._depreciation_expense_account_number
                ),
                "acquisition_date": acquisition_date,
                "acquisition_cost": acquisition_cost,
                "depreciation_start_date": (
                    depreciation_start_date
                ),
                "useful_life_months": useful_life_months,
            }

            if self._fixed_asset is not None:
                fixed_asset_kwargs.update(
                    {
                        "fixed_asset_id": (
                            self._fixed_asset.fixed_asset_id
                        ),
                        "status": (
                            self._fixed_asset.status
                        ),
                        "disposal_date": (
                            self._fixed_asset.disposal_date
                        ),
                    }
                )

            fixed_asset = FixedAsset(
                **fixed_asset_kwargs
            )

        except (
            TypeError,
            ValueError,
        ) as exc:
            QMessageBox.critical(
                self,
                (
                    "Anlagegut kann nicht bearbeitet werden"
                    if self._editing
                    else "Anlagegut kann nicht angelegt werden"
                ),
                str(exc),
            )
            return

        self.result = fixed_asset
        self.accept()

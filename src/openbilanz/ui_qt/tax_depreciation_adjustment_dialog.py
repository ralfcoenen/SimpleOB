"""PySide6-Dialog zur Erfassung einer steuerlichen AfA-Abweichung."""

from decimal import Decimal, InvalidOperation

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
)

from openbilanz.domain.fixed_asset import FixedAsset
from openbilanz.domain.fixed_asset_depreciation import (
    FixedAssetDepreciation,
)


class TaxDepreciationAdjustmentDialog(QDialog):
    """Erfasst die steuerliche AfA zu einer bestätigten HGB-Abschreibung."""

    def __init__(
        self,
        parent=None,
        *,
        fixed_asset: FixedAsset,
        depreciation: FixedAssetDepreciation,
        initial_tax_amount: Decimal,
    ) -> None:
        super().__init__(parent)

        self._fixed_asset = fixed_asset
        self._depreciation = depreciation

        self.result: Decimal | None = None

        self.setWindowTitle(
            "SimpleOB – Steuerliche AfA-Abweichung"
        )
        self.setFixedSize(
            560,
            360,
        )

        layout = QVBoxLayout(self)

        heading = QLabel(
            "Steuerliche AfA-Abweichung"
        )
        heading.setStyleSheet(
            "font-size: 18px; font-weight: bold;"
        )
        layout.addWidget(
            heading
        )

        form = QFormLayout()

        form.addRow(
            "Anlagegut",
            QLabel(
                (
                    f"{self._fixed_asset.asset_code} – "
                    f"{self._fixed_asset.description}"
                )
            ),
        )

        form.addRow(
            "Abschreibungsdatum",
            QLabel(
                self._depreciation.depreciation_date.strftime(
                    "%d.%m.%Y"
                )
            ),
        )

        form.addRow(
            "HGB-AfA",
            QLabel(
                (
                    f"{self._format_amount_for_display(
                        self._depreciation.amount
                    )} €"
                )
            ),
        )

        self._tax_amount_entry = QLineEdit(
            self._format_amount_for_input(
                initial_tax_amount
            )
        )
        self._tax_amount_entry.textChanged.connect(
            self._update_difference
        )
        form.addRow(
            "Steuerliche AfA",
            self._tax_amount_entry,
        )

        self._difference_label = QLabel()
        form.addRow(
            "Differenz",
            self._difference_label,
        )

        layout.addLayout(
            form
        )

        note = QLabel(
            (
                "Nur abweichende steuerliche AfA erfassen. "
                "Entspricht die steuerliche AfA der HGB-AfA, "
                "wird keine Abweichung gespeichert."
            )
        )
        note.setWordWrap(
            True
        )
        layout.addWidget(
            note
        )

        layout.addStretch()

        buttons = QDialogButtonBox()

        save_button = buttons.addButton(
            "Speichern",
            QDialogButtonBox.ButtonRole.AcceptRole,
        )
        cancel_button = buttons.addButton(
            "Abbrechen",
            QDialogButtonBox.ButtonRole.RejectRole,
        )

        save_button.clicked.connect(
            self._save
        )
        cancel_button.clicked.connect(
            self.reject
        )

        layout.addWidget(
            buttons
        )

        self._update_difference()
        self._tax_amount_entry.setFocus()
        self._tax_amount_entry.selectAll()

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
    def _format_amount_for_display(
        value: Decimal,
    ) -> str:
        """Formatiert einen Geldbetrag für die Anzeige."""

        return format(
            value,
            ".2f",
        ).replace(
            ".",
            ",",
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
            amount = Decimal(
                normalized
            )
        except InvalidOperation as exc:
            raise ValueError(
                "Die steuerliche AfA ist ungültig."
            ) from exc

        if amount < Decimal("0.00"):
            raise ValueError(
                "Die steuerliche AfA darf nicht negativ sein."
            )

        return amount

    def _update_difference(self) -> None:
        """Berechnet die Differenz zur HGB-AfA."""

        try:
            tax_amount = self._parse_amount(
                self._tax_amount_entry.text()
            )
        except ValueError:
            self._difference_label.setText(
                "–"
            )
            return

        difference = (
            tax_amount
            - self._depreciation.amount
        )

        self._difference_label.setText(
            (
                f"{self._format_amount_for_display(
                    difference
                )} €"
            )
        )

    def _save(self) -> None:
        """Übernimmt die eingegebene steuerliche AfA."""

        try:
            tax_amount = self._parse_amount(
                self._tax_amount_entry.text()
            )
        except ValueError as exc:
            QMessageBox.critical(
                self,
                "Steuerliche AfA-Abweichung",
                str(exc),
            )
            return

        self.result = tax_amount
        self.accept()

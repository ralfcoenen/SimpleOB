"""Dialog für mandantenbezogene Einstellungen der KR-Anzeige."""

from datetime import date
from decimal import Decimal

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
)

from simpleob.amount_input import format_german_amount, parse_german_amount
from simpleob.date_input import GermanDateEdit
from simpleob.domain.kr_settings import (
    KrAnnualTurnoverAddition,
    KrSettings,
)


class KrSettingsDialog(QDialog):
    """Bearbeitet KR-Einstellungen eines einzelnen Mandanten."""

    def __init__(
        self,
        parent,
        *,
        settings: KrSettings,
        today: date | None = None,
    ) -> None:
        super().__init__(parent)
        self._settings = settings
        self._today = today or date.today()
        self.result: KrSettings | None = None
        self.setWindowTitle("Kleinunternehmerregelung")
        self.setMinimumWidth(480)

        layout = QVBoxLayout(self)
        info_label = QLabel(
            "Diese Angaben steuern nur die informative Umsatzüberwachung "
            "zur Kleinunternehmerregelung. Sie ändern keine steuerliche Behandlung."
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        form = QFormLayout()
        layout.addLayout(form)

        self._activity_start_entry = GermanDateEdit(
            value=settings.activity_start_date,
            optional=True,
        )
        form.addRow("Beginn der unternehmerischen Tätigkeit", self._activity_start_entry)

        amounts_by_year = {
            item.calendar_year: item.amount
            for item in settings.external_turnovers
        }
        self._previous_year = self._today.year - 1
        self._current_year = self._today.year
        self._turnover_entries: dict[int, QLineEdit] = {}
        editable_years = sorted(
            set(amounts_by_year) | {self._previous_year, self._current_year}
        )
        for year in editable_years:
            entry = self._amount_entry(
                amounts_by_year.get(year, Decimal("0.00"))
            )
            self._turnover_entries[year] = entry
            form.addRow(f"Extern ergänzter Umsatz {year}", entry)

        self._waiver_checkbox = QCheckBox(
            "Auf die Kleinunternehmerregelung wurde verzichtet"
        )
        self._waiver_checkbox.setChecked(settings.waiver_declared)
        form.addRow(self._waiver_checkbox)
        self._waiver_date_entry = GermanDateEdit(
            value=settings.waiver_date,
            optional=True,
        )
        self._waiver_date_entry.setEnabled(settings.waiver_declared)
        form.addRow("Datum des Verzichts", self._waiver_date_entry)
        self._waiver_checkbox.toggled.connect(self._waiver_date_entry.setEnabled)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    @staticmethod
    def _amount_entry(amount: Decimal) -> QLineEdit:
        entry = QLineEdit(format_german_amount(amount))
        entry.setPlaceholderText("0,00")
        entry.setMaximumWidth(180)
        return entry

    @staticmethod
    def _parse_amount(entry: QLineEdit) -> Decimal:
        amount = parse_german_amount(entry.text())
        if not amount.is_finite():
            raise ValueError("Externe Umsatzergänzungen müssen endliche Beträge sein.")
        if amount < Decimal("0.00"):
            raise ValueError("Externe Umsatzergänzungen dürfen nicht negativ sein.")
        if amount != amount.quantize(Decimal("0.01")):
            raise ValueError(
                "Externe Umsatzergänzungen dürfen höchstens zwei Nachkommastellen haben."
            )
        return amount

    def _save(self) -> None:
        try:
            activity_start_date = self._activity_start_entry.date_value()
            waiver_declared = self._waiver_checkbox.isChecked()
            waiver_date = (
                self._waiver_date_entry.date_value()
                if waiver_declared
                else None
            )
            amounts = {
                item.calendar_year: item.amount
                for item in self._settings.external_turnovers
            }
            for year, entry in self._turnover_entries.items():
                amounts[year] = self._parse_amount(entry)
            settings = KrSettings(
                company_id=self._settings.company_id,
                activity_start_date=activity_start_date,
                waiver_declared=waiver_declared,
                waiver_date=waiver_date,
                external_turnovers=tuple(
                    KrAnnualTurnoverAddition(calendar_year=year, amount=amount)
                    for year, amount in sorted(amounts.items())
                ),
            )
        except (TypeError, ValueError) as exc:
            QMessageBox.critical(
                self,
                "Ungültige Einstellungen zur Kleinunternehmerregelung",
                str(exc),
            )
            return

        self.result = settings
        self.accept()

"""PySide6-Dialog zur Erfassung der Ergebnisverwendung."""

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

from simpleob.amount_input import normalize_german_amount
from simpleob.domain.profit_appropriation_annual_data import (
    ProfitAppropriationAnnualData,
)


class ProfitAppropriationDialog(QDialog):
    """Erfasst den Ergebnisverwendungsbeschluss eines Geschäftsjahres."""

    def __init__(
        self,
        parent=None,
        *,
        fiscal_year_name: str,
        net_income: Decimal,
        previous_profit_loss_carryforward: Decimal,
        initial_data: ProfitAppropriationAnnualData | None,
        read_only: bool = False,
    ) -> None:
        super().__init__(parent)

        self._read_only = read_only
        self.result: ProfitAppropriationAnnualData | None = None

        if initial_data is None:
            initial_data = ProfitAppropriationAnnualData(
                statutory_reserve_addition=Decimal("0.00"),
                other_revenue_reserves_addition=Decimal("0.00"),
                statutory_reserve_release=Decimal("0.00"),
                other_revenue_reserves_release=Decimal("0.00"),
                distribution=Decimal("0.00"),
                profit_loss_carryforward=(
                    net_income
                    + previous_profit_loss_carryforward
                ),
            )

        self.setWindowTitle(
            "SimpleOB – Ergebnisverwendungsbeschluss"
        )
        self.setMinimumWidth(620)

        layout = QVBoxLayout(self)

        heading = QLabel(
            "Ergebnisverwendungsbeschluss"
        )
        heading.setStyleSheet(
            "font-size: 18px; font-weight: bold;"
        )
        layout.addWidget(heading)

        form = QFormLayout()

        form.addRow(
            "Geschäftsjahr",
            QLabel(fiscal_year_name),
        )

        form.addRow(
            "Jahresüberschuss/-fehlbetrag",
            QLabel(
                f"{self._format_amount(net_income)} €"
            ),
        )

        form.addRow(
            "Gewinn-/Verlustvortrag Vorjahr",
            QLabel(
                f"{self._format_amount(
                    previous_profit_loss_carryforward
                )} €"
            ),
        )

        self._statutory_reserve_addition_entry = (
            self._create_amount_entry(
                initial_data.statutory_reserve_addition
            )
        )
        form.addRow(
            "Zuführung gesetzliche Rücklage",
            self._statutory_reserve_addition_entry,
        )

        self._other_revenue_reserves_addition_entry = (
            self._create_amount_entry(
                initial_data.other_revenue_reserves_addition
            )
        )
        form.addRow(
            "Zuführung andere Gewinnrücklagen",
            self._other_revenue_reserves_addition_entry,
        )

        self._statutory_reserve_release_entry = (
            self._create_amount_entry(
                initial_data.statutory_reserve_release
            )
        )
        form.addRow(
            "Auflösung gesetzliche Rücklage",
            self._statutory_reserve_release_entry,
        )

        self._other_revenue_reserves_release_entry = (
            self._create_amount_entry(
                initial_data.other_revenue_reserves_release
            )
        )
        form.addRow(
            "Auflösung andere Gewinnrücklagen",
            self._other_revenue_reserves_release_entry,
        )

        self._distribution_entry = self._create_amount_entry(
            initial_data.distribution
        )
        form.addRow(
            "Ausschüttung",
            self._distribution_entry,
        )

        self._profit_loss_carryforward_entry = (
            self._create_amount_entry(
                initial_data.profit_loss_carryforward
            )
        )
        form.addRow(
            "Neuer Gewinn-/Verlustvortrag",
            self._profit_loss_carryforward_entry,
        )

        layout.addLayout(form)

        note = QLabel(
            (
                "Der Beschluss wird dem abgeschlossenen "
                "Geschäftsjahr zugeordnet. Die daraus entstehenden "
                "Buchungen werden erst im Folgegeschäftsjahr "
                "gesondert vorgeschlagen und bestätigt."
            )
        )
        note.setWordWrap(True)
        layout.addWidget(note)

        if self._read_only:
            locked_note = QLabel(
                (
                    "Der Beschluss kann nicht geändert werden, "
                    "solange daraus wirksame "
                    "Umsetzungsbuchungen vorhanden sind."
                )
            )
            locked_note.setWordWrap(True)
            layout.addWidget(locked_note)

        layout.addStretch()

        buttons = QDialogButtonBox()

        if self._read_only:
            close_button = buttons.addButton(
                "Schließen",
                QDialogButtonBox.ButtonRole.RejectRole,
            )
            close_button.clicked.connect(
                self.reject
            )
        else:
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

        layout.addWidget(buttons)

        self._set_entries_read_only(
            self._read_only
        )

        if not self._read_only:
            self._statutory_reserve_addition_entry.setFocus()
            self._statutory_reserve_addition_entry.selectAll()

    def _create_amount_entry(
        self,
        value: Decimal,
    ) -> QLineEdit:
        """Erzeugt ein Betragseingabefeld."""

        entry = QLineEdit(
            self._format_amount_for_input(value)
        )
        entry.setPlaceholderText(
            "0,00"
        )
        entry.editingFinished.connect(
            lambda entry=entry:
            self._normalize_amount_entry(entry)
        )

        return entry

    def _normalize_amount_entry(
        self,
        entry: QLineEdit,
    ) -> None:
        """Normalisiert eine Betragseingabe."""

        value = entry.text().strip()

        if not value:
            return

        try:
            normalized = normalize_german_amount(
                value
            )
        except ValueError:
            return

        entry.setText(normalized)

    def _set_entries_read_only(
        self,
        read_only: bool,
    ) -> None:
        """Schaltet alle Beschlussfelder auf Nur-Lesen."""

        entries = (
            self._statutory_reserve_addition_entry,
            self._other_revenue_reserves_addition_entry,
            self._statutory_reserve_release_entry,
            self._other_revenue_reserves_release_entry,
            self._distribution_entry,
            self._profit_loss_carryforward_entry,
        )

        for entry in entries:
            entry.setReadOnly(read_only)

    @staticmethod
    def _format_amount_for_input(
        value: Decimal,
    ) -> str:
        """Formatiert einen Geldbetrag für ein Eingabefeld."""

        return format(
            value,
            ".2f",
        ).replace(
            ".",
            ",",
        )

    @staticmethod
    def _format_amount(
        value: Decimal,
    ) -> str:
        """Formatiert einen Geldbetrag für die Anzeige."""

        formatted = f"{value:,.2f}"

        return (
            formatted
            .replace(",", "X")
            .replace(".", ",")
            .replace("X", ".")
        )

    @staticmethod
    def _parse_amount(
        value: str,
        *,
        field_name: str,
        allow_negative: bool = False,
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
                f"{field_name} ist ungültig."
            ) from exc

        if (
            not allow_negative
            and amount < Decimal("0.00")
        ):
            raise ValueError(
                f"{field_name} darf nicht negativ sein."
            )

        return amount

    def _build_result(
        self,
    ) -> ProfitAppropriationAnnualData:
        """Erzeugt die Ergebnisverwendungsdaten aus den Eingaben."""

        return ProfitAppropriationAnnualData(
            statutory_reserve_addition=self._parse_amount(
                self._statutory_reserve_addition_entry.text(),
                field_name="Zuführung gesetzliche Rücklage",
            ),
            other_revenue_reserves_addition=self._parse_amount(
                self._other_revenue_reserves_addition_entry.text(),
                field_name="Zuführung andere Gewinnrücklagen",
            ),
            statutory_reserve_release=self._parse_amount(
                self._statutory_reserve_release_entry.text(),
                field_name="Auflösung gesetzliche Rücklage",
            ),
            other_revenue_reserves_release=self._parse_amount(
                self._other_revenue_reserves_release_entry.text(),
                field_name="Auflösung andere Gewinnrücklagen",
            ),
            distribution=self._parse_amount(
                self._distribution_entry.text(),
                field_name="Ausschüttung",
            ),
            profit_loss_carryforward=self._parse_amount(
                self._profit_loss_carryforward_entry.text(),
                field_name="Neuer Gewinn-/Verlustvortrag",
                allow_negative=True,
            ),
        )

    def _save(self) -> None:
        """Übernimmt den Ergebnisverwendungsbeschluss."""

        if self._read_only:
            return

        try:
            data = self._build_result()
        except ValueError as exc:
            QMessageBox.critical(
                self,
                "Ergebnisverwendungsbeschluss",
                str(exc),
            )
            return

        self.result = data
        self.accept()

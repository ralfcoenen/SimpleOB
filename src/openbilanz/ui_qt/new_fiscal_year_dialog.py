"""PySide6-Dialog zum Anlegen eines neuen Geschäftsjahres."""

from datetime import datetime, timedelta

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)
from openbilanz.database.lock_error import DatabaseLockError
from openbilanz.database.company_repository import CompanyRepository
from openbilanz.domain.company import Company
from openbilanz.domain.fiscal_year import FiscalYear
from openbilanz.date_input import (
    normalize_german_date,
    parse_german_date,
)


class NewFiscalYearDialog(QDialog):
    """Legt ein neues Geschäftsjahr für ein Unternehmen an."""

    def __init__(
        self,
        parent,
        *,
        repository: CompanyRepository,
        company: Company,
    ) -> None:
        super().__init__(parent)

        self._repository = repository
        self._company = company

        self.result: FiscalYear | None = None
        self.requested_opening_source: FiscalYear | None = None

        self.setWindowTitle("SimpleOB – Neues Geschäftsjahr")
        self.setFixedSize(520, 280)

        self._create_ui()
        self._set_default_dates()

        self._start_date_entry.setFocus()

    def _create_ui(self) -> None:
        """Erzeugt die Benutzeroberfläche."""

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        title_label = QLabel("Neues Geschäftsjahr")
        title_label.setStyleSheet(
            "font-size: 18px; font-weight: bold;"
        )
        layout.addWidget(title_label)

        company_label = QLabel(self._company.name)
        layout.addWidget(company_label)

        form_layout = QFormLayout()

        self._start_date_entry = QLineEdit()
        self._start_date_entry.setMaximumWidth(160)
        self._start_date_entry.editingFinished.connect(
            lambda: self._normalize_date_entry(
                self._start_date_entry
            )
        )
        form_layout.addRow(
            "Beginn",
            self._start_date_entry,
        )

        self._end_date_entry = QLineEdit()
        self._end_date_entry.setMaximumWidth(160)
        self._end_date_entry.editingFinished.connect(
            lambda: self._normalize_date_entry(
                self._end_date_entry
            )
        )
        form_layout.addRow(
            "Ende",
            self._end_date_entry,
        )

        layout.addLayout(form_layout)

        date_hint = QLabel("Datumsformat: TT.MM.JJJJ")
        layout.addWidget(date_hint)

        layout.addStretch()

        button_box = QDialogButtonBox()

        create_button = QPushButton("Geschäftsjahr anlegen")
        create_button.clicked.connect(
            self._create_fiscal_year
        )
        button_box.addButton(
            create_button,
            QDialogButtonBox.ButtonRole.AcceptRole,
        )

        cancel_button = QPushButton("Abbrechen")
        cancel_button.clicked.connect(self.reject)
        button_box.addButton(
            cancel_button,
            QDialogButtonBox.ButtonRole.RejectRole,
        )

        layout.addWidget(button_box)

    def _set_default_dates(self) -> None:
        """Schlägt das nächste Kalenderjahr vor."""

        fiscal_years = self._repository.get_fiscal_years(
            self._company.company_id
        )

        if fiscal_years:
            next_year = fiscal_years[-1].end_date.year + 1
        else:
            next_year = datetime.now().year

        self._start_date_entry.setText(
            f"01.01.{next_year}"
        )
        self._end_date_entry.setText(
            f"31.12.{next_year}"
        )

    @staticmethod
    def _parse_date(
        value: str,
    ):
        """Liest eine deutsche Datumseingabe."""

        return parse_german_date(value)

    def _find_immediate_predecessor(
        self,
        fiscal_year: FiscalYear,
    ):
        """Liefert das unmittelbar vorhergehende Geschäftsjahr."""

        managed_fiscal_years = (
            self._repository.get_managed_fiscal_years(
                self._company.company_id
            )
        )

        expected_end_date = (
            fiscal_year.start_date - timedelta(days=1)
        )

        return next(
            (
                managed
                for managed in managed_fiscal_years
                if (
                    managed.fiscal_year.end_date
                    == expected_end_date
                )
            ),
            None,
        )

    def _confirm_opening_transfer(
        self,
        fiscal_year: FiscalYear,
    ) -> bool:
        """Fragt nach einer möglichen Saldenübernahme."""

        predecessor = self._find_immediate_predecessor(
            fiscal_year
        )

        if predecessor is None:
            self.requested_opening_source = None
            return True

        source_fiscal_year = predecessor.fiscal_year

        if not predecessor.is_closed:
            decision = QMessageBox.question(
                self,
                "Vorjahr noch nicht abgeschlossen",
                (
                    "Das unmittelbar vorhergehende "
                    "Geschäftsjahr "
                    f"{source_fiscal_year.display_name} "
                    "ist noch nicht abgeschlossen.\n\n"
                    "Eine Übernahme der Vorjahressalden "
                    "ist deshalb derzeit nicht möglich.\n\n"
                    "Soll das neue Geschäftsjahr trotzdem "
                    "ohne Saldenübernahme angelegt werden?"
                ),
                QMessageBox.StandardButton.Ok
                | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            )

            if decision != QMessageBox.StandardButton.Ok:
                return False

            self.requested_opening_source = None
            return True

        decision = QMessageBox.question(
            self,
            "Vorjahressalden übernehmen",
            (
                "Das abgeschlossene Geschäftsjahr "
                f"{source_fiscal_year.display_name} "
                "ist das unmittelbare Vorjahr.\n\n"
                "Sollen dessen Schlussbestände als "
                "Eröffnungswerte in das neue Geschäftsjahr "
                "übernommen werden?\n\n"
                "Ja = Vorjahressalden übernehmen\n"
                "Nein = ohne Saldenübernahme anlegen\n"
                "Abbrechen = Geschäftsjahr nicht anlegen"
            ),
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )

        if decision == QMessageBox.StandardButton.Cancel:
            return False

        if decision == QMessageBox.StandardButton.Yes:
            self.requested_opening_source = (
                source_fiscal_year
            )
        else:
            self.requested_opening_source = None

        return True

    def _create_fiscal_year(self) -> None:
        """Erzeugt und speichert das Geschäftsjahr."""

        try:
            start_date = self._parse_date(
                self._start_date_entry.text()
            )
            end_date = self._parse_date(
                self._end_date_entry.text()
            )

            self._start_date_entry.setText(
                start_date.strftime("%d.%m.%Y")
            )
            self._end_date_entry.setText(
                end_date.strftime("%d.%m.%Y")
            )

            fiscal_year = FiscalYear(
                start_date=start_date,
                end_date=end_date,
            )

            if not self._confirm_opening_transfer(
                fiscal_year
            ):
                return

            self._repository.add_fiscal_year(
                self._company.company_id,
                fiscal_year,
            )

        except (ValueError, DatabaseLockError) as exc:
            QMessageBox.critical(
                self,
                "Geschäftsjahr kann nicht angelegt werden",
                str(exc),
            )
            return

        self.result = fiscal_year
        self.accept()

    @staticmethod
    def _normalize_date_entry(
        entry: QLineEdit,
    ) -> None:
        """Normalisiert eine gültige Datumseingabe."""

        value = entry.text().strip()

        if not value:
            return

        try:
            normalized = normalize_german_date(value)
        except ValueError:
            return

        entry.setText(normalized)

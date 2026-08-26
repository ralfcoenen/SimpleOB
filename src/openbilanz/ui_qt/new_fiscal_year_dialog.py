"""Qt-Dialog zum Anlegen eines neuen Geschäftsjahres."""

from collections.abc import Callable
from datetime import datetime

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
)

from openbilanz.database.company_repository import CompanyRepository
from openbilanz.domain.company import Company
from openbilanz.domain.fiscal_year import FiscalYear
from openbilanz.ui.date_input import parse_german_date


class NewFiscalYearDialog(QDialog):
    """Legt ein neues Geschäftsjahr für ein Unternehmen an."""

    def __init__(
        self,
        *,
        repository: CompanyRepository,
        company: Company,
        create_fiscal_year: Callable[
            [Company, FiscalYear],
            None,
        ],
        parent=None,
    ) -> None:
        super().__init__(parent)

        self._repository = repository
        self._company = company
        self.result: FiscalYear | None = None
        self._create_fiscal_year_callback = (
            create_fiscal_year
        )

        self.setWindowTitle(
            "OpenBilanz – Neues Geschäftsjahr"
        )
        self.setMinimumWidth(480)

        layout = QVBoxLayout(self)

        title = QLabel("Neues Geschäftsjahr")
        font = title.font()
        font.setPointSize(18)
        font.setBold(True)
        title.setFont(font)
        layout.addWidget(title)

        layout.addWidget(
            QLabel(company.name)
        )

        form = QFormLayout()

        self._start_date = QLineEdit()
        self._end_date = QLineEdit()

        form.addRow(
            "Beginn",
            self._start_date,
        )
        form.addRow(
            "Ende",
            self._end_date,
        )

        layout.addLayout(form)

        layout.addWidget(
            QLabel("Datumsformat: TT.MM.JJJJ")
        )

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )

        buttons.button(
            QDialogButtonBox.StandardButton.Save
        ).setText(
            "Geschäftsjahr anlegen"
        )

        buttons.accepted.connect(
            self._create_fiscal_year
        )
        buttons.rejected.connect(
            self.reject
        )

        layout.addWidget(buttons)

        self._set_default_dates()
        self._start_date.setFocus()

    def _set_default_dates(self) -> None:
        """Schlägt das nächste Kalenderjahr vor."""

        fiscal_years = (
            self._repository.get_fiscal_years(
                self._company.company_id
            )
        )

        if fiscal_years:
            next_year = (
                fiscal_years[-1].end_date.year + 1
            )
        else:
            next_year = datetime.now().year

        self._start_date.setText(
            f"01.01.{next_year}"
        )
        self._end_date.setText(
            f"31.12.{next_year}"
        )

    def _create_fiscal_year(self) -> None:
        """Erzeugt und speichert das Geschäftsjahr."""

        try:
            start_date = parse_german_date(
                self._start_date.text()
            )
            end_date = parse_german_date(
                self._end_date.text()
            )

            self._start_date.setText(
                start_date.strftime("%d.%m.%Y")
            )
            self._end_date.setText(
                end_date.strftime("%d.%m.%Y")
            )

            fiscal_year = FiscalYear(
                start_date=start_date,
                end_date=end_date,
            )

            self._create_fiscal_year_callback(
                self._company,
                fiscal_year,
            )

        except ValueError as exc:
            QMessageBox.critical(
                self,
                "Geschäftsjahr kann nicht angelegt werden",
                str(exc),
            )
            return

        self.result = fiscal_year
        self.accept()

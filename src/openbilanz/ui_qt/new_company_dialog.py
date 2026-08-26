"""Qt-Dialog zum Anlegen einer neuen Buchhaltung."""

from uuid import uuid4

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
)

from openbilanz.core.context import ApplicationContext
from openbilanz.database.company_repository import CompanyRepository
from openbilanz.domain.company import Company
from openbilanz.domain.fiscal_year import FiscalYear
from openbilanz.ui.date_input import parse_german_date


class NewCompanyDialog(QDialog):
    """Erfasst ein neues Unternehmen mit erstem Geschäftsjahr."""

    def __init__(
        self,
        *,
        repository: CompanyRepository,
        parent=None,
    ) -> None:
        super().__init__(parent)

        self._repository = repository
        self.result: ApplicationContext | None = None

        self.setWindowTitle(
            "OpenBilanz – Neue Buchhaltung"
        )
        self.setMinimumWidth(520)

        layout = QVBoxLayout(self)

        title = QLabel("Neue Buchhaltung")
        font = title.font()
        font.setPointSize(18)
        font.setBold(True)
        title.setFont(font)
        layout.addWidget(title)

        form = QFormLayout()

        self._company_name = QLineEdit()
        self._start_date = QLineEdit("01.01.2026")
        self._end_date = QLineEdit("31.12.2026")

        form.addRow(
            "Unternehmensname",
            self._company_name,
        )
        form.addRow(
            "Beginn Geschäftsjahr",
            self._start_date,
        )
        form.addRow(
            "Ende Geschäftsjahr",
            self._end_date,
        )

        layout.addLayout(form)

        layout.addWidget(
            QLabel(
                "Datum: TT.MM.JJJJ · "
                "auch TTMMJJJJ oder TTMMJJ möglich"
            )
        )

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )

        buttons.button(
            QDialogButtonBox.StandardButton.Save
        ).setText(
            "Buchhaltung anlegen"
        )

        buttons.accepted.connect(
            self._create_company
        )
        buttons.rejected.connect(
            self.reject
        )

        layout.addWidget(buttons)

        self._company_name.setFocus()

    def _create_company(self) -> None:
        """Erzeugt Unternehmen und erstes Geschäftsjahr."""

        company_name = (
            self._company_name.text().strip()
        )

        if not company_name:
            QMessageBox.critical(
                self,
                "Ungültige Eingabe",
                "Bitte geben Sie einen Unternehmensnamen ein.",
            )
            return

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

            company = Company(
                company_id=uuid4(),
                name=company_name,
            )

            fiscal_year = FiscalYear(
                start_date=start_date,
                end_date=end_date,
            )

            self._repository.add(
                company
            )

            self._repository.add_fiscal_year(
                company.company_id,
                fiscal_year,
            )

        except ValueError as exc:
            QMessageBox.critical(
                self,
                "Buchhaltung kann nicht angelegt werden",
                str(exc),
            )
            return

        self.result = ApplicationContext(
            company=company,
            fiscal_year=fiscal_year,
        )

        self.accept()

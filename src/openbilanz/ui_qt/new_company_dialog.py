"""PySide6-Dialog zum Anlegen einer neuen Buchhaltung."""

from uuid import uuid4

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

from openbilanz.core.context import ApplicationContext
from openbilanz.database.company_repository import CompanyRepository
from openbilanz.domain.company import Company
from openbilanz.domain.fiscal_year import FiscalYear
from openbilanz.ui.date_input import (
    normalize_german_date,
    parse_german_date,
)


class NewCompanyDialog(QDialog):
    """Erfasst ein neues Unternehmen mit erstem Geschäftsjahr."""

    def __init__(
        self,
        parent,
        *,
        repository: CompanyRepository,
    ) -> None:
        super().__init__(parent)

        self._repository = repository
        self.result: ApplicationContext | None = None

        self.setWindowTitle("SimpleOB – Neue Buchhaltung")
        self.setFixedSize(560, 390)

        self._create_ui()

        self._company_name_entry.setFocus()

    def _create_ui(self) -> None:
        """Erzeugt die Benutzeroberfläche."""

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        title_label = QLabel("Neue Buchhaltung")
        title_label.setStyleSheet(
            "font-size: 18px; font-weight: bold;"
        )
        layout.addWidget(title_label)

        form_layout = QFormLayout()

        self._company_name_entry = QLineEdit()
        form_layout.addRow(
            "Unternehmensname",
            self._company_name_entry,
        )

        self._start_date_entry = QLineEdit("01.01.2026")
        self._start_date_entry.editingFinished.connect(
            lambda: self._normalize_date_entry(
                self._start_date_entry
            )
        )
        form_layout.addRow(
            "Beginn Geschäftsjahr",
            self._start_date_entry,
        )

        self._end_date_entry = QLineEdit("31.12.2026")
        self._end_date_entry.editingFinished.connect(
            lambda: self._normalize_date_entry(
                self._end_date_entry
            )
        )
        form_layout.addRow(
            "Ende Geschäftsjahr",
            self._end_date_entry,
        )

        layout.addLayout(form_layout)

        date_hint = QLabel(
            "Datum: TT.MM.JJJJ · "
            "auch TTMMJJJJ oder TTMMJJ möglich"
        )
        layout.addWidget(date_hint)

        layout.addStretch()

        button_box = QDialogButtonBox()

        create_button = QPushButton("Buchhaltung anlegen")
        create_button.clicked.connect(self._create_company)
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

    @staticmethod
    def _parse_date(
        value: str,
    ):
        """Liest eine deutsche Datumseingabe."""

        return parse_german_date(value)

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

    def _create_company(self) -> None:
        """Erzeugt und speichert die neue Buchhaltung."""

        company_name = self._company_name_entry.text().strip()

        if not company_name:
            QMessageBox.critical(
                self,
                "Ungültige Eingabe",
                "Bitte geben Sie einen Unternehmensnamen ein.",
            )
            return

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

            company = Company(
                company_id=uuid4(),
                name=company_name,
            )

            fiscal_year = FiscalYear(
                start_date=start_date,
                end_date=end_date,
            )

            self._repository.add(company)

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

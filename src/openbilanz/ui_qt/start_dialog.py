"""PySide6-Startdialog für SimpleOB."""

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from openbilanz.core.context import ApplicationContext
from openbilanz.database.company_repository import CompanyRepository
from openbilanz.domain.company import Company
from openbilanz.domain.fiscal_year import FiscalYear
from openbilanz.ui_qt.new_company_dialog import NewCompanyDialog


class StartDialog(QDialog):
    """Wählt Unternehmen und Geschäftsjahr für die Buchhaltung."""

    def __init__(
        self,
        *,
        repository: CompanyRepository,
    ) -> None:
        super().__init__()

        self._repository = repository

        self.result: ApplicationContext | None = None
        self.opening_transfer_request: (
            tuple[FiscalYear, FiscalYear] | None
        ) = None

        self._companies: tuple[Company, ...] = ()
        self._company_by_display_name: dict[str, Company] = {}
        self._fiscal_year_by_display_name: dict[
            str,
            FiscalYear,
        ] = {}

        self.setWindowTitle("SimpleOB – Buchhaltung öffnen")
        self.setFixedSize(800, 320)

        self._create_ui()
        self._load_companies()

    def _create_ui(self) -> None:
        """Erzeugt die Benutzeroberfläche."""

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        title_label = QLabel("SimpleOB")
        title_label.setStyleSheet(
            "font-size: 22px; font-weight: bold;"
        )
        layout.addWidget(title_label)

        subtitle_label = QLabel("Buchhaltung öffnen")
        subtitle_label.setStyleSheet(
            "font-size: 14px; font-weight: bold;"
        )
        layout.addWidget(subtitle_label)

        form_layout = QFormLayout()

        self._company_box = QComboBox()
        self._company_box.currentIndexChanged.connect(
            self._on_company_selected
        )
        form_layout.addRow(
            "Unternehmen",
            self._company_box,
        )

        self._fiscal_year_box = QComboBox()
        form_layout.addRow(
            "Geschäftsjahr",
            self._fiscal_year_box,
        )

        layout.addLayout(form_layout)

        self._status_label = QLabel()
        layout.addWidget(self._status_label)

        layout.addStretch()

        button_box = QDialogButtonBox()

        new_company_button = QPushButton(
            "Neue Buchhaltung anlegen"
        )
        new_company_button.clicked.connect(
            self._create_new_company
        )
        button_box.addButton(
            new_company_button,
            QDialogButtonBox.ButtonRole.ActionRole,
        )

        self._open_button = QPushButton("Öffnen")
        self._open_button.setEnabled(False)
        self._open_button.clicked.connect(self._open)
        button_box.addButton(
            self._open_button,
            QDialogButtonBox.ButtonRole.AcceptRole,
        )

        cancel_button = QPushButton("Abbrechen")
        cancel_button.clicked.connect(self.reject)
        button_box.addButton(
            cancel_button,
            QDialogButtonBox.ButtonRole.RejectRole,
        )

        layout.addWidget(button_box)

    def _load_companies(self) -> None:
        """Lädt die vorhandenen Unternehmen."""

        self._companies = self._repository.list_companies()

        self._company_by_display_name = {
            company.name: company
            for company in self._companies
        }

        self._company_box.blockSignals(True)
        self._company_box.clear()
        self._company_box.addItems(
            tuple(self._company_by_display_name)
        )
        self._company_box.blockSignals(False)

        if not self._companies:
            self._status_label.setText(
                "Es ist noch keine Buchhaltung vorhanden."
            )
            self._fiscal_year_box.clear()
            self._open_button.setEnabled(False)
            return

        self._load_fiscal_years(self._companies[0])

    def _on_company_selected(
        self,
        _index: int,
    ) -> None:
        """Lädt die Geschäftsjahre des ausgewählten Unternehmens."""

        company = self._selected_company()

        if company is None:
            return

        self._load_fiscal_years(company)

    def _load_fiscal_years(
        self,
        company: Company,
    ) -> None:
        """Lädt die Geschäftsjahre eines Unternehmens."""

        fiscal_years = self._repository.get_fiscal_years(
            company.company_id
        )

        self._fiscal_year_by_display_name = {
            fiscal_year.display_name: fiscal_year
            for fiscal_year in fiscal_years
        }

        self._fiscal_year_box.clear()
        self._fiscal_year_box.addItems(
            tuple(self._fiscal_year_by_display_name)
        )

        if not fiscal_years:
            self._status_label.setText(
                "Für dieses Unternehmen ist "
                "noch kein Geschäftsjahr vorhanden."
            )
            self._open_button.setEnabled(False)
            return

        self._status_label.clear()
        self._open_button.setEnabled(True)

    def _selected_company(
        self,
    ) -> Company | None:
        """Liefert das ausgewählte Unternehmen."""

        return self._company_by_display_name.get(
            self._company_box.currentText()
        )

    def _selected_fiscal_year(
        self,
    ) -> FiscalYear | None:
        """Liefert das ausgewählte Geschäftsjahr."""

        return self._fiscal_year_by_display_name.get(
            self._fiscal_year_box.currentText()
        )

    def _open(self) -> None:
        """Erzeugt den Anwendungskontext."""

        company = self._selected_company()
        fiscal_year = self._selected_fiscal_year()

        if company is None or fiscal_year is None:
            return

        self.result = ApplicationContext(
            company=company,
            fiscal_year=fiscal_year,
        )

        self.accept()

    def _create_new_company(self) -> None:
        """Öffnet den Dialog zum Anlegen einer Buchhaltung."""

        dialog = NewCompanyDialog(
            self,
            repository=self._repository,
        )

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        if dialog.result is None:
            return

        self.result = dialog.result
        self.accept()

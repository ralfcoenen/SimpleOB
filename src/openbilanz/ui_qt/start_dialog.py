"""Startdialog der experimentellen PySide6-Oberfläche."""

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


class StartDialog(QDialog):
    """Wählt Unternehmen und Geschäftsjahr."""

    def __init__(
        self,
        *,
        repository: CompanyRepository,
    ) -> None:
        super().__init__()

        self._repository = repository
        self.result: ApplicationContext | None = None

        self._companies: tuple[Company, ...] = ()
        self._fiscal_years: tuple[FiscalYear, ...] = ()

        self.setWindowTitle("OpenBilanz – Buchhaltung öffnen")
        self.setMinimumWidth(520)

        self._create_ui()
        self._load_companies()

    def _create_ui(self) -> None:
        layout = QVBoxLayout(self)

        title = QLabel("OpenBilanz")
        font = title.font()
        font.setPointSize(22)
        font.setBold(True)
        title.setFont(font)
        layout.addWidget(title)

        subtitle = QLabel("Buchhaltung öffnen")
        font = subtitle.font()
        font.setPointSize(14)
        font.setBold(True)
        subtitle.setFont(font)
        layout.addWidget(subtitle)

        form = QFormLayout()

        self._company_box = QComboBox()
        self._company_box.currentIndexChanged.connect(
            self._on_company_selected
        )
        form.addRow(
            "Unternehmen",
            self._company_box,
        )

        self._fiscal_year_box = QComboBox()
        form.addRow(
            "Geschäftsjahr",
            self._fiscal_year_box,
        )

        layout.addLayout(form)

        self._status_label = QLabel()
        layout.addWidget(self._status_label)

        buttons = QDialogButtonBox()

        self._open_button = QPushButton("Öffnen")
        self._open_button.clicked.connect(self._open)
        buttons.addButton(
            self._open_button,
            QDialogButtonBox.ButtonRole.AcceptRole,
        )

        cancel_button = QPushButton("Beenden")
        cancel_button.clicked.connect(self.reject)
        buttons.addButton(
            cancel_button,
            QDialogButtonBox.ButtonRole.RejectRole,
        )

        layout.addWidget(buttons)

    def _load_companies(self) -> None:
        self._companies = self._repository.list_companies()

        self._company_box.blockSignals(True)
        self._company_box.clear()

        for company in self._companies:
            self._company_box.addItem(company.name)

        self._company_box.blockSignals(False)

        if not self._companies:
            self._status_label.setText(
                "Es ist noch keine Buchhaltung vorhanden."
            )
            self._open_button.setEnabled(False)
            return

        self._company_box.setCurrentIndex(0)
        self._load_fiscal_years(
            self._companies[0]
        )

    def _on_company_selected(
        self,
        index: int,
    ) -> None:
        if index < 0 or index >= len(self._companies):
            return

        self._load_fiscal_years(
            self._companies[index]
        )

    def _load_fiscal_years(
        self,
        company: Company,
    ) -> None:
        self._fiscal_years = (
            self._repository.get_fiscal_years(
                company.company_id
            )
        )

        self._fiscal_year_box.clear()

        for fiscal_year in self._fiscal_years:
            self._fiscal_year_box.addItem(
                fiscal_year.display_name
            )

        if not self._fiscal_years:
            self._status_label.setText(
                "Für dieses Unternehmen ist "
                "noch kein Geschäftsjahr vorhanden."
            )
            self._open_button.setEnabled(False)
            return

        self._fiscal_year_box.setCurrentIndex(0)
        self._status_label.clear()
        self._open_button.setEnabled(True)

    def _open(self) -> None:
        company_index = self._company_box.currentIndex()
        fiscal_year_index = (
            self._fiscal_year_box.currentIndex()
        )

        if (
            company_index < 0
            or fiscal_year_index < 0
        ):
            return

        self.result = ApplicationContext(
            company=self._companies[company_index],
            fiscal_year=self._fiscal_years[
                fiscal_year_index
            ],
        )

        self.accept()

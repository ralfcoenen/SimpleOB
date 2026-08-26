"""Startdialog der experimentellen PySide6-Oberfläche."""
from collections.abc import Callable

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
from openbilanz.ui_qt.new_company_dialog import (
    NewCompanyDialog,
)
from openbilanz.ui_qt.new_fiscal_year_dialog import (
    NewFiscalYearDialog,
)


class StartDialog(QDialog):
    """Wählt Unternehmen und Geschäftsjahr."""

    def __init__(
        self,
        *,
        repository: CompanyRepository,
        create_fiscal_year: Callable[
            [Company, FiscalYear],
            None,
        ],
    ) -> None:
        super().__init__()

        self._repository = repository
        self.result: ApplicationContext | None = None

        self._companies: tuple[Company, ...] = ()

        self._fiscal_years: tuple[FiscalYear, ...] = ()

        self._create_fiscal_year_callback = (
            create_fiscal_year
        )

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

        self._new_company_button = QPushButton(
            "Neue Buchhaltung anlegen"
        )
        self._new_company_button.clicked.connect(
            self._create_new_company
        )
        buttons.addButton(
            self._new_company_button,
            QDialogButtonBox.ButtonRole.ActionRole,
        )

        self._new_fiscal_year_button = QPushButton(
            "Neues Geschäftsjahr"
        )
        self._new_fiscal_year_button.clicked.connect(
            self._create_new_fiscal_year
        )
        buttons.addButton(
            self._new_fiscal_year_button,
            QDialogButtonBox.ButtonRole.ActionRole,
        )

        self._new_fiscal_year_button.setEnabled(
            False
        )
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

        self._new_fiscal_year_button.setEnabled(
            bool(self._companies)
        )

        if not self._companies:
            self._fiscal_years = ()
            self._fiscal_year_box.clear()

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

    def _create_new_company(self) -> None:
        """Öffnet den Dialog zum Anlegen einer Buchhaltung."""

        dialog = NewCompanyDialog(
            repository=self._repository,
            parent=self,
        )

        if (
            dialog.exec()
            != QDialog.DialogCode.Accepted
        ):
            return

        if dialog.result is None:
            return

        self.result = dialog.result
        self.accept()

    def _create_new_fiscal_year(self) -> None:
        """Legt für das ausgewählte Unternehmen ein Geschäftsjahr an."""

        company_index = (
            self._company_box.currentIndex()
        )

        if (
            company_index < 0
            or company_index >= len(self._companies)
        ):
            return

        company = self._companies[
            company_index
        ]

        dialog = NewFiscalYearDialog(
            repository=self._repository,
            company=company,
            create_fiscal_year=(
                self._create_fiscal_year_callback
            ),
            parent=self,
        )

        if (
            dialog.exec()
            != QDialog.DialogCode.Accepted
        ):
            return

        if dialog.result is None:
            return

        self._load_fiscal_years(
            company
        )

        for index, fiscal_year in enumerate(
            self._fiscal_years
        ):
            if fiscal_year == dialog.result:
                self._fiscal_year_box.setCurrentIndex(
                    index
                )
                break

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

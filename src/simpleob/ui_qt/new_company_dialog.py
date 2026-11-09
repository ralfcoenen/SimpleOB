"""PySide6-Dialog zum Anlegen einer neuen Buchhaltung."""

from collections.abc import Callable
from datetime import date
from pathlib import Path
from uuid import uuid4

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from simpleob.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
from simpleob.accounting.hgb_financial_statement_position_provider import (
    HgbFinancialStatementPositionProvider,
)
from simpleob.core.config import desktop_application_data_dir
from simpleob.core.context import ApplicationContext
from simpleob.database.company_repository import CompanyRepository
from simpleob.date_input import GermanDateEdit
from simpleob.domain.account import Account
from simpleob.domain.company import Company
from simpleob.domain.fiscal_year import FiscalYear
from simpleob.hgb.balance_sheet_structure import create_hgb_balance_sheet_structure
from simpleob.hgb.income_statement_structure import (
    create_hgb_income_statement_structure,
)
from simpleob.importers.chart_of_accounts_template_bundle_importer import (
    ChartOfAccountsTemplateBundle,
    ChartOfAccountsTemplateBundleImporter,
)
from simpleob.importers.csv_chart_of_accounts_importer import (
    CsvChartOfAccountsImporter,
)
from simpleob.importers.errors import ChartOfAccountsImportError
from simpleob.ui_qt.account_configuration_dialog import AccountConfigurationDialog
from simpleob.ui_qt.chart_of_accounts_template_editor_dialog import (
    ChartOfAccountsTemplateEditorDialog,
)


class NewCompanyDialog(QDialog):
    """Erfasst ein neues Unternehmen mit erstem Geschäftsjahr."""

    def __init__(
        self,
        parent,
        *,
        repository: CompanyRepository,
        template_directory: Path | None = None,
        taxonomy_choices_provider: (
            Callable[
                [FiscalYear, FinancialStatementPosition],
                tuple[tuple[str, str], ...],
            ]
            | None
        ) = None,
    ) -> None:
        super().__init__(parent)

        self._repository = repository
        self._taxonomy_choices_provider = taxonomy_choices_provider
        self.result: ApplicationContext | None = None
        self.chart_bundle: ChartOfAccountsTemplateBundle | None = None
        self.uses_standard_chart = False
        self._edited_chart_bundle: ChartOfAccountsTemplateBundle | None = None
        self._edited_chart_source_path: Path | None = None
        self._bundle_was_edited = False
        self._chart_importer = ChartOfAccountsTemplateBundleImporter(
            chart_importer=CsvChartOfAccountsImporter(
                position_provider=self._create_position_provider()
            )
        )
        self._chart_directory = (
            Path(__file__).resolve().parent.parent
            / "resources"
            / "chart_of_accounts"
        )
        self._template_directory = (
            template_directory
            if template_directory is not None
            else desktop_application_data_dir() / "chart_of_accounts_templates"
        )
        self._custom_chart_path: Path | None = None

        self.setWindowTitle("SimpleOB – Neue Buchhaltung")
        self.setFixedSize(700, 560)

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

        chart_row = QHBoxLayout()
        self._chart_box = QComboBox()
        self._chart_paths = tuple(
            sorted(
                (
                    *self._chart_directory.glob("*.csv"),
                    *(
                        path
                        for path in self._template_directory.glob("*/*.csv")
                        if path.name == f"{path.parent.name}.csv"
                    ),
                ),
                key=lambda path: str(path).casefold(),
            )
        )
        for chart_path in self._chart_paths:
            self._chart_box.addItem(
                self._chart_label(chart_path),
                str(chart_path),
            )
        standard_index = self._chart_box.findText("SimpleOB-Standard")
        if standard_index >= 0:
            self._chart_box.setCurrentIndex(standard_index)
        self._chart_box.currentIndexChanged.connect(
            self._on_chart_selection_changed
        )
        chart_row.addWidget(self._chart_box, 1)
        custom_chart_button = QPushButton("Eigene CSV wählen …")
        custom_chart_button.clicked.connect(self._select_custom_chart)
        chart_row.addWidget(custom_chart_button)
        form_layout.addRow("Kontenrahmen", chart_row)
        self._edit_chart_button = QPushButton("Kontenrahmen bearbeiten …")
        self._edit_chart_button.clicked.connect(self._edit_chart_template)
        form_layout.addRow("", self._edit_chart_button)
        self._custom_chart_label = QLabel()
        self._custom_chart_label.setWordWrap(True)
        form_layout.addRow("Eigene Datei", self._custom_chart_label)
        self._save_template_configuration_box = QCheckBox(
            "Zuordnungen neben der CSV als wiederverwendbare Vorlage speichern"
        )
        self._save_template_configuration_box.setEnabled(False)
        form_layout.addRow("Vorlage", self._save_template_configuration_box)

        self._start_date_entry = GermanDateEdit(value=date(2026, 1, 1))
        form_layout.addRow(
            "Beginn Geschäftsjahr",
            self._start_date_entry,
        )

        self._end_date_entry = GermanDateEdit(value=date(2026, 12, 31))
        form_layout.addRow(
            "Ende Geschäftsjahr",
            self._end_date_entry,
        )

        layout.addLayout(form_layout)

        date_hint = QLabel(
            "Datum: TT.MM.JJJJ · "
            "Kurzformate wie 1.2.2026 werden übernommen und normalisiert."
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

    def _create_company(self) -> None:
        """Prüft die Eingaben und bereitet die Neuanlage vor."""

        company_name = self._company_name_entry.text().strip()

        if not company_name:
            QMessageBox.critical(
                self,
                "Ungültige Eingabe",
                "Bitte geben Sie einen Unternehmensnamen ein.",
            )
            return

        try:
            start_date = self._start_date_entry.date_value()
            end_date = self._end_date_entry.date_value()

            company = Company(
                company_id=uuid4(),
                name=company_name,
            )

            fiscal_year = FiscalYear(
                start_date=start_date,
                end_date=end_date,
            )
        except ValueError as exc:
            QMessageBox.critical(
                self,
                "Buchhaltung kann nicht angelegt werden",
                str(exc),
            )
            return

        chart_path = self._selected_chart_path()
        if chart_path is None:
            QMessageBox.critical(
                self,
                "Kontenrahmen fehlt",
                "Bitte wählen Sie einen Kontenrahmen aus.",
            )
            return

        try:
            if (
                self._edited_chart_bundle is not None
                and self._edited_chart_source_path == chart_path
            ):
                bundle = self._edited_chart_bundle
            else:
                bundle = self._chart_importer.load(chart_path)
        except (
            ChartOfAccountsImportError,
            OSError,
            ValueError,
            KeyError,
            TypeError,
        ) as exc:
            QMessageBox.critical(
                self,
                "Kontenrahmen ungültig",
                str(exc),
            )
            return

        uses_standard_chart = (
            self._is_standard_chart(chart_path)
            and not self._bundle_was_edited
        )
        if not uses_standard_chart and not self._confirm_individual_chart_setup():
            return

        if (
            not uses_standard_chart
            or bundle.control_accounts is None
            or bundle.vat_accounts is None
        ):
            account_objects = tuple(
                Account(template=template)
                for template in bundle.chart.accounts
            )
            setup_dialog = AccountConfigurationDialog(
                self,
                accounts=account_objects,
                control_accounts=bundle.control_accounts,
                vat_accounts=bundle.vat_accounts,
                account_roles=bundle.account_roles,
                for_new_company=True,
            )
            if setup_dialog.exec() != QDialog.DialogCode.Accepted:
                return
            if setup_dialog.result is None:
                return
            control_accounts, vat_accounts, account_roles = setup_dialog.result
            bundle = ChartOfAccountsTemplateBundle(
                chart=bundle.chart,
                control_accounts=control_accounts,
                vat_accounts=vat_accounts,
                account_roles=account_roles,
                taxonomy_version=bundle.taxonomy_version,
                taxonomy_mappings=bundle.taxonomy_mappings,
            )

        try:
            self._chart_importer.validate(bundle)
        except (ValueError, TypeError) as exc:
            QMessageBox.critical(
                self,
                "Kontenrahmen ungültig",
                str(exc),
            )
            return

        if self._save_template_configuration_box.isChecked():
            config_path = chart_path.with_name(
                f"{chart_path.stem}{self._chart_importer.CONFIG_SUFFIX}"
            )
            try:
                self._chart_importer.save_configuration(bundle, config_path)
            except (FileExistsError, OSError, ValueError, TypeError) as exc:
                QMessageBox.critical(
                    self,
                    "Vorlagenkonfiguration konnte nicht gespeichert werden",
                    str(exc),
                )
                return

        self.chart_bundle = bundle
        self.uses_standard_chart = uses_standard_chart

        self.result = ApplicationContext(
            company=company,
            fiscal_year=fiscal_year,
        )

        self.accept()

    def _is_standard_chart(self, chart_path: Path) -> bool:
        standard_path = (
            self._chart_directory / "openbilanz_standard.csv"
        )
        return chart_path.resolve() == standard_path.resolve()

    def _edit_chart_template(self) -> None:
        chart_path = self._selected_chart_path()
        if chart_path is None:
            QMessageBox.information(
                self,
                "Kontenrahmen bearbeiten",
                "Bitte wählen Sie zuerst einen Kontenrahmen aus.",
            )
            return
        try:
            if (
                self._edited_chart_bundle is not None
                and self._edited_chart_source_path == chart_path
            ):
                bundle = self._edited_chart_bundle
            else:
                bundle = self._chart_importer.load(chart_path)
        except (
            ChartOfAccountsImportError,
            OSError,
            ValueError,
            KeyError,
            TypeError,
        ) as exc:
            QMessageBox.critical(
                self,
                "Kontenrahmen ungültig",
                str(exc),
            )
            return

        assets, liabilities, income_statement = self._create_statement_roots()
        taxonomy_choices_provider = None
        if self._taxonomy_choices_provider is not None:
            def choices_for_position(position: FinancialStatementPosition):
                fiscal_year = FiscalYear(
                    start_date=self._start_date_entry.date_value(),
                    end_date=self._end_date_entry.date_value(),
                )
                return self._taxonomy_choices_provider(
                    fiscal_year,
                    position,
                )

            taxonomy_choices_provider = choices_for_position
        dialog = ChartOfAccountsTemplateEditorDialog(
            self,
            bundle=bundle,
            bundle_importer=self._chart_importer,
            templates_directory=self._template_directory,
            prepare_bundle_for_save=self._prepare_bundle_for_template_save,
            taxonomy_choices_provider=taxonomy_choices_provider,
            assets=assets,
            liabilities=liabilities,
            income_statement=income_statement,
        )
        dialog.exec()
        if dialog.result is None:
            return

        self._edited_chart_bundle = dialog.result
        self._edited_chart_source_path = chart_path
        self._bundle_was_edited = True
        self._save_template_configuration_box.setChecked(False)
        self._save_template_configuration_box.setEnabled(False)

    def _prepare_bundle_for_template_save(
        self,
        bundle: ChartOfAccountsTemplateBundle,
    ) -> ChartOfAccountsTemplateBundle | None:
        """Ergänzt fehlende Zuordnungen vor dem Speichern einer eigenen Vorlage."""

        account_objects = tuple(
            Account(template=template)
            for template in bundle.chart.accounts
        )
        setup_dialog = AccountConfigurationDialog(
            self,
            accounts=account_objects,
            control_accounts=bundle.control_accounts,
            vat_accounts=bundle.vat_accounts,
            account_roles=bundle.account_roles,
            for_new_company=True,
        )
        if setup_dialog.exec() != QDialog.DialogCode.Accepted:
            return None
        if setup_dialog.result is None:
            return None
        control_accounts, vat_accounts, account_roles = setup_dialog.result
        return ChartOfAccountsTemplateBundle(
            chart=bundle.chart,
            control_accounts=control_accounts,
            vat_accounts=vat_accounts,
            account_roles=account_roles,
            taxonomy_version=bundle.taxonomy_version,
            taxonomy_mappings=bundle.taxonomy_mappings,
        )

    def _confirm_individual_chart_setup(self) -> bool:
        message = (
            "Bei einem individuellen Kontenrahmen müssen die technischen "
            "Systemkonten fachlich richtig zugeordnet werden. Prüfen Sie "
            "auch die Umsatzsteuer- und Vorsteuerkonten sowie die Kontenrollen "
            "und ergänzen Sie diese bei Bedarf. Kontrollieren Sie außerdem "
            "die HGB-Zuordnungen. E-Bilanz-Taxonomiezuweisungen müssen bei "
            "Bedarf individuell eingerichtet werden. Fehlende oder fehlerhafte "
            "Zuordnungen können einzelne Buchungs-, Abschluss- oder "
            "E-Bilanz-Funktionen verhindern."
        )
        answer = QMessageBox.warning(
            self,
            "Individuellen Kontenrahmen prüfen",
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return answer == QMessageBox.StandardButton.Yes

    @staticmethod
    def _create_position_provider() -> HgbFinancialStatementPositionProvider:
        roots = NewCompanyDialog._create_statement_roots()
        return HgbFinancialStatementPositionProvider(
            roots
        )

    @staticmethod
    def _create_statement_roots() -> tuple[
        FinancialStatementPosition,
        FinancialStatementPosition,
        FinancialStatementPosition,
    ]:
        assets, liabilities = create_hgb_balance_sheet_structure()
        income_statement = create_hgb_income_statement_structure()
        return assets, liabilities, income_statement

    def _chart_label(self, path: Path) -> str:
        if path.stem == "openbilanz_standard" and path.parent == self._chart_directory:
            return "SimpleOB-Standard"
        try:
            path.relative_to(self._template_directory)
        except ValueError:
            return path.stem
        return f"{path.stem} (eigene Vorlage)"

    def _selected_chart_path(self) -> Path | None:
        if self._custom_chart_path is not None:
            return self._custom_chart_path
        value = self._chart_box.currentData()
        return Path(value) if isinstance(value, str) else None

    def _on_chart_selection_changed(self, _index: int) -> None:
        self._custom_chart_path = None
        self._custom_chart_label.clear()
        self._save_template_configuration_box.setChecked(False)
        self._save_template_configuration_box.setEnabled(False)
        self._edited_chart_bundle = None
        self._edited_chart_source_path = None
        self._bundle_was_edited = False
        self._edit_chart_button.setEnabled(
            isinstance(self._chart_box.currentData(), str)
        )

    def _select_custom_chart(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Kontenrahmen-CSV auswählen",
            "",
            "Kontenrahmen-CSV (*.csv)",
        )
        if not filename:
            return
        self._chart_box.setCurrentIndex(-1)
        self._custom_chart_path = Path(filename)
        self._custom_chart_label.setText(str(self._custom_chart_path))
        self._edited_chart_bundle = None
        self._edited_chart_source_path = None
        self._bundle_was_edited = False
        self._edit_chart_button.setEnabled(True)
        config_path = self._custom_chart_path.with_name(
            f"{self._custom_chart_path.stem}{self._chart_importer.CONFIG_SUFFIX}"
        )
        self._save_template_configuration_box.setChecked(False)
        self._save_template_configuration_box.setEnabled(
            not config_path.exists()
        )

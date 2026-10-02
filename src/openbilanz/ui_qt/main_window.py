"""PySide6-Hauptfenster von SimpleOB."""

from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from openbilanz.accounting.balance_sheet import BalanceSheet
from openbilanz.accounting.financial_statement_builder import (
    FinancialStatementBuilder,
)
from openbilanz.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
from openbilanz.accounting.income_statement import IncomeStatement
from openbilanz.core.context import ApplicationContext
from openbilanz.date_input import parse_german_date
from openbilanz.domain.account import Account
from openbilanz.domain.account_type import AccountType
from openbilanz.domain.booking_type import BookingType
from openbilanz.domain.chart_of_accounts_template import (
    ChartOfAccountsTemplate,
)
from openbilanz.domain.entry_side import EntrySide
from openbilanz.domain.fiscal_year_status import FiscalYearStatus
from openbilanz.domain.vat_accounts import VatAccounts
from openbilanz.eric.elster_bilanz_transmission_service import (
    ElsterBilanzTransmissionService,
)
from openbilanz.eric.eric_validate_adapter import EricValidateError
from openbilanz.services.closing_accounts import ClosingAccounts
from openbilanz.services.closing_service import (
    ClosingResult,
    ClosingService,
)
from openbilanz.services.fiscal_year_workspace import FiscalYearWorkspace
from openbilanz.services.opening_balance_service import OpeningBalanceService
from openbilanz.services.pdf_reporting_service import PdfReportingService
from openbilanz.ui_qt.account_configuration_dialog import (
    AccountConfigurationDialog,
)
from openbilanz.ui_qt.account_editor_dialog import AccountEditorDialog
from openbilanz.ui_qt.balance_sheet_frame import BalanceSheetFrame
from openbilanz.ui_qt.booking_frame import BookingFrame
from openbilanz.ui_qt.closing_frame import ClosingFrame
from openbilanz.ui_qt.company_master_data_dialog import (
    CompanyMasterDataDialog,
)
from openbilanz.ui_qt.e_bilanz_account_mapping_dialog import (
    EBilanzAccountMappingDialog,
)
from openbilanz.ui_qt.e_bilanz_frame import EBilanzFrame
from openbilanz.ui_qt.fixed_asset_acquisition_link_dialog import (
    AcquisitionBookingCandidate,
    FixedAssetAcquisitionLinkDialog,
)
from openbilanz.ui_qt.fixed_asset_disposal_dialog import (
    FixedAssetDisposalDialog,
)
from openbilanz.ui_qt.fixed_asset_disposal_link_dialog import (
    DisposalBookingCandidate,
    FixedAssetDisposalLinkDialog,
)
from openbilanz.ui_qt.income_statement_frame import (
    IncomeStatementFrame,
)
from openbilanz.ui_qt.new_fixed_asset_dialog import NewFixedAssetDialog
from openbilanz.ui_qt.opening_balance_dialog import OpeningBalanceDialog
from openbilanz.ui_qt.profit_appropriation_dialog import (
    ProfitAppropriationDialog,
)
from openbilanz.ui_qt.reports_widget import ReportsWidget
from openbilanz.ui_qt.shareholder_dialog import ShareholdersDialog
from openbilanz.ui_qt.tax_depreciation_adjustment_dialog import (
    TaxDepreciationAdjustmentDialog,
)
from openbilanz.ui_qt.vat_booking_frame import VatBookingFrame

ZERO = Decimal("0.00")


class MainWindow(QMainWindow):
    """Hauptfenster der PySide6-Oberfläche."""

    def __init__(
        self,
        *,
        context: ApplicationContext,
        workspace: FiscalYearWorkspace,
        accounts: tuple[Account, ...],
        assets: FinancialStatementPosition,
        liabilities: FinancialStatementPosition,
        income_statement: FinancialStatementPosition,
        statement_builder: FinancialStatementBuilder,
        account_types: dict[str, AccountType],
        chart_of_accounts: ChartOfAccountsTemplate,
        opening_balance_account_number: str,
        depreciation_expense_account_number: str,
        closing_accounts: ClosingAccounts,
        closing_service: ClosingService,
        account_mapper,
        vat_accounts: VatAccounts,
        pdf_reporting_service: PdfReportingService,
        elster_bilanz_transmission_service: (
            ElsterBilanzTransmissionService | None
        ) = None,
    ) -> None:
        super().__init__()

        self._context = context
        self._workspace = workspace
        self._accounts = accounts
        self._assets = assets
        self._liabilities = liabilities
        self._income_statement = income_statement
        self._financial_statement_builder = statement_builder
        self._account_types = account_types
        self._chart_of_accounts = chart_of_accounts
        self._account_mapper = account_mapper
        self._opening_balance_account_number = (
            opening_balance_account_number
        )
        self._opening_balance_service = OpeningBalanceService(
            opening_balance_account_number=(
                self._opening_balance_account_number
            ),
        )
        self._depreciation_expense_account_number = (
            depreciation_expense_account_number
        )
        self._closing_accounts = closing_accounts
        self._closing_service = closing_service
        self._vat_accounts = vat_accounts
        self._pdf_reporting_service = pdf_reporting_service
        self._elster_bilanz_transmission_service = (
            elster_bilanz_transmission_service
        )
        self._current_income_statement: IncomeStatement | None = None
        self._current_closing_result: ClosingResult | None = None
        self._current_balance_sheet: BalanceSheet | None = None
        self._current_closing_balances = ()

        self._current_e_bilanz_preparation = None
        self._current_e_bilanz_document = None
        self._current_e_bilanz_arelle_valid = False

        self._return_to_start_requested = False
        self._company_master_data = (
            self._workspace.load_company_master_data()
        )
        self.setWindowTitle(
            f"SimpleOB – {self._context.company.name}"
        )
        self.resize(1300, 800)
        self.setMinimumSize(1100, 700)

        central_widget = QWidget(self)
        layout = QVBoxLayout(central_widget)

        title_label = QLabel("SimpleOB")
        title_label.setStyleSheet(
            "font-size: 24px; font-weight: bold;"
        )
        layout.addWidget(title_label)

        subtitle_label = QLabel(
            "Buchhaltung und Jahresabschluss"
        )
        layout.addWidget(subtitle_label)

        company_label = QLabel(
            f"Unternehmen: {self._context.company.name}"
        )
        company_label.setStyleSheet(
            "font-weight: bold;"
        )
        layout.addWidget(company_label)

        fiscal_year_label = QLabel(
            "Geschäftsjahr: "
            f"{self._context.fiscal_year.display_name}"
        )
        layout.addWidget(fiscal_year_label)

        administration_layout = QHBoxLayout()

        self._company_master_data_button = QPushButton(
            "Unternehmensstammdaten"
        )
        self._company_master_data_button.clicked.connect(
            self._open_company_master_data
        )
        administration_layout.addWidget(
            self._company_master_data_button
        )

        self._shareholders_button = QPushButton(
            "Gesellschafter"
        )
        self._shareholders_button.clicked.connect(
            self._open_shareholders
        )
        administration_layout.addWidget(
            self._shareholders_button
        )

        self._account_configuration_button = QPushButton(
            "Kontenkonfiguration"
        )
        self._account_configuration_button.clicked.connect(
            self._open_account_configuration
        )
        administration_layout.addWidget(
            self._account_configuration_button
        )
        self._return_to_start_button = QPushButton(
            "Buchhaltung wechseln"
        )
        self._return_to_start_button.clicked.connect(
            self._return_to_start
        )
        administration_layout.addWidget(
            self._return_to_start_button
        )
        self._opening_balance_button = QPushButton(
            "Eröffnungsbilanz erfassen"
        )
        self._opening_balance_button.clicked.connect(
            self._open_opening_balance
        )
        administration_layout.addWidget(
            self._opening_balance_button
        )

        administration_layout.addStretch()
        layout.addLayout(administration_layout)

        self._notebook = QTabWidget()
        layout.addWidget(self._notebook)

        self._accounts_tab = QWidget()
        self._journal_tab = QWidget()
        self._booking_tab = QWidget()
        self._fixed_assets_tab = QWidget()
        self._balance_sheet_tab = QWidget()
        self._income_statement_tab = QWidget()
        self._reports_tab = QWidget()
        self._closing_tab = QWidget()
        self._e_bilanz_tab = QWidget()

        self._notebook.addTab(
            self._accounts_tab,
            "Konten",
        )
        self._notebook.addTab(
            self._journal_tab,
            "Journal",
        )
        self._notebook.addTab(
            self._booking_tab,
            "Buchen",
        )
        self._notebook.addTab(
            self._fixed_assets_tab,
            "Anlagen",
        )
        self._notebook.addTab(
            self._balance_sheet_tab,
            "Bilanz",
        )
        self._notebook.addTab(
            self._income_statement_tab,
            "GuV",
        )
        self._notebook.addTab(
            self._reports_tab,
            "Auswertungen",
        )
        self._notebook.addTab(
            self._closing_tab,
            "Jahresabschluss",
        )
        self._notebook.addTab(
            self._e_bilanz_tab,
            "E-Bilanz",
        )

        self._create_accounts_tab()
        self._create_journal_tab()
        self._create_booking_tab()
        self._create_fixed_assets_tab()
        self._create_balance_sheet_tab()
        self._create_income_statement_tab()
        self._create_reports_tab()
        self._create_closing_tab()
        self._create_e_bilanz_tab()

        self.setCentralWidget(central_widget)

        self._refresh_balance_sheet()
        self._refresh_closing()
        self._refresh_e_bilanz_availability()

        if self._company_master_data.supports_e_bilanz:
            self._refresh_taxonomy_status()
            self._refresh_bvv_evaluation()
            self._refresh_e_bilanz()

    def closeEvent(self, event) -> None:
        """Kehrt beim Schließen des Hauptfensters zur Buchhaltungsauswahl zurück."""

        self._return_to_start_requested = True
        event.accept()

        app = QApplication.instance()
        if app is not None:
            app.quit()

    @property
    def return_to_start_requested(self) -> bool:
        """Zeigt an, ob zur Buchhaltungsauswahl zurückgekehrt werden soll."""

        return self._return_to_start_requested

    def _create_e_bilanz_tab(self) -> None:
        """Erzeugt den Arbeitsbereich E-Bilanz."""

        layout = QVBoxLayout(self._e_bilanz_tab)

        self._e_bilanz_frame = EBilanzFrame(
            on_install_taxonomy=self._install_required_taxonomy,
            on_prepare=self._prepare_e_bilanz,
            on_build=self._build_e_bilanz,
            on_validate=self._validate_e_bilanz,
            on_export_bvv_pdf=self._export_bvv_pdf,
            on_export_xbrl=self._export_e_bilanz,
            on_export_pdf=self._export_e_bilanz_pdf,
            on_send_test=self._send_e_bilanz_test,
            on_send_production=self._send_e_bilanz_production,
            parent=self._e_bilanz_tab,
        )

        layout.addWidget(self._e_bilanz_frame)

    def _refresh_e_bilanz_availability(self) -> None:
        """Aktiviert die E-Bilanz nur für unterstützte Rechtsformen."""

        tab_index = self._notebook.indexOf(
            self._e_bilanz_tab
        )

        if tab_index < 0:
            return

        self._notebook.setTabEnabled(
            tab_index,
            self._company_master_data.supports_e_bilanz,
        )

    def _refresh_taxonomy_status(self) -> None:
        """Aktualisiert den Taxonomiestatus des Geschäftsjahres."""

        status = self._workspace.taxonomy_status

        if status.complete:
            status_text = "installiert und vollständig"
        elif status.installed:
            status_text = "installiert, aber unvollständig"
        else:
            status_text = "nicht installiert"

        self._e_bilanz_frame.set_taxonomy_status(
            text=(
                "Benötigte Taxonomie: "
                f"{status.required_version.value}\n"
                f"Status: {status_text}"
            ),
            install_enabled=not status.usable,
        )

    def _install_required_taxonomy(self) -> None:
        """Installiert die benötigte Taxonomie."""

        try:
            self._workspace.install_required_taxonomy()
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Taxonomie konnte nicht installiert werden",
                str(exc),
            )
            return

        self._refresh_taxonomy_status()
        self._refresh_e_bilanz()

        QMessageBox.information(
            self,
            "Taxonomie",
            "Die benötigte Taxonomie wurde erfolgreich installiert.",
        )

    def _refresh_bvv_evaluation(self) -> None:
        """Aktualisiert den aus der Buchführung ermittelten BVV."""

        if not self._company_master_data.supports_e_bilanz:
            self._e_bilanz_frame.clear_bvv_evaluation()
            return

        if (
            not self._workspace.is_closed
            or self._current_income_statement is None
        ):
            self._e_bilanz_frame.clear_bvv_evaluation()
            return

        try:
            preparation = self._workspace.prepare_e_bilanz(
                income_statement=self._current_income_statement,
            )
            evaluation = self._workspace.build_bvv_evaluation(
                preparation=preparation,
                chart_of_accounts=self._chart_of_accounts,
            )
        except (
            ValueError,
            RuntimeError,
        ):
            self._e_bilanz_frame.clear_bvv_evaluation()
            return

        def amount(value: object) -> str:
            return f"{self._format_amount(value)} €"

        self._e_bilanz_frame.set_bvv_evaluation(
            current_hgb_equity=amount(
                evaluation.current_hgb_equity
            ),
            current_book_value_difference=amount(
                evaluation.current_book_value_difference
            ),
            current_tax_equity=amount(
                evaluation.current_tax_equity
            ),
            previous_hgb_equity=amount(
                evaluation.previous_hgb_equity
            ),
            previous_book_value_difference=amount(
                evaluation.previous_book_value_difference
            ),
            previous_tax_equity=amount(
                evaluation.previous_tax_equity
            ),
            change_in_tax_equity=amount(
                evaluation.change_in_tax_equity
            ),
            contribution=amount(
                evaluation.contribution
            ),
            withdrawal_distribution=amount(
                evaluation.withdrawal_distribution
            ),
            profit_loss=amount(
                evaluation.profit_loss
            ),
        )

    def _refresh_e_bilanz(self) -> None:
        """Aktualisiert den Zustand des E-Bilanz-Arbeitsbereichs."""

        if not self._workspace.is_closed:
            self._e_bilanz_frame.set_workflow_state(
                status_text=(
                    "Das Geschäftsjahr ist noch nicht abgeschlossen. "
                    "Die E-Bilanz kann erst nach dem "
                    "Jahresabschluss vorbereitet werden."
                ),
                prepare_enabled=False,
                build_enabled=False,
                validate_enabled=False,
                export_enabled=False,
            )
            return

        if self._current_e_bilanz_preparation is None:
            self._e_bilanz_frame.set_workflow_state(
                status_text=(
                    "Das Geschäftsjahr ist abgeschlossen. "
                    "Die E-Bilanz kann vorbereitet werden."
                ),
                prepare_enabled=True,
                build_enabled=False,
                validate_enabled=False,
                export_enabled=False,
            )
            return

        preparation = self._current_e_bilanz_preparation
        taxonomy_status = self._workspace.taxonomy_status

        build_enabled = taxonomy_status.usable
        validate_enabled = (
            self._current_e_bilanz_document is not None
        )
        export_enabled = (
            validate_enabled
            and self._current_e_bilanz_arelle_valid
        )

        status_text = (
            "Die E-Bilanz wurde vorbereitet.\n"
            f"Bilanzpositionen: "
            f"{len(preparation.balance_sheet_amounts)}\n"
            f"GuV-Positionen: "
            f"{len(preparation.income_statement_amounts)}"
        )

        if not taxonomy_status.usable:
            status_text += (
                "\n\nDie benötigte Taxonomie ist nicht "
                "vollständig installiert."
            )

        self._e_bilanz_frame.set_workflow_state(
            status_text=status_text,
            prepare_enabled=True,
            build_enabled=build_enabled,
            validate_enabled=validate_enabled,
            export_enabled=export_enabled,
            transmission_enabled=(
                export_enabled
                and self._elster_bilanz_transmission_service
                is not None
            ),
        )

    def _invalidate_built_e_bilanz(self) -> None:
        """Verwirft eine aus inzwischen geänderten Daten erzeugte E-Bilanz."""

        self._current_e_bilanz_document = None
        self._current_e_bilanz_arelle_valid = False
        self._refresh_e_bilanz()

    def _prepare_e_bilanz(self) -> None:
        """Bereitet die Abschlusswerte für die E-Bilanz auf."""

        if not self._company_master_data.supports_e_bilanz:
            QMessageBox.warning(
                self,
                "E-Bilanz",
                (
                    "Für die gewählte Rechtsform steht die "
                    "E-Bilanz-Funktion nicht zur Verfügung."
                ),
            )
            return

        if not self._workspace.is_closed:
            QMessageBox.warning(
                self,
                "E-Bilanz",
                "Das Geschäftsjahr ist noch nicht abgeschlossen.",
            )
            return

        if self._current_income_statement is None:
            QMessageBox.warning(
                self,
                "E-Bilanz",
                (
                    "Es steht keine GuV für die "
                    "E-Bilanz-Vorbereitung zur Verfügung."
                ),
            )
            return

        try:
            preparation = self._workspace.prepare_e_bilanz(
                income_statement=self._current_income_statement,
            )
        except ValueError as exc:
            QMessageBox.critical(
                self,
                "E-Bilanz konnte nicht vorbereitet werden",
                str(exc),
            )
            return

        self._current_e_bilanz_preparation = preparation
        self._current_e_bilanz_document = None
        self._current_e_bilanz_arelle_valid = False

        self._refresh_bvv_evaluation()
        self._refresh_e_bilanz()

    def _build_e_bilanz(self) -> None:
        """Erzeugt die E-Bilanz aus den vorbereiteten Abschlusswerten."""

        if self._current_e_bilanz_preparation is None:
            QMessageBox.warning(
                self,
                "E-Bilanz",
                "Die E-Bilanz wurde noch nicht vorbereitet.",
            )
            return

        try:
            document = self._workspace.build_e_bilanz(
                preparation=self._current_e_bilanz_preparation,
                chart_of_accounts=self._chart_of_accounts,
            )
        except (
            ValueError,
            FileNotFoundError,
            RuntimeError,
        ) as exc:
            QMessageBox.critical(
                self,
                "E-Bilanz konnte nicht erzeugt werden",
                str(exc),
            )
            return

        self._current_e_bilanz_document = document
        self._current_e_bilanz_arelle_valid = False

        self._refresh_e_bilanz()

        QMessageBox.information(
            self,
            "E-Bilanz",
            "Die E-Bilanz wurde erfolgreich erzeugt.",
        )

    def _validate_e_bilanz(self) -> None:
        """Validiert die erzeugte E-Bilanz mit Arelle."""

        if self._current_e_bilanz_document is None:
            QMessageBox.warning(
                self,
                "E-Bilanz",
                "Die E-Bilanz wurde noch nicht erzeugt.",
            )
            return

        try:
            result = self._workspace.validate_e_bilanz(
                self._current_e_bilanz_document
            )
        except (
            ValueError,
            RuntimeError,
        ) as exc:
            QMessageBox.critical(
                self,
                "E-Bilanz konnte nicht validiert werden",
                str(exc),
            )
            return

        if result.is_valid:
            self._current_e_bilanz_arelle_valid = True
            self._refresh_e_bilanz()

            QMessageBox.information(
                self,
                "E-Bilanz",
                (
                    "Die E-Bilanz wurde von Arelle "
                    "erfolgreich validiert."
                ),
            )
            return

        self._current_e_bilanz_arelle_valid = False
        self._refresh_e_bilanz()

        errors = "\n".join(result.errors)

        QMessageBox.critical(
            self,
            "E-Bilanz-Validierung fehlgeschlagen",
            (
                "Arelle hat Fehler in der E-Bilanz "
                f"festgestellt.\n\n{errors}"
            ),
        )

    def _send_e_bilanz_test(self) -> None:
        """Übermittelt die E-Bilanz als echte ELSTER-Testsendung."""

        if self._elster_bilanz_transmission_service is None:
            QMessageBox.critical(
                self,
                "ELSTER-Testübermittlung",
                "Die ERiC-/ELSTER-Konfiguration ist nicht vollständig.",
            )
            return

        if self._current_e_bilanz_document is None:
            QMessageBox.warning(
                self,
                "ELSTER-Testübermittlung",
                "Die E-Bilanz wurde noch nicht erzeugt.",
            )
            return

        if not self._current_e_bilanz_arelle_valid:
            QMessageBox.warning(
                self,
                "ELSTER-Testübermittlung",
                (
                    "Die E-Bilanz muss zuerst erfolgreich "
                    "mit Arelle validiert werden."
                ),
            )
            return

        confirmation, accepted = QInputDialog.getText(
            self,
            "ELSTER-Testübermittlung",
            (
                "ACHTUNG: Diese Funktion stellt eine echte "
                "Verbindung zum ELSTER-Server her.\n\n"
                "Der Datensatz wird ausschließlich als "
                "Testsendung mit dem ELSTER-Testmerker "
                "700000004 übertragen.\n\n"
                "Zum Start bitte exakt TESTSENDUNG eingeben:"
            ),
        )

        if not accepted or confirmation != "TESTSENDUNG":
            return

        try:
            master_data = self._workspace.load_company_master_data()

            validated = (
                self._elster_bilanz_transmission_service
                .validate_test_transmission(
                    xbrl_xml=self._current_e_bilanz_document.xml,
                    master_data=master_data,
                    balance_sheet_date=(
                        self._context.fiscal_year.end_date
                    ),
                )
            )

            send_result = (
                self._elster_bilanz_transmission_service
                .send_test_transmission(
                    validated=validated,
                )
            )
            transmitted_at = datetime.now()

        except EricValidateError as exc:
            message_box = QMessageBox(self)
            message_box.setIcon(
                QMessageBox.Icon.Critical
            )
            message_box.setWindowTitle(
                "ELSTER-Testübermittlung fehlgeschlagen"
            )
            message_box.setText(str(exc))

            if exc.response_xml:
                message_box.setDetailedText(
                    exc.response_xml
                )

            message_box.exec()
            return

        except (
            ValueError,
            FileNotFoundError,
            RuntimeError,
        ) as exc:
            QMessageBox.critical(
                self,
                "ELSTER-Testübermittlung fehlgeschlagen",
                str(exc),
            )
            return

        answer = QMessageBox.question(
            self,
            "ELSTER-Testübermittlung",
            (
                "Die ELSTER-Testübermittlung wurde "
                "ohne Fehler abgeschlossen.\n\n"
                "Testmerker: 700000004\n\n"
                "TransferTicket:\n"
                f"{send_result.transfer_ticket}\n\n"
                "Es wurde keine produktive "
                "Steuerübermittlung durchgeführt.\n\n"
                "Soll ein Übertragungsnachweis "
                "gespeichert werden?"
            ),
            (
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No
            ),
            QMessageBox.StandardButton.Yes,
        )

        if answer == QMessageBox.StandardButton.Yes:
            self._save_elster_transmission_receipt(
                transfer_ticket=send_result.transfer_ticket,
                transmission_mode="TEST",
                test_marker="700000004",
                transmitted_at=transmitted_at,
            )

    def _send_e_bilanz_production(self) -> None:
        """Übermittelt die E-Bilanz produktiv an ELSTER."""

        if self._elster_bilanz_transmission_service is None:
            QMessageBox.critical(
                self,
                "ELSTER-Produktivübermittlung",
                "Die ERiC-/ELSTER-Konfiguration ist nicht vollständig.",
            )
            return

        if self._current_e_bilanz_document is None:
            QMessageBox.warning(
                self,
                "ELSTER-Produktivübermittlung",
                "Die E-Bilanz wurde noch nicht erzeugt.",
            )
            return

        if not self._current_e_bilanz_arelle_valid:
            QMessageBox.warning(
                self,
                "ELSTER-Produktivübermittlung",
                (
                    "Die E-Bilanz muss zuerst erfolgreich "
                    "mit Arelle validiert werden."
                ),
            )
            return

        confirmation, accepted = QInputDialog.getText(
            self,
            "ELSTER-Produktivübermittlung",
            (
                "ACHTUNG: Dies ist eine PRODUKTIVE "
                "ELSTER-Übermittlung.\n\n"
                "Der Datensatz wird ohne Testmerker an ELSTER "
                "übertragen und ist keine Testsendung.\n\n"
                "Bitte prüfen Sie vor dem Versand nochmals "
                "Mandant, Geschäftsjahr und E-Bilanz.\n\n"
                "Zum endgültigen Start bitte exakt "
                "PRODUKTIV SENDEN eingeben:"
            ),
        )

        if not accepted or confirmation != "PRODUKTIV SENDEN":
            return

        try:
            master_data = self._workspace.load_company_master_data()

            validated = (
                self._elster_bilanz_transmission_service
                .validate_production_transmission(
                    xbrl_xml=self._current_e_bilanz_document.xml,
                    master_data=master_data,
                    balance_sheet_date=(
                        self._context.fiscal_year.end_date
                    ),
                )
            )

            send_result = (
                self._elster_bilanz_transmission_service
                .send_production_transmission(
                    validated=validated,
                )
            )
            transmitted_at = datetime.now()

        except (
            ValueError,
            FileNotFoundError,
            RuntimeError,
        ) as exc:
            QMessageBox.critical(
                self,
                "ELSTER-Produktivübermittlung fehlgeschlagen",
                str(exc),
            )
            return

        answer = QMessageBox.question(
            self,
            "ELSTER-Produktivübermittlung",
            (
                "Die produktive ELSTER-Übermittlung wurde "
                "ohne Fehler abgeschlossen.\n\n"
                "TransferTicket:\n"
                f"{send_result.transfer_ticket}\n\n"
                "Soll ein Übertragungsnachweis "
                "gespeichert werden?"
            ),
            (
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No
            ),
            QMessageBox.StandardButton.Yes,
        )

        if answer == QMessageBox.StandardButton.Yes:
            self._save_elster_transmission_receipt(
                transfer_ticket=send_result.transfer_ticket,
                transmission_mode="PRODUKTIV",
                test_marker=None,
                transmitted_at=transmitted_at,
            )

    def _save_elster_transmission_receipt(
        self,
        *,
        transfer_ticket: str,
        transmission_mode: str,
        test_marker: str | None,
        transmitted_at: datetime,
    ) -> None:
        """Speichert einen Nachweis der ELSTER-Übertragung."""

        context = self._workspace.context
        fiscal_year = context.fiscal_year

        safe_company_name = "".join(
            character
            if character.isalnum() or character in "-_"
            else "_"
            for character in context.company.name
        ).strip("_")

        timestamp = transmitted_at.strftime("%Y%m%d_%H%M%S")

        default_filename = (
            "SimpleOB_ELSTER_"
            f"{safe_company_name}_"
            f"{fiscal_year.end_date.year}_"
            f"{transmission_mode}_"
            f"{timestamp}.txt"
        )

        filename, _ = QFileDialog.getSaveFileName(
            self,
            "ELSTER-Übertragungsnachweis speichern",
            default_filename,
            "Textdateien (*.txt);;Alle Dateien (*)",
        )

        if not filename:
            return

        target = Path(filename)

        if target.suffix.lower() != ".txt":
            target = target.with_suffix(".txt")

        lines = [
            "SimpleOB – ELSTER-Übertragungsnachweis",
            "",
            f"Mandant: {context.company.name}",
            (
                "Geschäftsjahr: "
                f"{fiscal_year.start_date:%d.%m.%Y} – "
                f"{fiscal_year.end_date:%d.%m.%Y}"
            ),
            f"Übertragung: {transmission_mode}",
            (
                "Zeitpunkt: "
                f"{transmitted_at:%d.%m.%Y %H:%M:%S}"
            ),
            "Datenart: Bilanz_6.9",
        ]

        if test_marker is not None:
            lines.append(f"Testmerker: {test_marker}")

        lines.extend(
            (
                f"TransferTicket: {transfer_ticket}",
                "Status: Übertragung erfolgreich",
                "",
            )
        )

        try:
            target.write_text(
                "\n".join(lines),
                encoding="utf-8",
            )
        except OSError as exc:
            QMessageBox.critical(
                self,
                "ELSTER-Übertragungsnachweis",
                (
                    "Der Übertragungsnachweis konnte nicht "
                    f"gespeichert werden.\n\n{exc}"
                ),
            )
            return

        QMessageBox.information(
            self,
            "ELSTER-Übertragungsnachweis",
            (
                "Der Übertragungsnachweis wurde gespeichert.\n\n"
                f"{target}"
            ),
        )

    def _export_bvv_pdf(self) -> None:
        """Exportiert den Betriebsvermögensvergleich als PDF."""

        if (
            not self._workspace.is_closed
            or self._current_income_statement is None
        ):
            QMessageBox.warning(
                self,
                "Betriebsvermögensvergleich",
                (
                    "Es steht kein Betriebsvermögensvergleich "
                    "für den PDF-Export zur Verfügung."
                ),
            )
            return

        try:
            preparation = self._workspace.prepare_e_bilanz(
                income_statement=self._current_income_statement,
            )
            evaluation = self._workspace.build_bvv_evaluation(
                preparation=preparation,
                chart_of_accounts=self._chart_of_accounts,
            )
        except (
            ValueError,
            RuntimeError,
        ) as exc:
            QMessageBox.critical(
                self,
                "BVV PDF konnte nicht exportiert werden",
                str(exc),
            )
            return

        context = self._workspace.context
        fiscal_year = context.fiscal_year

        safe_company_name = "".join(
            character
            if character.isalnum() or character in "-_"
            else "_"
            for character in context.company.name
        ).strip("_")

        default_filename = (
            "SimpleOB_BVV_"
            f"{safe_company_name}_"
            f"{fiscal_year.end_date.year}.pdf"
        )

        filename, _ = QFileDialog.getSaveFileName(
            self,
            "BVV als PDF exportieren",
            default_filename,
            "PDF-Dateien (*.pdf);;Alle Dateien (*)",
        )

        if not filename:
            return

        target = Path(filename)

        if target.suffix.lower() != ".pdf":
            target = target.with_suffix(".pdf")

        try:
            exported_path = (
                self._pdf_reporting_service.export_bvv(
                    evaluation=evaluation,
                    company_name=context.company.name,
                    fiscal_year_name=(
                        f"{fiscal_year.start_date:%d.%m.%Y} – "
                        f"{fiscal_year.end_date:%d.%m.%Y}"
                    ),
                    target=target,
                )
            )
        except OSError as exc:
            QMessageBox.critical(
                self,
                "BVV PDF konnte nicht exportiert werden",
                str(exc),
            )
            return

        QMessageBox.information(
            self,
            "Betriebsvermögensvergleich",
            (
                "Der Betriebsvermögensvergleich wurde "
                "erfolgreich als PDF exportiert.\n\n"
                f"{exported_path}"
            ),
        )

    def _export_e_bilanz(self) -> None:
        """Exportiert die erfolgreich validierte E-Bilanz."""

        if self._current_e_bilanz_document is None:
            QMessageBox.warning(
                self,
                "E-Bilanz",
                "Die E-Bilanz wurde noch nicht erzeugt.",
            )
            return

        filename, _ = QFileDialog.getSaveFileName(
            self,
            "E-Bilanz exportieren",
            "",
            "XBRL-Dateien (*.xbrl);;Alle Dateien (*)",
        )

        if not filename:
            return

        target = Path(filename)

        if target.suffix.lower() != ".xbrl":
            target = target.with_suffix(".xbrl")

        try:
            exported_path = self._workspace.export_e_bilanz(
                document=self._current_e_bilanz_document,
                target=target,
            )
        except (
            ValueError,
            OSError,
        ) as exc:
            QMessageBox.critical(
                self,
                "E-Bilanz konnte nicht exportiert werden",
                str(exc),
            )
            return

        QMessageBox.information(
            self,
            "E-Bilanz",
            (
                "Die E-Bilanz wurde erfolgreich exportiert.\n\n"
                f"{exported_path}"
            ),
        )

    def _export_e_bilanz_pdf(self) -> None:
        """Exportiert die E-Bilanz-Abschlusswerte als PDF."""

        if self._current_e_bilanz_preparation is None:
            QMessageBox.warning(
                self,
                "E-Bilanz PDF",
                "Die E-Bilanz wurde noch nicht vorbereitet.",
            )
            return

        if (
            self._current_e_bilanz_document is None
            or not self._current_e_bilanz_arelle_valid
        ):
            QMessageBox.warning(
                self,
                "E-Bilanz PDF",
                (
                    "Die E-Bilanz muss zuerst erzeugt und "
                    "erfolgreich mit Arelle validiert werden."
                ),
            )
            return

        context = self._workspace.context
        fiscal_year = context.fiscal_year

        fixed_asset_schedule = (
            self._workspace.build_fixed_asset_schedule()
        )

        fixed_asset_position_names: dict[str, str] = {}

        if fixed_asset_schedule:

            def collect_position_names(position) -> None:
                fixed_asset_position_names[
                    position.code
                ] = position.name

                for child in position.children:
                    collect_position_names(child)

            collect_position_names(self._assets)

        safe_company_name = "".join(
            character
            if character.isalnum() or character in "-_"
            else "_"
            for character in context.company.name
        ).strip("_")

        default_filename = (
            "SimpleOB_E-Bilanz_"
            f"{safe_company_name}_"
            f"{fiscal_year.end_date.year}.pdf"
        )

        filename, _ = QFileDialog.getSaveFileName(
            self,
            "E-Bilanz als PDF exportieren",
            default_filename,
            "PDF-Dateien (*.pdf);;Alle Dateien (*)",
        )

        if not filename:
            return

        target = Path(filename)

        if target.suffix.lower() != ".pdf":
            target = target.with_suffix(".pdf")

        try:
            exported_path = (
                self._pdf_reporting_service.export_e_bilanz(
                    preparation=self._current_e_bilanz_preparation,
                    company_name=context.company.name,
                    fiscal_year_name=(
                        f"{fiscal_year.start_date:%d.%m.%Y} – "
                        f"{fiscal_year.end_date:%d.%m.%Y}"
                    ),
                    target=target,
                    fixed_asset_schedule=fixed_asset_schedule,
                    fixed_asset_position_names=(
                        fixed_asset_position_names
                    ),
                )
            )
        except (
            ValueError,
            OSError,
        ) as exc:
            QMessageBox.critical(
                self,
                "E-Bilanz PDF konnte nicht exportiert werden",
                str(exc),
            )
            return

        QMessageBox.information(
            self,
            "E-Bilanz PDF",
            (
                "Die E-Bilanz wurde erfolgreich als PDF "
                "exportiert.\n\n"
                f"{exported_path}"
            ),
        )

    def _create_closing_tab(self) -> None:
        """Erzeugt den Arbeitsbereich Jahresabschluss."""

        layout = QVBoxLayout(self._closing_tab)

        self._closing_frame = ClosingFrame(
            on_validate=self._validate_closing,
            on_close=self._close_fiscal_year,
            on_edit_profit_appropriation=(
                self._edit_profit_appropriation
            ),
            on_post_previous_profit_appropriation=(
                self._post_previous_profit_appropriation
            ),
            parent=self._closing_tab,
        )

        layout.addWidget(self._closing_frame)

    def _create_balance_sheet_tab(self) -> None:
        """Erzeugt den Arbeitsbereich Bilanz."""

        layout = QVBoxLayout(self._balance_sheet_tab)

        title_label = QLabel("Bilanz nach § 266 HGB")
        title_label.setStyleSheet(
            "font-size: 18px; font-weight: bold;"
        )
        layout.addWidget(title_label)

        export_button = QPushButton("PDF exportieren")
        export_button.clicked.connect(
            self._export_balance_sheet_pdf
        )
        layout.addWidget(export_button)

        self._balance_sheet_frame = BalanceSheetFrame(
            self._balance_sheet_tab
        )
        layout.addWidget(self._balance_sheet_frame)

    def _create_income_statement_tab(self) -> None:
        """Erzeugt den Arbeitsbereich GuV."""

        layout = QVBoxLayout(self._income_statement_tab)

        title_label = QLabel(
            "Gewinn- und Verlustrechnung nach § 275 HGB"
        )
        title_label.setStyleSheet(
            "font-size: 18px; font-weight: bold;"
        )
        layout.addWidget(title_label)

        export_button = QPushButton("PDF exportieren")
        export_button.clicked.connect(
            self._export_income_statement_pdf
        )
        layout.addWidget(export_button)

        self._income_statement_frame = IncomeStatementFrame(
            self._income_statement_tab
        )
        layout.addWidget(self._income_statement_frame)

    def _create_reports_tab(self) -> None:
        """Erzeugt den Arbeitsbereich Auswertungen."""

        layout = QVBoxLayout(self._reports_tab)

        self._reports_widget = ReportsWidget(
            context=self._context,
            workspace=self._workspace,
            accounts=self._accounts,
            opening_balance_account_number=(
                self._opening_balance_account_number
            ),
            pdf_reporting_service=(
                self._pdf_reporting_service
            ),
            parent=self._reports_tab,
        )

        layout.addWidget(self._reports_widget)

    def _create_accounts_tab(self) -> None:
        """Erzeugt den Arbeitsbereich Konten."""

        layout = QVBoxLayout(self._accounts_tab)

        accounts_label = QLabel("Kontenübersicht")
        accounts_label.setStyleSheet(
            "font-size: 18px; font-weight: bold;"
        )
        layout.addWidget(accounts_label)

        button_layout = QHBoxLayout()

        self._new_account_button = QPushButton(
            "Neues Konto"
        )
        self._new_account_button.clicked.connect(
            self._open_new_account
        )
        self._new_account_button.setEnabled(
            self._workspace.is_open
        )

        button_layout.addWidget(
            self._new_account_button
        )

        self._edit_account_button = QPushButton(
            "Konto bearbeiten"
        )
        self._edit_account_button.clicked.connect(
            self._open_edit_account
        )
        self._edit_account_button.setEnabled(
            not self._workspace.is_closed
        )

        button_layout.addWidget(
            self._edit_account_button
        )

        self._e_bilanz_mapping_button = QPushButton(
            "E-Bilanz-Zuordnung"
        )
        self._e_bilanz_mapping_button.clicked.connect(
            self._open_e_bilanz_account_mapping
        )

        button_layout.addWidget(
            self._e_bilanz_mapping_button
        )

        self._e_bilanz_mapping_label = QLabel(
            "Zuordnung: –"
        )
        button_layout.addWidget(
            self._e_bilanz_mapping_label,
            1,
        )

        button_layout.addStretch()

        layout.addLayout(button_layout)

        self._journal_status = QLabel(
            f"Journal: {len(self._workspace.journal)} Buchungen"
        )
        layout.addWidget(self._journal_status)

        self._account_table = QTableWidget()
        self._account_table.setColumnCount(6)
        self._account_table.setHorizontalHeaderLabels(
            (
                "Konto",
                "Bezeichnung",
                "Soll",
                "Haben",
                "Saldo",
                "E-Bilanz",
            )
        )

        self._account_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self._account_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self._account_table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self._account_table.setAlternatingRowColors(True)
        self._account_table.itemSelectionChanged.connect(
            self._refresh_e_bilanz_mapping_label
        )

        header = self._account_table.horizontalHeader()
        header.setSectionResizeMode(
            0,
            QHeaderView.ResizeMode.ResizeToContents,
        )
        header.setSectionResizeMode(
            1,
            QHeaderView.ResizeMode.Stretch,
        )
        header.setSectionResizeMode(
            2,
            QHeaderView.ResizeMode.ResizeToContents,
        )
        header.setSectionResizeMode(
            3,
            QHeaderView.ResizeMode.ResizeToContents,
        )
        header.setSectionResizeMode(
            4,
            QHeaderView.ResizeMode.ResizeToContents,
        )
        header.setSectionResizeMode(
            5,
            QHeaderView.ResizeMode.ResizeToContents,
        )

        layout.addWidget(self._account_table)

        self._refresh_accounts()

    def _create_booking_tab(self) -> None:
        """Erzeugt den Arbeitsbereich Buchen."""

        layout = QVBoxLayout(self._booking_tab)

        booking_label = QLabel("Neue Buchung")
        booking_label.setStyleSheet(
            "font-size: 18px; font-weight: bold;"
        )
        layout.addWidget(booking_label)

        mode_layout = QHBoxLayout()

        mode_layout.addWidget(
            QLabel("Buchungsart")
        )

        self._booking_mode_box = QComboBox()
        self._booking_mode_box.addItems(
            (
                "Einfache Buchung",
                "Rechnung mit Umsatzsteuer",
            )
        )
        self._booking_mode_box.setCurrentText(
            "Einfache Buchung"
        )
        self._booking_mode_box.setMaximumWidth(280)

        mode_layout.addWidget(
            self._booking_mode_box
        )
        mode_layout.addStretch()

        layout.addLayout(mode_layout)

        technical_account_numbers = {
            self._opening_balance_account_number,
            self._closing_accounts.income_summary_account,
            self._closing_accounts.profit_account,
            self._closing_accounts.loss_account,
        }

        manual_bookable_accounts = tuple(
            account
            for account in self._accounts
            if (
                account.is_active
                and account.number
                not in technical_account_numbers
            )
        )

        vat_booking_account_numbers = {
            *technical_account_numbers,
            *self._vat_accounts.account_numbers,
        }

        vat_bookable_accounts = tuple(
            account
            for account in self._accounts
            if (
                account.is_active
                and account.number
                not in vat_booking_account_numbers
            )
        )

        self._booking_frame_container = QWidget()
        self._booking_frame_layout = QVBoxLayout(
            self._booking_frame_container
        )
        self._booking_frame_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        equity_contribution_account_numbers = frozenset(
            rule.account_number
            for rule in self._chart_of_accounts.account_mapping_rules
            if (
                rule.credit_position is not None
                and rule.credit_position.code
                in {
                    "HGB.266.PASSIVA.A.I",
                    "HGB.266.PASSIVA.A.II",
                }
            )
        )

        self._booking_frame = BookingFrame(
            self._booking_frame_container,
            accounts=manual_bookable_accounts,
            equity_contribution_account_numbers=(
                equity_contribution_account_numbers
            ),
            on_booking_created=self._post_booking,
        )

        self._vat_booking_frame = VatBookingFrame(
            self._booking_frame_container,
            accounts=vat_bookable_accounts,
            vat_accounts=self._vat_accounts,
            on_booking_created=self._post_booking,
        )

        self._booking_frame_layout.addWidget(
            self._booking_frame
        )
        self._booking_frame_layout.addWidget(
            self._vat_booking_frame
        )

        layout.addWidget(
            self._booking_frame_container
        )

        self._booking_mode_box.currentTextChanged.connect(
            self._update_booking_mode
        )

        self._update_editing_state()
        self._update_booking_mode()

    def _update_editing_state(self) -> None:
        """Aktualisiert den Bearbeitungszustand des Geschäftsjahres."""

        enabled = self._workspace.is_open

        self._booking_frame.set_enabled(enabled)
        self._vat_booking_frame.set_enabled(enabled)
        self._booking_mode_box.setEnabled(enabled)
        self._opening_balance_button.setEnabled(enabled)

    def _update_booking_mode(
        self,
        *_args: object,
    ) -> None:
        """Schaltet zwischen einfacher und Umsatzsteuerbuchung um."""

        vat_mode = (
            self._booking_mode_box.currentText()
            == "Rechnung mit Umsatzsteuer"
        )

        self._booking_frame.setVisible(
            not vat_mode
        )
        self._vat_booking_frame.setVisible(
            vat_mode
        )

    def _post_booking(
        self,
        booking,
        equity_contribution_line_positions: tuple[int, ...] = (),
    ) -> None:
        """Verbucht und speichert eine Buchung."""

        if self._workspace.is_closed:
            return

        self._workspace.post_booking(
            booking,
            equity_contribution_line_positions=(
                equity_contribution_line_positions
            ),
            chart_of_accounts=(
                self._chart_of_accounts
                if equity_contribution_line_positions
                else None
            ),
        )

        self._refresh_accounts()
        self._refresh_journal()
        self._refresh_balance_sheet()

    def _create_fixed_assets_tab(self) -> None:
        """Erzeugt den Arbeitsbereich Anlagen."""

        layout = QVBoxLayout(self._fixed_assets_tab)

        header_layout = QHBoxLayout()

        fixed_assets_label = QLabel("Anlagegüter")
        fixed_assets_label.setStyleSheet(
            "font-size: 18px; font-weight: bold;"
        )
        header_layout.addWidget(
            fixed_assets_label
        )

        header_layout.addStretch()

        self._add_fixed_asset_button = QPushButton(
            "Anlagegut hinzufügen"
        )

        self._add_fixed_asset_button.clicked.connect(
            self._open_new_fixed_asset
        )

        self._add_fixed_asset_button.setEnabled(
            self._workspace.is_open
        )

        header_layout.addWidget(
            self._add_fixed_asset_button
        )

        self._export_fixed_asset_schedule_pdf_button = QPushButton(
            "Anlagenspiegel PDF exportieren"
        )

        self._export_fixed_asset_schedule_pdf_button.clicked.connect(
            self._export_fixed_asset_schedule_pdf
        )

        header_layout.addWidget(
            self._export_fixed_asset_schedule_pdf_button
        )

        self._fixed_asset_actions_menu = QMenu(
            self
        )

        self._process_depreciations_action = (
            self._fixed_asset_actions_menu.addAction(
                "Abschreibungen prüfen/buchen"
            )
        )
        self._process_depreciations_action.triggered.connect(
            self._process_depreciations
        )
        self._process_depreciations_action.setEnabled(
            self._workspace.is_open
        )

        self._tax_depreciation_adjustments_action = (
            self._fixed_asset_actions_menu.addAction(
                "Steuerliche AfA-Abweichungen"
            )
        )
        self._tax_depreciation_adjustments_action.triggered.connect(
            self._manage_tax_depreciation_adjustments
        )
        self._tax_depreciation_adjustments_action.setEnabled(
            self._workspace.is_open
        )

        self._fixed_asset_actions_button = QPushButton(
            "Aktionen"
        )
        self._fixed_asset_actions_button.setMenu(
            self._fixed_asset_actions_menu
        )
        header_layout.addWidget(
            self._fixed_asset_actions_button
        )

        layout.addLayout(
            header_layout
        )

        self._fixed_asset_table = QTableWidget()
        self._fixed_asset_table.setColumnCount(11)
        self._fixed_asset_table.setHorizontalHeaderLabels(
            (
                "Anlagen-ID",
                "Bezeichnung",
                "Anschaffung",
                "AK/HK",
                "kum. AfA",
                "Buchwert",
                "ND Monate",
                "Anlagekonto",
                "AfA-Konto",
                "Anschaffungsbuchung",
                "Status",
            )
        )

        self._fixed_asset_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self._fixed_asset_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self._fixed_asset_table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self._fixed_asset_table.setAlternatingRowColors(
            True
        )
        self._fixed_asset_table.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )
        self._fixed_asset_table.customContextMenuRequested.connect(
            self._show_fixed_asset_context_menu
        )

        header = self._fixed_asset_table.horizontalHeader()

        header.setSectionResizeMode(
            0,
            QHeaderView.ResizeMode.ResizeToContents,
        )
        header.setSectionResizeMode(
            1,
            QHeaderView.ResizeMode.Stretch,
        )

        for column in range(2, 11):
            header.setSectionResizeMode(
                column,
                QHeaderView.ResizeMode.ResizeToContents,
            )

        layout.addWidget(
            self._fixed_asset_table
        )

        self._refresh_fixed_assets()

    def _export_fixed_asset_schedule_pdf(self) -> None:
        """Exportiert den Anlagenspiegel als PDF."""

        positions = self._workspace.build_fixed_asset_schedule()

        if not positions:
            QMessageBox.information(
                self,
                "Anlagenspiegel PDF",
                (
                    "Für das ausgewählte Geschäftsjahr "
                    "ist kein Anlagenspiegel vorhanden."
                ),
            )
            return

        position_names: dict[str, str] = {}

        def collect_position_names(position) -> None:
            position_names[position.code] = position.name

            for child in position.children:
                collect_position_names(child)

        collect_position_names(self._assets)

        context = self._workspace.context
        fiscal_year = context.fiscal_year

        safe_company_name = "".join(
            character
            if character.isalnum() or character in "-_"
            else "_"
            for character in context.company.name
        ).strip("_")

        default_filename = (
            "SimpleOB_Anlagenspiegel_"
            f"{safe_company_name}_"
            f"{fiscal_year.end_date.year}.pdf"
        )

        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Anlagenspiegel als PDF exportieren",
            default_filename,
            "PDF-Dateien (*.pdf);;Alle Dateien (*)",
        )

        if not filename:
            return

        target = Path(filename)

        if target.suffix.lower() != ".pdf":
            target = target.with_suffix(".pdf")

        try:
            exported_path = (
                self._pdf_reporting_service.export_fixed_asset_schedule(
                    positions=positions,
                    position_names=position_names,
                    company_name=context.company.name,
                    fiscal_year_name=(
                        f"{fiscal_year.start_date:%d.%m.%Y} – "
                        f"{fiscal_year.end_date:%d.%m.%Y}"
                    ),
                    target=target,
                )
            )
        except (ValueError, OSError) as exc:
            QMessageBox.critical(
                self,
                "Anlagenspiegel PDF konnte nicht exportiert werden",
                str(exc),
            )
            return

        QMessageBox.information(
            self,
            "Anlagenspiegel PDF",
            (
                "Der Anlagenspiegel wurde erfolgreich als PDF "
                "exportiert.\n\n"
                f"{exported_path}"
            ),
        )

    def _refresh_fixed_assets(self) -> None:
        """Aktualisiert die Liste der Anlagegüter."""

        try:
            assets = self._workspace.list_fixed_assets()
        except RuntimeError:
            self._fixed_assets = ()
            self._fixed_asset_table.setRowCount(0)
            return

        self._fixed_assets = tuple(
            assets
        )

        self._fixed_asset_table.setRowCount(
            len(self._fixed_assets)
        )

        for row, asset in enumerate(
            self._fixed_assets
        ):
            accumulated_depreciation = (
                self._workspace
                .fixed_asset_accumulated_depreciation(
                    asset.fixed_asset_id
                )
            )

            carrying_amount = (
                asset.acquisition_cost
                - accumulated_depreciation
            )
            status = (
                "Aktiv"
                if asset.status.value == "ACTIVE"
                else "Abgegangen"
            )

            try:
                acquisition_linked = (
                    self._workspace.has_fixed_asset_acquisition(
                        asset.fixed_asset_id
                    )
                )
            except RuntimeError:
                acquisition_linked = False

            acquisition_booking = (
                "zugeordnet"
                if acquisition_linked
                else "nicht zugeordnet"
            )

            values = (
                asset.asset_code,
                asset.description,
                asset.acquisition_date.strftime(
                    "%d.%m.%Y"
                ),
                self._format_amount(
                    asset.acquisition_cost
                ),
                self._format_amount(
                    accumulated_depreciation
                ),
                self._format_amount(
                    carrying_amount
                ),
                asset.useful_life_months,
                asset.asset_account_number,
                asset.depreciation_expense_account_number,
                acquisition_booking,
                status,
            )

            for column, value in enumerate(
                values
            ):
                item = QTableWidgetItem(
                    str(value)
                )

                if column in (3, 4, 5, 6):
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignRight
                        | Qt.AlignmentFlag.AlignVCenter
                    )

                self._fixed_asset_table.setItem(
                    row,
                    column,
                    item,
                )

        self._fixed_asset_table.resizeRowsToContents()

    def _selected_fixed_asset(self):
        """Gibt das aktuell ausgewählte Anlagegut zurück."""

        row = self._fixed_asset_table.currentRow()

        if row < 0:
            return None

        if row >= len(
            self._fixed_assets
        ):
            return None

        return self._fixed_assets[row]

    def _show_fixed_asset_context_menu(
        self,
        position,
    ) -> None:
        """Zeigt die Aktionen für ein Anlagegut an."""

        item = self._fixed_asset_table.itemAt(
            position
        )

        if item is None:
            return

        self._fixed_asset_table.selectRow(
            item.row()
        )

        menu = QMenu(
            self._fixed_asset_table
        )

        edit_action = menu.addAction(
            "Anlagegut bearbeiten"
        )
        delete_action = menu.addAction(
            "Anlagegut löschen"
        )

        menu.addSeparator()

        acquisition_action = menu.addAction(
            "Anschaffungsbuchung zuordnen"
        )

        sale_action = menu.addAction(
            "Anlagegut verkaufen …"
        )

        disposal_action = menu.addAction(
            "Abgangsbuchung zuordnen"
        )

        enabled = self._workspace.is_open

        edit_action.setEnabled(
            enabled
        )
        delete_action.setEnabled(
            enabled
        )
        acquisition_action.setEnabled(
            enabled
        )
        sale_action.setEnabled(
            enabled
        )
        disposal_action.setEnabled(
            enabled
        )

        selected_action = menu.exec(
            self._fixed_asset_table.viewport().mapToGlobal(
                position
            )
        )

        if selected_action is edit_action:
            self._open_edit_fixed_asset()
        elif selected_action is delete_action:
            self._delete_fixed_asset()
        elif selected_action is acquisition_action:
            self._open_link_fixed_asset_acquisition()
        elif selected_action is sale_action:
            self._open_fixed_asset_disposal()
        elif selected_action is disposal_action:
            self._open_link_fixed_asset_disposal()

    def _open_new_fixed_asset(self) -> None:
        """Öffnet den Dialog für ein neues Anlagegut."""

        if not self._workspace.is_open:
            return

        dialog = NewFixedAssetDialog(
            self,
            company_id=(
                self._context.company.company_id
            ),
            depreciation_expense_account_number=(
                self._depreciation_expense_account_number
            ),
        )

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        if dialog.result is None:
            return

        try:
            self._workspace.add_fixed_asset(
                dialog.result
            )
        except (
            ValueError,
            RuntimeError,
        ) as exc:
            QMessageBox.critical(
                self,
                "Anlagegut kann nicht angelegt werden",
                str(exc),
            )
            return

        self._refresh_fixed_assets()

        QMessageBox.information(
            self,
            "Anlagegut",
            "Das Anlagegut wurde angelegt.",
        )

    def _open_edit_fixed_asset(self) -> None:
        """Öffnet ein Anlagegut zur Bearbeitung."""

        if not self._workspace.is_open:
            return

        fixed_asset = self._selected_fixed_asset()

        if fixed_asset is None:
            QMessageBox.information(
                self,
                "Anlagegut bearbeiten",
                "Bitte zuerst ein Anlagegut auswählen.",
            )
            return

        try:
            acquisition_linked = (
                self._workspace.has_fixed_asset_acquisition(
                    fixed_asset.fixed_asset_id
                )
            )
        except RuntimeError as exc:
            QMessageBox.critical(
                self,
                "Anlagegut kann nicht bearbeitet werden",
                str(exc),
            )
            return

        dialog = NewFixedAssetDialog(
            self,
            company_id=(
                self._context.company.company_id
            ),
            depreciation_expense_account_number=(
                self._depreciation_expense_account_number
            ),
            fixed_asset=fixed_asset,
            acquisition_linked=acquisition_linked,
        )

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        if dialog.result is None:
            return

        try:
            self._workspace.update_fixed_asset(
                dialog.result
            )
        except (
            ValueError,
            RuntimeError,
        ) as exc:
            QMessageBox.critical(
                self,
                "Anlagegut kann nicht bearbeitet werden",
                str(exc),
            )
            return

        self._refresh_fixed_assets()

        QMessageBox.information(
            self,
            "Anlagegut",
            "Das Anlagegut wurde geändert.",
        )

    def _delete_fixed_asset(self) -> None:
        """Löscht ein noch nicht buchungswirksames Anlagegut."""

        if not self._workspace.is_open:
            return

        fixed_asset = self._selected_fixed_asset()

        if fixed_asset is None:
            QMessageBox.information(
                self,
                "Anlagegut löschen",
                "Bitte zuerst ein Anlagegut auswählen.",
            )
            return

        answer = QMessageBox.question(
            self,
            "Anlagegut löschen",
            (
                f"Soll das Anlagegut "
                f"„{fixed_asset.asset_code} – "
                f"{fixed_asset.description}“ "
                "wirklich gelöscht werden?\n\n"
                "Dieser Vorgang kann nicht rückgängig "
                "gemacht werden."
            ),
            (
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No
            ),
            QMessageBox.StandardButton.No,
        )

        if answer != QMessageBox.StandardButton.Yes:
            return

        try:
            self._workspace.delete_fixed_asset(
                fixed_asset.fixed_asset_id
            )
        except (
            ValueError,
            RuntimeError,
        ) as exc:
            QMessageBox.critical(
                self,
                "Anlagegut kann nicht gelöscht werden",
                str(exc),
            )
            return

        self._refresh_fixed_assets()

        QMessageBox.information(
            self,
            "Anlagegut",
            "Das Anlagegut wurde gelöscht.",
        )

    def _open_link_fixed_asset_acquisition(self) -> None:
        """Ordnet eine vorhandene Buchung einem Anlagegut zu."""

        if not self._workspace.is_open:
            return

        fixed_asset = self._selected_fixed_asset()

        if fixed_asset is None:
            QMessageBox.information(
                self,
                "Anschaffungsbuchung zuordnen",
                "Bitte zuerst ein Anlagegut auswählen.",
            )
            return

        try:
            if self._workspace.has_fixed_asset_acquisition(
                fixed_asset.fixed_asset_id
            ):
                QMessageBox.information(
                    self,
                    "Anschaffungsbuchung zuordnen",
                    (
                        "Dem ausgewählten Anlagegut ist bereits "
                        "eine Anschaffungsbuchung zugeordnet."
                    ),
                )
                return
        except RuntimeError as exc:
            QMessageBox.critical(
                self,
                "Anschaffungsbuchung kann nicht zugeordnet werden",
                str(exc),
            )
            return

        candidates: list[AcquisitionBookingCandidate] = []

        reversed_booking_ids = {
            booking.reversal_of_booking_id
            for booking in self._workspace.journal.bookings
            if (
                booking.booking_type is BookingType.REVERSAL
                and booking.reversal_of_booking_id is not None
            )
        }

        for booking in self._workspace.journal.bookings:
            if booking.booking_type is not BookingType.REGULAR:
                continue

            if booking.booking_id in reversed_booking_ids:
                continue

            for position, line in enumerate(booking.lines):
                if (
                    line.account_number
                    != fixed_asset.asset_account_number
                ):
                    continue

                if line.side is not EntrySide.DEBIT:
                    continue

                if line.amount != fixed_asset.acquisition_cost:
                    continue

                candidates.append(
                    AcquisitionBookingCandidate(
                        booking_id=booking.booking_id,
                        booking_line_position=position,
                        booking_date_text=(
                            booking.booking_date.strftime(
                                "%d.%m.%Y"
                            )
                        ),
                        voucher_no=booking.voucher_no or "",
                        description=booking.description or "",
                        account_number=line.account_number,
                        amount=line.amount,
                    )
                )

        if not candidates:
            QMessageBox.information(
                self,
                "Anschaffungsbuchung zuordnen",
                (
                    "Es wurde keine passende "
                    "Anschaffungsbuchung gefunden."
                ),
            )
            return

        dialog = FixedAssetAcquisitionLinkDialog(
            self,
            candidates=tuple(candidates),
        )

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        candidate = dialog.selected_candidate

        if candidate is None:
            return

        try:
            self._workspace.link_fixed_asset_acquisition(
                fixed_asset_id=fixed_asset.fixed_asset_id,
                booking_id=candidate.booking_id,
                booking_line_position=(
                    candidate.booking_line_position
                ),
            )
        except (
            ValueError,
            RuntimeError,
        ) as exc:
            QMessageBox.critical(
                self,
                (
                    "Anschaffungsbuchung konnte "
                    "nicht zugeordnet werden"
                ),
                str(exc),
            )
            return

        QMessageBox.information(
            self,
            "Anschaffungsbuchung",
            (
                "Die Anschaffungsbuchung wurde "
                "dem Anlagegut zugeordnet."
            ),
        )

        self._refresh_fixed_assets()

    def _open_fixed_asset_disposal(self) -> None:
        """Erfasst und bucht den Verkauf eines Anlageguts."""

        if not self._workspace.is_open:
            return

        fixed_asset = self._selected_fixed_asset()

        if fixed_asset is None:
            QMessageBox.information(
                self,
                "Anlagegut verkaufen",
                "Bitte zuerst ein Anlagegut auswählen.",
            )
            return

        if fixed_asset.status.value != "ACTIVE":
            QMessageBox.information(
                self,
                "Anlagegut verkaufen",
                "Das ausgewählte Anlagegut ist bereits abgegangen.",
            )
            return

        try:
            acquisition_linked = (
                self._workspace.has_fixed_asset_acquisition(
                    fixed_asset.fixed_asset_id
                )
            )
        except RuntimeError as exc:
            QMessageBox.critical(
                self,
                "Anlagenverkauf kann nicht vorbereitet werden",
                str(exc),
            )
            return

        if not acquisition_linked:
            QMessageBox.information(
                self,
                "Anlagegut verkaufen",
                (
                    "Dem ausgewählten Anlagegut ist noch keine "
                    "Anschaffungsbuchung zugeordnet."
                ),
            )
            return

        dialog = FixedAssetDisposalDialog(
            self,
            fixed_asset=fixed_asset,
            accounts=self._accounts,
        )

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        disposal_input = dialog.result

        if disposal_input is None:
            return

        try:
            preview = (
                self._workspace.build_fixed_asset_disposal_preview(
                    fixed_asset_id=fixed_asset.fixed_asset_id,
                    disposal_date=disposal_input.disposal_date,
                    gross_proceeds=disposal_input.gross_proceeds,
                    tax_rate=disposal_input.tax_rate,
                    counter_account_number=(
                        disposal_input.counter_account_number
                    ),
                    voucher_no=disposal_input.voucher_no,
                    description=(
                        "Verkauf Anlagegut "
                        f"{fixed_asset.asset_code} – "
                        f"{fixed_asset.description}"
                    ),
                )
            )
        except (
            ValueError,
            RuntimeError,
        ) as exc:
            QMessageBox.critical(
                self,
                "Anlagenverkauf kann nicht vorbereitet werden",
                str(exc),
            )
            return

        if preview.depreciation_proposal is not None:
            proposal = preview.depreciation_proposal

            answer = QMessageBox.question(
                self,
                "Abschreibung vor Anlagenverkauf",
                (
                    "Vor dem Anlagenverkauf ist noch eine "
                    "Abschreibung zu buchen.\n\n"
                    f"Betrag: {proposal.amount:.2f} €\n"
                    "Aufwandskonto: "
                    f"{proposal.expense_account_number}\n"
                    "Anlagenkonto: "
                    f"{proposal.asset_account_number}\n"
                    "Datum: "
                    f"{proposal.depreciation_date:%d.%m.%Y}\n\n"
                    "Soll diese Abschreibung jetzt gebucht werden?"
                ),
                (
                    QMessageBox.StandardButton.Yes
                    | QMessageBox.StandardButton.No
                ),
                QMessageBox.StandardButton.No,
            )

            if answer != QMessageBox.StandardButton.Yes:
                return

            try:
                self._workspace.confirm_depreciation(
                    proposal
                )

                preview = (
                    self._workspace.build_fixed_asset_disposal_preview(
                        fixed_asset_id=fixed_asset.fixed_asset_id,
                        disposal_date=disposal_input.disposal_date,
                        gross_proceeds=disposal_input.gross_proceeds,
                        tax_rate=disposal_input.tax_rate,
                        counter_account_number=(
                            disposal_input.counter_account_number
                        ),
                        voucher_no=disposal_input.voucher_no,
                        description=(
                            "Verkauf Anlagegut "
                            f"{fixed_asset.asset_code} – "
                            f"{fixed_asset.description}"
                        ),
                    )
                )

            except (
                ValueError,
                RuntimeError,
            ) as exc:
                QMessageBox.critical(
                    self,
                    "Anlagenverkauf kann nicht vorbereitet werden",
                    str(exc),
                )
                return

        calculation = preview.disposal_calculation

        booking_lines = []

        for line in calculation.booking.lines:
            side = (
                "Soll"
                if line.side is EntrySide.DEBIT
                else "Haben"
            )

            booking_lines.append(
                f"{line.account_number}  "
                f"{side}  {line.amount:.2f} €"
            )

        booking_preview = "\n".join(
            booking_lines
        )

        result_label = (
            f"Gewinn: {calculation.gain:.2f} €"
            if calculation.gain > ZERO
            else (
                f"Verlust: {calculation.loss:.2f} €"
                if calculation.loss > ZERO
                else "Gewinn/Verlust: 0,00 €"
            )
        )

        answer = QMessageBox.question(
            self,
            "Anlagenverkauf bestätigen",
            (
                f"Anlagegut: {fixed_asset.asset_code} – "
                f"{fixed_asset.description}\n"
                "Abgangsdatum: "
                f"{disposal_input.disposal_date:%d.%m.%Y}\n\n"
                "Anschaffungskosten: "
                f"{calculation.acquisition_cost:.2f} €\n"
                "Kumulierte AfA: "
                f"{calculation.accumulated_depreciation:.2f} €\n"
                "Restbuchwert: "
                f"{calculation.carrying_amount:.2f} €\n\n"
                "Verkaufspreis brutto: "
                f"{calculation.gross_proceeds:.2f} €\n"
                "Nettoerlös: "
                f"{calculation.net_proceeds:.2f} €\n"
                "Umsatzsteuer: "
                f"{calculation.tax_amount:.2f} €\n"
                f"{result_label}\n\n"
                "Buchung:\n"
                f"{booking_preview}\n\n"
                "Soll der Anlagenverkauf gebucht werden?"
            ),
            (
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No
            ),
            QMessageBox.StandardButton.No,
        )

        if answer != QMessageBox.StandardButton.Yes:
            return

        try:
            self._workspace.confirm_fixed_asset_disposal(
                preview
            )
        except (
            ValueError,
            RuntimeError,
        ) as exc:
            QMessageBox.critical(
                self,
                "Anlagenverkauf konnte nicht gebucht werden",
                str(exc),
            )
            return

        QMessageBox.information(
            self,
            "Anlagenverkauf",
            "Der Anlagenverkauf wurde erfolgreich gebucht.",
        )

        self._refresh_accounts()
        self._refresh_journal()
        self._refresh_fixed_assets()
        self._refresh_balance_sheet()

    def _open_link_fixed_asset_disposal(self) -> None:
        """Ordnet eine vorhandene Abgangsbuchung einem Anlagegut zu."""

        if not self._workspace.is_open:
            return

        fixed_asset = self._selected_fixed_asset()

        if fixed_asset is None:
            QMessageBox.information(
                self,
                "Abgangsbuchung zuordnen",
                "Bitte zuerst ein Anlagegut auswählen.",
            )
            return

        if fixed_asset.status.value != "ACTIVE":
            QMessageBox.information(
                self,
                "Abgangsbuchung zuordnen",
                "Das ausgewählte Anlagegut ist bereits abgegangen.",
            )
            return

        try:
            acquisition_linked = (
                self._workspace.has_fixed_asset_acquisition(
                    fixed_asset.fixed_asset_id
                )
            )
        except RuntimeError as exc:
            QMessageBox.critical(
                self,
                "Abgangsbuchung kann nicht zugeordnet werden",
                str(exc),
            )
            return

        if not acquisition_linked:
            QMessageBox.information(
                self,
                "Abgangsbuchung zuordnen",
                (
                    "Dem ausgewählten Anlagegut ist noch keine "
                    "Anschaffungsbuchung zugeordnet."
                ),
            )
            return

        candidates: list[DisposalBookingCandidate] = []

        for booking in self._workspace.journal.bookings:
            if (
                booking.booking_date
                < fixed_asset.acquisition_date
            ):
                continue

            for position, line in enumerate(booking.lines):
                if (
                    line.account_number
                    != fixed_asset.asset_account_number
                ):
                    continue

                if line.side is not EntrySide.CREDIT:
                    continue

                candidates.append(
                    DisposalBookingCandidate(
                        booking_id=booking.booking_id,
                        booking_line_position=position,
                        booking_date_text=(
                            booking.booking_date.strftime(
                                "%d.%m.%Y"
                            )
                        ),
                        voucher_no=booking.voucher_no or "",
                        description=booking.description or "",
                        account_number=line.account_number,
                        amount=line.amount,
                    )
                )

        if not candidates:
            QMessageBox.information(
                self,
                "Abgangsbuchung zuordnen",
                (
                    "Es wurde keine passende "
                    "Abgangsbuchung gefunden."
                ),
            )
            return

        dialog = FixedAssetDisposalLinkDialog(
            self,
            candidates=tuple(candidates),
        )

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        candidate = dialog.selected_candidate

        if candidate is None:
            return

        try:
            self._workspace.link_fixed_asset_disposal(
                fixed_asset_id=fixed_asset.fixed_asset_id,
                booking_id=candidate.booking_id,
                booking_line_position=(
                    candidate.booking_line_position
                ),
            )
        except (
            ValueError,
            RuntimeError,
        ) as exc:
            QMessageBox.critical(
                self,
                "Abgangsbuchung konnte nicht zugeordnet werden",
                str(exc),
            )
            return

        QMessageBox.information(
            self,
            "Abgangsbuchung",
            (
                "Die Abgangsbuchung wurde "
                "dem Anlagegut zugeordnet."
            ),
        )

        self._refresh_fixed_assets()

    def _process_depreciations(self) -> None:
        """Prüft und bucht offene Abschreibungen."""

        try:
            proposals = (
                self._workspace.build_depreciation_proposals()
            )
        except (
            ValueError,
            RuntimeError,
        ) as exc:
            QMessageBox.critical(
                self,
                "Abschreibungen konnten nicht vorbereitet werden",
                str(exc),
            )
            return

        if not proposals:
            QMessageBox.information(
                self,
                "Abschreibungen",
                (
                    "Für dieses Geschäftsjahr sind keine "
                    "offenen Abschreibungen vorhanden."
                ),
            )
            return
        fixed_assets = self._workspace.list_fixed_assets()

        fixed_assets_by_id = {
            fixed_asset.fixed_asset_id: fixed_asset
            for fixed_asset in fixed_assets
        }

        for proposal in proposals:
            fixed_asset = fixed_assets_by_id.get(
                proposal.fixed_asset_id
            )

            if fixed_asset is None:
                QMessageBox.critical(
                    self,
                    "Abschreibung bestätigen",
                    (
                        "Das Anlagegut zur vorgeschlagenen "
                        "Abschreibung wurde nicht gefunden.\n\n"
                        "Anlagen-ID: "
                        f"{proposal.fixed_asset_id}"
                    ),
                )
                break

            answer = QMessageBox.question(
                self,
                "Abschreibung bestätigen",
                (
                    "Für folgendes Anlagegut wurde eine lineare "
                    "Abschreibung ermittelt:\n\n"
                    "Bezeichnung: "
                    f"{fixed_asset.description}\n"
                    "Anlagen-Nummer: "
                    f"{fixed_asset.asset_code}\n\n"
                    f"Betrag: {proposal.amount:.2f} €\n"
                    "Aufwandskonto: "
                    f"{proposal.expense_account_number}\n"
                    "Anlagenkonto: "
                    f"{proposal.asset_account_number}\n"
                    "Datum: "
                    f"{proposal.depreciation_date:%d.%m.%Y}\n\n"
                    "Soll diese Abschreibung gebucht werden?"
                ),
                (
                    QMessageBox.StandardButton.Yes
                    | QMessageBox.StandardButton.No
                ),
                QMessageBox.StandardButton.No,
            )

            if answer != QMessageBox.StandardButton.Yes:
                continue

            try:
                self._workspace.confirm_depreciation(
                    proposal
                )
            except (
                ValueError,
                RuntimeError,
            ) as exc:
                QMessageBox.critical(
                    self,
                    "Abschreibung konnte nicht gebucht werden",
                    str(exc),
                )
                break

        self._refresh_accounts()
        self._refresh_journal()
        self._refresh_fixed_assets()
        self._refresh_balance_sheet()

    def _manage_tax_depreciation_adjustments(self) -> None:
        """Bearbeitet steuerliche AfA-Abweichungen."""

        try:
            depreciations = (
                self._workspace.list_confirmed_depreciations()
            )
            fixed_assets = (
                self._workspace.list_fixed_assets()
            )
        except (
            ValueError,
            RuntimeError,
        ) as exc:
            QMessageBox.critical(
                self,
                "Steuerliche AfA-Abweichungen",
                str(exc),
            )
            return

        if not depreciations:
            QMessageBox.information(
                self,
                "Steuerliche AfA-Abweichungen",
                (
                    "Für dieses Geschäftsjahr sind noch keine "
                    "bestätigten Abschreibungen vorhanden."
                ),
            )
            return

        fixed_assets_by_id = {
            fixed_asset.fixed_asset_id: fixed_asset
            for fixed_asset in fixed_assets
        }

        for depreciation in depreciations:
            fixed_asset = fixed_assets_by_id.get(
                depreciation.fixed_asset_id
            )

            if fixed_asset is None:
                QMessageBox.critical(
                    self,
                    "Steuerliche AfA-Abweichungen",
                    (
                        "Das Anlagegut zu einer bestätigten "
                        "Abschreibung konnte nicht gefunden werden."
                    ),
                )
                return

            try:
                adjustment = (
                    self._workspace
                    .get_tax_depreciation_adjustment(
                        depreciation.depreciation_id
                    )
                )
            except (
                ValueError,
                RuntimeError,
            ) as exc:
                QMessageBox.critical(
                    self,
                    "Steuerliche AfA-Abweichungen",
                    str(exc),
                )
                return

            initial_tax_amount = (
                adjustment.tax_amount
                if adjustment is not None
                else depreciation.amount
            )

            dialog = TaxDepreciationAdjustmentDialog(
                self,
                fixed_asset=fixed_asset,
                depreciation=depreciation,
                initial_tax_amount=initial_tax_amount,
            )

            if dialog.exec() != QDialog.DialogCode.Accepted:
                break

            if dialog.result is None:
                break

            try:
                self._workspace.save_tax_depreciation_adjustment(
                    depreciation_id=(
                        depreciation.depreciation_id
                    ),
                    tax_amount=dialog.result,
                )
            except (
                ValueError,
                RuntimeError,
            ) as exc:
                QMessageBox.critical(
                    self,
                    (
                        "Steuerliche AfA-Abweichung konnte "
                        "nicht gespeichert werden"
                    ),
                    str(exc),
                )
                break

    def _create_journal_tab(self) -> None:
        """Erzeugt den Arbeitsbereich Journal."""

        layout = QVBoxLayout(self._journal_tab)

        journal_label = QLabel("Journal")
        journal_label.setStyleSheet(
            "font-size: 18px; font-weight: bold;"
        )
        layout.addWidget(journal_label)

        self._journal_table = QTableWidget()
        self._journal_table.setColumnCount(6)
        self._journal_table.setHorizontalHeaderLabels(
            (
                "Datum",
                "Beleg",
                "Buchungstext",
                "Konto",
                "S/H",
                "Betrag",
            )
        )

        self._journal_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self._journal_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self._journal_table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self._journal_table.setAlternatingRowColors(True)

        header = self._journal_table.horizontalHeader()

        header.setSectionResizeMode(
            0,
            QHeaderView.ResizeMode.ResizeToContents,
        )
        header.setSectionResizeMode(
            1,
            QHeaderView.ResizeMode.ResizeToContents,
        )
        header.setSectionResizeMode(
            2,
            QHeaderView.ResizeMode.Stretch,
        )
        header.setSectionResizeMode(
            3,
            QHeaderView.ResizeMode.Stretch,
        )
        header.setSectionResizeMode(
            4,
            QHeaderView.ResizeMode.ResizeToContents,
        )
        header.setSectionResizeMode(
            5,
            QHeaderView.ResizeMode.ResizeToContents,
        )

        layout.addWidget(self._journal_table)

        self._journal_reversal_button = QPushButton(
            "Buchung stornieren"
        )
        self._journal_reversal_button.clicked.connect(
            self._reverse_selected_journal_booking
        )
        layout.addWidget(
            self._journal_reversal_button,
            alignment=Qt.AlignmentFlag.AlignLeft,
        )

        self._refresh_journal()

    def _refresh_journal(self) -> None:
        """Aktualisiert die Journalanzeige."""

        self._journal_table.setRowCount(0)
        self._journal_booking_ids: dict[int, UUID] = {}

        account_names = {
            account.number: account.name
            for account in self._accounts
        }

        for booking in self._workspace.journal:
            first_line = True

            for line in booking.lines:
                account_name = account_names.get(
                    line.account_number,
                    "Unbekanntes Konto",
                )

                account_display = (
                    f"{line.account_number} – "
                    f"{account_name}"
                )

                if line.is_debit:
                    side = "Soll"
                else:
                    side = "Haben"

                row = self._journal_table.rowCount()
                self._journal_table.insertRow(row)

                self._journal_booking_ids[
                    row
                ] = booking.booking_id

                values = (
                    (
                        booking.booking_date.strftime(
                            "%d.%m.%Y"
                        )
                        if first_line
                        else ""
                    ),
                    (
                        booking.voucher_no or ""
                        if first_line
                        else ""
                    ),
                    (
                        booking.description or ""
                        if first_line
                        else ""
                    ),
                    account_display,
                    side,
                    self._format_amount(
                        line.amount
                    ),
                )

                for column, value in enumerate(values):
                    item = QTableWidgetItem(
                        str(value)
                    )

                    if column == 4:
                        item.setTextAlignment(
                            Qt.AlignmentFlag.AlignCenter
                        )

                    if column == 5:
                        item.setTextAlignment(
                            Qt.AlignmentFlag.AlignRight
                            | Qt.AlignmentFlag.AlignVCenter
                        )

                    self._journal_table.setItem(
                        row,
                        column,
                        item,
                    )

                first_line = False

    def _reverse_selected_journal_booking(
        self,
    ) -> None:
        """Storniert die im Journal ausgewählte reguläre Buchung."""

        selected_rows = (
            self._journal_table.selectionModel().selectedRows()
        )

        if not selected_rows:
            QMessageBox.warning(
                self,
                "Buchung stornieren",
                (
                    "Bitte wählen Sie zuerst eine "
                    "Buchung im Journal aus."
                ),
            )
            return

        row = selected_rows[0].row()

        booking_id = self._journal_booking_ids.get(
            row
        )

        if booking_id is None:
            QMessageBox.critical(
                self,
                "Buchung stornieren",
                (
                    "Die ausgewählte Buchung konnte "
                    "nicht ermittelt werden."
                ),
            )
            return

        original_booking = next(
            (
                booking
                for booking in self._workspace.journal
                if booking.booking_id == booking_id
            ),
            None,
        )

        if original_booking is None:
            QMessageBox.critical(
                self,
                "Buchung stornieren",
                (
                    "Die ausgewählte Buchung konnte "
                    "im Journal nicht gefunden werden."
                ),
            )
            return

        if (
            original_booking.booking_type
            is not BookingType.REGULAR
        ):
            QMessageBox.critical(
                self,
                "Buchung stornieren",
                (
                    "Nur reguläre Buchungen können "
                    "über das Journal storniert werden."
                ),
            )
            return

        if self._workspace.is_closed:
            QMessageBox.critical(
                self,
                "Buchung stornieren",
                (
                    "Das Geschäftsjahr ist abgeschlossen. "
                    "Eine Stornobuchung ist nicht mehr möglich."
                ),
            )
            return

        default_date = date.today()

        if not self._context.fiscal_year.contains(
            default_date
        ):
            default_date = (
                self._context.fiscal_year.end_date
            )

        reversal_date_text, accepted = (
            QInputDialog.getText(
                self,
                "Buchung stornieren",
                (
                    "Bitte geben Sie das Stornodatum ein "
                    "(TT.MM.JJJJ):"
                ),
                text=default_date.strftime(
                    "%d.%m.%Y"
                ),
            )
        )

        if not accepted:
            return

        try:
            reversal_date = parse_german_date(
                reversal_date_text
            )

            reversal_booking = (
                self._workspace
                .create_reversal_booking(
                    booking_id=booking_id,
                    reversal_date=reversal_date,
                )
            )

        except (TypeError, ValueError) as exc:
            QMessageBox.critical(
                self,
                "Buchung stornieren",
                str(exc),
            )
            return

        account_names = {
            account.number: account.name
            for account in self._accounts
        }

        preview_lines = []

        for line in reversal_booking.lines:
            account_name = account_names.get(
                line.account_number,
                "Unbekanntes Konto",
            )

            side = (
                "Soll"
                if line.side is EntrySide.DEBIT
                else "Haben"
            )

            preview_lines.append(
                (
                    f"{line.account_number} "
                    f"{account_name}\n"
                    f"    {side}: "
                    f"{self._format_amount(line.amount)}"
                )
            )

        preview = "\n\n".join(
            preview_lines
        )

        confirmation, accepted = (
            QInputDialog.getText(
                self,
                "Stornobuchung bestätigen",
                (
                    "Folgende Stornobuchung wird erzeugt:\n\n"
                    f"Datum: "
                    f"{reversal_booking.booking_date.strftime('%d.%m.%Y')}\n"
                    f"Buchungstext: "
                    f"{reversal_booking.description or ''}\n\n"
                    f"{preview}\n\n"
                    "Die ursprüngliche Buchung bleibt "
                    "unverändert bestehen.\n\n"
                    "Zum endgültigen Buchen geben Sie exakt "
                    "DURCHFÜHREN ein:"
                ),
            )
        )

        if not accepted:
            return

        if confirmation != "DURCHFÜHREN":
            QMessageBox.information(
                self,
                "Buchung stornieren",
                (
                    "Die Stornobuchung wurde nicht "
                    "durchgeführt."
                ),
            )
            return

        try:
            self._workspace.post_booking(
                reversal_booking
            )
        except (TypeError, ValueError) as exc:
            QMessageBox.critical(
                self,
                "Buchung stornieren",
                str(exc),
            )
            return

        self._refresh_journal()
        self._refresh_accounts()
        self._refresh_fixed_assets()
        self._refresh_balance_sheet()

        QMessageBox.information(
            self,
            "Buchung storniert",
            (
                "Die Stornobuchung wurde erfolgreich "
                "gebucht.\n\n"
                "Die ursprüngliche Buchung bleibt "
                "im Journal erhalten."
            ),
        )

    def _return_to_start(self) -> None:
        """Schließt die aktuelle Buchhaltung und kehrt zur Auswahl zurück."""

        answer = QMessageBox.question(
            self,
            "Buchhaltung wechseln",
            (
                "Möchten Sie die aktuelle Buchhaltung schließen "
                "und zur Buchhaltungsauswahl zurückkehren?"
            ),
            (
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No
            ),
            QMessageBox.StandardButton.No,
        )

        if answer != QMessageBox.StandardButton.Yes:
            return

        self._return_to_start_requested = True
        self.close()

        app = QApplication.instance()
        if app is not None:
            app.quit()

    def _open_opening_balance(self) -> None:
        """Erfasst, verbucht und speichert die Eröffnungsbilanz."""

        if self._workspace.is_closed:
            return

        dialog = OpeningBalanceDialog(
            self,
            accounts=self._accounts,
            excluded_account_numbers={
                self._opening_balance_account_number,
                self._closing_accounts.income_summary_account,
                self._closing_accounts.profit_account,
                self._closing_accounts.loss_account,
            },
        )

        dialog.exec()

        if dialog.result is None:
            return

        bookings = self._opening_balance_service.create_bookings(
            opening_balance=dialog.result,
            booking_date=self._context.fiscal_year.start_date,
        )

        for booking in bookings:
            self._workspace.post_booking(booking)

        self._refresh_accounts()
        self._refresh_journal()
        self._refresh_balance_sheet()

    def _edit_profit_appropriation(self) -> None:
        """Öffnet den Ergebnisverwendungsbeschluss."""

        managed_fiscal_year = self._workspace.managed_fiscal_year

        if managed_fiscal_year.status is not FiscalYearStatus.CLOSED:
            return

        if self._current_closing_result is None:
            QMessageBox.warning(
                self,
                "Ergebnisverwendungsbeschluss",
                (
                    "Das Jahresergebnis konnte nicht ermittelt werden."
                ),
            )
            return

        try:
            initial_data = (
                self._workspace.load_profit_appropriation_annual_data()
            )
            previous_profit_loss_carryforward = (
                self._workspace.previous_profit_loss_carryforward()
            )
            resolution_locked = (
                self._workspace
                .has_effective_profit_appropriation_postings()
            )
        except (ValueError, RuntimeError) as exc:
            QMessageBox.critical(
                self,
                "Ergebnisverwendungsbeschluss",
                (
                    "Der Ergebnisverwendungsbeschluss konnte "
                    "nicht geladen werden.\n\n"
                    f"{exc}"
                ),
            )
            return

        dialog = ProfitAppropriationDialog(
            self,
            fiscal_year_name=(
                managed_fiscal_year.fiscal_year.display_name
            ),
            net_income=self._current_closing_result.net_income,
            previous_profit_loss_carryforward=(
                previous_profit_loss_carryforward
            ),
            initial_data=initial_data,
            read_only=resolution_locked,
        )

        dialog.exec()

        if resolution_locked or dialog.result is None:
            return

        try:
            validation_result = (
                self._workspace.validate_profit_appropriation(
                    net_income=(
                        self._current_closing_result.net_income
                    ),
                    data=dialog.result,
                )
            )

            if not validation_result.is_consistent:
                errors = "\n".join(validation_result.errors)

                QMessageBox.critical(
                    self,
                    "Ergebnisverwendungsbeschluss",
                    (
                        "Der Ergebnisverwendungsbeschluss ist "
                        "rechnerisch nicht ausgeglichen.\n\n"
                        f"{errors}"
                    ),
                )
                return

            self._workspace.save_profit_appropriation_annual_data(
                dialog.result
            )
        except (ValueError, RuntimeError) as exc:
            QMessageBox.critical(
                self,
                "Ergebnisverwendungsbeschluss",
                (
                    "Der Ergebnisverwendungsbeschluss konnte "
                    "nicht gespeichert werden.\n\n"
                    f"{exc}"
                ),
            )
            return

        self._invalidate_built_e_bilanz()
        self._refresh_closing()

        QMessageBox.information(
            self,
            "Ergebnisverwendungsbeschluss",
            (
                "Der Ergebnisverwendungsbeschluss wurde "
                "gespeichert."
            ),
        )

    def _post_previous_profit_appropriation(self) -> None:
        """Bucht die Ergebnisverwendung des Vorjahres."""

        managed_fiscal_year = self._workspace.managed_fiscal_year

        if (
            managed_fiscal_year.status is not FiscalYearStatus.OPEN
            or managed_fiscal_year.opening_source is None
        ):
            return

        default_date = date.today()

        if not managed_fiscal_year.fiscal_year.contains(
            default_date
        ):
            default_date = managed_fiscal_year.fiscal_year.start_date

        booking_date_text, accepted = QInputDialog.getText(
            self,
            "Ergebnisverwendung Vorjahr buchen",
            (
                "Bitte geben Sie das Buchungsdatum ein "
                "(TT.MM.JJJJ):"
            ),
            text=default_date.strftime("%d.%m.%Y"),
        )

        if not accepted:
            return

        try:
            booking_date = parse_german_date(
                booking_date_text
            )

            proposals = (
                self._workspace
                .build_profit_appropriation_posting_proposals(
                    booking_date=booking_date,
                )
            )
        except (
            TypeError,
            ValueError,
            RuntimeError,
        ) as exc:
            QMessageBox.critical(
                self,
                "Ergebnisverwendung konnte nicht vorbereitet werden",
                str(exc),
            )
            return

        if not proposals:
            QMessageBox.information(
                self,
                "Ergebnisverwendung Vorjahr",
                (
                    "Für das Vorjahr sind keine offenen "
                    "Umsetzungsbuchungen zur Ergebnisverwendung "
                    "vorhanden."
                ),
            )
            return

        posting_type_names = {
            "STATUTORY_RESERVE_ADDITION": (
                "Zuführung zur gesetzlichen Rücklage"
            ),
            "OTHER_REVENUE_RESERVES_ADDITION": (
                "Zuführung zu anderen Gewinnrücklagen"
            ),
            "STATUTORY_RESERVE_RELEASE": (
                "Auflösung der gesetzlichen Rücklage"
            ),
            "OTHER_REVENUE_RESERVES_RELEASE": (
                "Auflösung anderer Gewinnrücklagen"
            ),
            "DISTRIBUTION": "Ausschüttung",
        }

        account_names = {
            account.number: account.name
            for account in self._accounts
        }

        for proposal in proposals:
            posting_type_name = posting_type_names.get(
                proposal.posting_type.value,
                proposal.posting_type.value,
            )

            debit_account_name = account_names.get(
                proposal.debit_account_number,
                "Unbekanntes Konto",
            )
            credit_account_name = account_names.get(
                proposal.credit_account_number,
                "Unbekanntes Konto",
            )

            answer = QMessageBox.question(
                self,
                "Ergebnisverwendung buchen",
                (
                    "Folgende Umsetzungsbuchung wurde aus dem "
                    "Ergebnisverwendungsbeschluss des Vorjahres "
                    "ermittelt:\n\n"
                    f"Art: {posting_type_name}\n"
                    f"Betrag: {self._format_amount(proposal.amount)}\n"
                    f"Sollkonto: {proposal.debit_account_number} "
                    f"{debit_account_name}\n"
                    f"Habenkonto: {proposal.credit_account_number} "
                    f"{credit_account_name}\n"
                    "Datum: "
                    f"{proposal.booking_date:%d.%m.%Y}\n\n"
                    "Soll diese Buchung jetzt durchgeführt werden?"
                ),
                (
                    QMessageBox.StandardButton.Yes
                    | QMessageBox.StandardButton.No
                ),
                QMessageBox.StandardButton.No,
            )

            if answer != QMessageBox.StandardButton.Yes:
                continue

            try:
                self._workspace.confirm_profit_appropriation_posting(
                    proposal
                )
            except (
                ValueError,
                RuntimeError,
            ) as exc:
                QMessageBox.critical(
                    self,
                    "Ergebnisverwendung konnte nicht gebucht werden",
                    str(exc),
                )
                break

        self._refresh_accounts()
        self._refresh_journal()
        self._refresh_balance_sheet()
        self._refresh_closing()

    def _validate_closing(self) -> None:
        """Prüft den Jahresabschluss."""

        if (
            self._current_income_statement is None
            or self._current_closing_result is None
            or self._current_balance_sheet is None
        ):
            return

        try:
            depreciation_proposals = (
                self._workspace.build_depreciation_proposals()
            )
        except (ValueError, RuntimeError) as exc:
            QMessageBox.critical(
                self,
                "Abschreibungen konnten nicht geprüft werden",
                str(exc),
            )
            return

        if depreciation_proposals:
            QMessageBox.warning(
                self,
                "Offene Abschreibungen",
                (
                    "Für dieses Geschäftsjahr sind noch "
                    "Abschreibungen zu bearbeiten.\n\n"
                    "Bitte führen Sie zuerst im Bereich "
                    '"Anlagen" die Aktion '
                    '"Abschreibungen prüfen/buchen" aus.'
                ),
            )
            return

        result = self._workspace.validate_closing(
            balance_sheet=self._current_balance_sheet,
            income_statement=self._current_income_statement,
            closing_result=self._current_closing_result,
            balances=self._current_closing_balances,
            mapper=self._account_mapper,
        )

        self._closing_frame.update_consistency(result)

    def _close_fiscal_year(self) -> None:
        """Schließt das Geschäftsjahr persistent ab."""

        if self._workspace.is_closed:
            return

        if self._current_income_statement is None:
            return

        answer = QMessageBox.question(
            self,
            "Geschäftsjahr abschließen",
            (
                "Das Geschäftsjahr wird nun endgültig "
                "abgeschlossen.\n\n"
                "Dabei werden die Erfolgskonten abgeschlossen "
                "und weitere Buchungen in diesem Geschäftsjahr "
                "gesperrt.\n\n"
                "Möchten Sie fortfahren?"
            ),
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if answer != QMessageBox.StandardButton.Yes:
            return

        try:
            result = self._workspace.close_fiscal_year(
                income_statement=self._current_income_statement,
                chart_of_accounts=self._chart_of_accounts,
            )
        except ValueError as exc:
            QMessageBox.critical(
                self,
                "Jahresabschluss fehlgeschlagen",
                str(exc),
            )
            return

        self._refresh_after_closing()

        self._closing_frame.update_net_income(
            result.net_income
        )
        self._closing_frame.mark_closed()

        QMessageBox.information(
            self,
            "Jahresabschluss",
            "Das Geschäftsjahr wurde erfolgreich abgeschlossen.",
        )

    def _refresh_after_closing(self) -> None:
        """Aktualisiert die für den Jahresabschluss relevanten Daten."""

        self._refresh_journal()
        self._refresh_balance_sheet()
        self._refresh_closing()
        self._refresh_bvv_evaluation()
        self._refresh_e_bilanz()
        self._update_editing_state()

    def _refresh_closing(self) -> None:
        """Aktualisiert den sichtbaren Abschlussstatus."""

        managed_fiscal_year = self._workspace.managed_fiscal_year

        self._closing_frame.update_fiscal_year_status(
            managed_fiscal_year.status
        )

        resolution_locked = False

        if managed_fiscal_year.status is FiscalYearStatus.CLOSED:
            try:
                resolution_locked = (
                    self._workspace
                    .has_effective_profit_appropriation_postings()
                )
            except RuntimeError:
                resolution_locked = False

        can_edit_resolution = (
            managed_fiscal_year.status
            is FiscalYearStatus.CLOSED
            and not resolution_locked
        )

        can_post_previous = (
            managed_fiscal_year.status
            is FiscalYearStatus.OPEN
            and managed_fiscal_year.opening_source is not None
        )

        self._closing_frame.update_profit_appropriation_state(
            can_edit_resolution=can_edit_resolution,
            can_post_previous=can_post_previous,
            resolution_locked=resolution_locked,
        )

        if self._current_closing_result is None:
            return

        self._closing_frame.update_net_income(
            self._current_closing_result.net_income
        )

    def _refresh_balance_sheet(self) -> None:
        """Erzeugt und aktualisiert GuV und laufende Bilanz."""

        self._current_balance_sheet = None

        balance_sheet_account_types = (
            AccountType.ASSET,
            AccountType.LIABILITY,
            AccountType.EQUITY,
        )

        income_statement_account_types = (
            AccountType.REVENUE,
            AccountType.EXPENSE,
        )

        balance_sheet_balances = tuple(
            balance
            for balance in self._workspace.ledger.balances()
            if self._account_types.get(balance.account_number)
            in balance_sheet_account_types
            and (
                balance.debit_balance > ZERO
                or balance.credit_balance > ZERO
            )
        )

        income_statement_ledger = (
            self._workspace.pre_closing_ledger
            if self._workspace.is_closed
            else self._workspace.ledger
        )

        income_statement_balances = tuple(
            balance
            for balance in income_statement_ledger.balances()
            if self._account_types.get(balance.account_number)
            in income_statement_account_types
            and (
                balance.debit_balance > ZERO
                or balance.credit_balance > ZERO
            )
        )

        self._current_closing_balances = (
            balance_sheet_balances
            + income_statement_balances
        )

        income_statement_amounts = (
            self._financial_statement_builder.build(
                balances=income_statement_balances,
                root_positions=(self._income_statement,),
            )
        )

        income_statement = IncomeStatement(
            income_statement=self._income_statement,
            amounts=income_statement_amounts,
        )

        self._current_income_statement = income_statement

        net_income = self._closing_service.calculate_net_income(
            income_statement=income_statement,
        )

        self._income_statement_frame.update_income_statement(
            income_statement=income_statement,
            net_income=net_income,
        )

        closing_result = ClosingResult(
            net_income=net_income,
        )

        self._current_closing_result = closing_result

        equity = next(
            position
            for position in self._liabilities.children
            if position.code == "HGB.266.PASSIVA.A"
        )

        result_position = next(
            position
            for position in equity.children
            if position.code == "HGB.266.PASSIVA.A.V"
        )

        try:
            amounts = self._financial_statement_builder.build(
                balances=balance_sheet_balances,
                root_positions=(
                    self._assets,
                    self._liabilities,
                ),
                closing_result=closing_result,
                result_position=result_position,
            )
        except ValueError as exc:
            message = str(exc)

            if (
                "no debit position defined for account"
                not in message
                and "no credit position defined for account"
                not in message
            ):
                raise

            self._balance_sheet_frame.show_mapping_error(
                message
            )
            return

        balance_sheet = BalanceSheet(
            assets=self._assets,
            liabilities=self._liabilities,
            amounts=amounts,
        )

        self._current_balance_sheet = balance_sheet

        self._balance_sheet_frame.update_balance_sheet(
            balance_sheet
        )

    def _export_balance_sheet_pdf(self) -> None:
        """Exportiert die aktuelle Bilanz als PDF."""

        if self._current_balance_sheet is None:
            QMessageBox.warning(
                self,
                "Bilanz",
                "Es steht keine Bilanz für den PDF-Export zur Verfügung.",
            )
            return

        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Bilanz als PDF exportieren",
            "Bilanz.pdf",
            "PDF-Dateien (*.pdf);;Alle Dateien (*)",
        )

        if not filename:
            return

        try:
            exported_path = (
                self._pdf_reporting_service.export_balance_sheet(
                    balance_sheet=self._current_balance_sheet,
                    company_name=self._context.company.name,
                    fiscal_year_name=(
                        self._context.fiscal_year.display_name
                    ),
                    target=Path(filename),
                )
            )
        except OSError as exc:
            QMessageBox.critical(
                self,
                "Bilanz konnte nicht exportiert werden",
                str(exc),
            )
            return

        QMessageBox.information(
            self,
            "Bilanz",
            "PDF erfolgreich exportiert.\n\n"
            f"{exported_path}",
        )

    def _export_income_statement_pdf(self) -> None:
        """Exportiert die aktuelle GuV als PDF."""

        if (
            self._current_income_statement is None
            or self._current_closing_result is None
        ):
            QMessageBox.warning(
                self,
                "Gewinn- und Verlustrechnung",
                "Es steht keine GuV für den PDF-Export zur Verfügung.",
            )
            return

        filename, _ = QFileDialog.getSaveFileName(
            self,
            "GuV als PDF exportieren",
            "GuV.pdf",
            "PDF-Dateien (*.pdf);;Alle Dateien (*)",
        )

        if not filename:
            return

        try:
            exported_path = (
                self._pdf_reporting_service.export_income_statement(
                    income_statement=(
                        self._current_income_statement
                    ),
                    net_income=(
                        self._current_closing_result.net_income
                    ),
                    company_name=self._context.company.name,
                    fiscal_year_name=(
                        self._context.fiscal_year.display_name
                    ),
                    target=Path(filename),
                )
            )
        except OSError as exc:
            QMessageBox.critical(
                self,
                "GuV konnte nicht exportiert werden",
                str(exc),
            )
            return

        QMessageBox.information(
            self,
            "Gewinn- und Verlustrechnung",
            "PDF erfolgreich exportiert.\n\n"
            f"{exported_path}",
        )

    def _open_new_account(self) -> None:
        """Öffnet den Dialog zum Anlegen eines Kontos."""

        if not self._workspace.is_open:
            return

        dialog = AccountEditorDialog(
            self,
            assets=self._assets,
            liabilities=self._liabilities,
            income_statement=self._income_statement,
        )

        dialog.exec()

        if dialog.result is None:
            return

        try:
            self._workspace.add_account(
                account=dialog.result.account,
                mapping_rule=dialog.result.mapping_rule,
            )
        except ValueError as exc:
            QMessageBox.critical(
                self,
                "Konto kann nicht angelegt werden",
                str(exc),
            )
            return

        QMessageBox.information(
            self,
            "Konto angelegt",
            (
                "Das Konto wurde gespeichert.\n\n"
                "Bitte schließen Sie die Buchhaltung und "
                "öffnen Sie sie erneut, damit der geänderte "
                "Kontenrahmen vollständig wirksam wird."
            ),
        )

    def _open_e_bilanz_account_mapping(self) -> None:
        """Bearbeitet die E-Bilanz-Zuordnung des ausgewählten Kontos."""

        selected_rows = (
            self._account_table.selectionModel().selectedRows()
        )

        if not selected_rows:
            QMessageBox.information(
                self,
                "E-Bilanz-Zuordnung",
                "Bitte wählen Sie zuerst ein Konto aus.",
            )
            return

        row = selected_rows[0].row()

        account_number_item = self._account_table.item(
            row,
            0,
        )

        if account_number_item is None:
            return

        account_number = account_number_item.text()

        account = next(
            (
                item
                for item in self._accounts
                if item.number == account_number
            ),
            None,
        )

        if account is None:
            QMessageBox.critical(
                self,
                "E-Bilanz-Zuordnung",
                "Das ausgewählte Konto wurde nicht gefunden.",
            )
            return

        try:
            choices = self._workspace.account_taxonomy_choices(
                account_number=account_number,
                chart_of_accounts=self._chart_of_accounts,
            )

            mappings = (
                self._workspace
                .load_account_taxonomy_concepts()
            )
        except ValueError as exc:
            QMessageBox.critical(
                self,
                "E-Bilanz-Zuordnung",
                str(exc),
            )
            return

        if not choices:
            QMessageBox.information(
                self,
                "E-Bilanz-Zuordnung",
                (
                    "Für die HGB-Zuordnung dieses Kontos "
                    "stehen keine feineren "
                    "E-Bilanz-Taxonomiepositionen zur Auswahl."
                ),
            )
            return

        current_concept_name = mappings.get(
            account_number
        )

        dialog = EBilanzAccountMappingDialog(
            self,
            account_number=account.number,
            account_name=account.name,
            choices=choices,
            current_concept_name=current_concept_name,
        )

        dialog.exec()

        if not dialog.saved:
            return

        try:
            self._workspace.save_account_taxonomy_concept(
                account_number=account_number,
                concept_name=dialog.result,
            )
        except ValueError as exc:
            QMessageBox.critical(
                self,
                "E-Bilanz-Zuordnung",
                str(exc),
            )
            return

        if dialog.result is None:
            message = (
                "Die E-Bilanz-Zuordnung wurde entfernt."
            )
        else:
            message = (
                "Die E-Bilanz-Zuordnung wurde gespeichert."
            )

        self._refresh_accounts()

        QMessageBox.information(
            self,
            "E-Bilanz-Zuordnung",
            message,
        )

    def _open_edit_account(self) -> None:
        """Öffnet den Dialog zum Bearbeiten des ausgewählten Kontos."""

        if self._workspace.is_closed:
            return

        selected_rows = (
            self._account_table.selectionModel().selectedRows()
        )

        if not selected_rows:
            QMessageBox.information(
                self,
                "Konto bearbeiten",
                "Bitte wählen Sie zuerst ein Konto aus.",
            )
            return

        row = selected_rows[0].row()

        account_number_item = self._account_table.item(
            row,
            0,
        )

        if account_number_item is None:
            return

        account_number = account_number_item.text()

        technical_account_numbers = {
            self._opening_balance_account_number,
            self._closing_accounts.income_summary_account,
            self._closing_accounts.profit_account,
            self._closing_accounts.loss_account,
            *self._vat_accounts.account_numbers,
        }

        if account_number in technical_account_numbers:
            QMessageBox.information(
                self,
                "Konto bearbeiten",
                (
                    "Dieses Konto ist als technisches "
                    "Steuerungskonto konfiguriert und kann "
                    "hier nicht bearbeitet werden."
                ),
            )
            return

        account = next(
            (
                item
                for item in self._accounts
                if item.number == account_number
            ),
            None,
        )

        if account is None:
            QMessageBox.critical(
                self,
                "Konto bearbeiten",
                "Das ausgewählte Konto wurde nicht gefunden.",
            )
            return

        mapping_rule = next(
            (
                rule
                for rule
                in self._chart_of_accounts.account_mapping_rules
                if rule.account_number == account_number
            ),
            None,
        )

        dialog = AccountEditorDialog(
            self,
            assets=self._assets,
            liabilities=self._liabilities,
            income_statement=self._income_statement,
            account=account,
            mapping_rule=mapping_rule,
        )

        dialog.exec()

        if dialog.result is None:
            return

        try:
            self._workspace.update_account(
                account=dialog.result.account,
                mapping_rule=dialog.result.mapping_rule,
            )
        except ValueError as exc:
            QMessageBox.critical(
                self,
                "Konto kann nicht geändert werden",
                str(exc),
            )
            return

        self._accounts = tuple(
            dialog.result.account
            if item.number == account_number
            else item
            for item in self._accounts
        )
        self._refresh_accounts()

        QMessageBox.information(
            self,
            "Konto geändert",
            (
                "Das Konto wurde gespeichert.\n\n"
                "Bitte schließen Sie die Buchhaltung und "
                "öffnen Sie sie erneut, damit der geänderte "
                "Kontenrahmen vollständig wirksam wird."
            ),
        )

    def _open_company_master_data(self) -> None:
        """Öffnet die Unternehmensstammdaten."""

        try:
            master_data = (
                self._workspace.load_company_master_data()
            )
        except ValueError as exc:
            QMessageBox.critical(
                self,
                "Unternehmensstammdaten",
                str(exc),
            )
            return

        dialog = CompanyMasterDataDialog(
            self,
            master_data=master_data,
        )

        dialog.exec()

        if dialog.result is None:
            return

        try:
            self._workspace.save_company_master_data(
                dialog.result
            )
        except ValueError as exc:
            QMessageBox.critical(
                self,
                "Unternehmensstammdaten",
                str(exc),
            )
            return

        self._company_master_data = dialog.result
        self._current_e_bilanz_preparation = None
        self._current_e_bilanz_document = None
        self._current_e_bilanz_arelle_valid = False

        self._refresh_e_bilanz_availability()

        if self._company_master_data.supports_e_bilanz:
            self._refresh_taxonomy_status()
            self._refresh_bvv_evaluation()
            self._refresh_e_bilanz()
        else:
            self._e_bilanz_frame.clear_bvv_evaluation()

        QMessageBox.information(
            self,
            "Unternehmensstammdaten",
            "Die Unternehmensstammdaten wurden gespeichert.",
        )

    def _open_shareholders(self) -> None:
        """Öffnet die Gesellschafterverwaltung."""

        dialog = ShareholdersDialog(
            self,
            workspace=self._workspace,
        )
        dialog.exec()

        if dialog.data_changed:
            self._invalidate_built_e_bilanz()

    def _open_account_configuration(self) -> None:
        """Öffnet die mandantenspezifische Kontenkonfiguration."""

        try:
            (
                control_accounts,
                vat_accounts,
                account_roles,
            ) = self._workspace.load_account_configuration()
        except (RuntimeError, ValueError) as exc:
            QMessageBox.critical(
                self,
                "Kontenkonfiguration",
                str(exc),
            )
            return

        dialog = AccountConfigurationDialog(
            self,
            accounts=self._accounts,
            control_accounts=control_accounts,
            vat_accounts=vat_accounts,
            account_roles=account_roles,
        )

        dialog.exec()

        if dialog.result is None:
            return

        (
            control_accounts,
            vat_accounts,
            account_roles,
        ) = dialog.result

        try:
            self._workspace.update_account_configuration(
                control_accounts=control_accounts,
                vat_accounts=vat_accounts,
                account_roles=account_roles,
            )
        except (RuntimeError, ValueError) as exc:
            QMessageBox.critical(
                self,
                "Kontenkonfiguration",
                str(exc),
            )
            return

        self._opening_balance_account_number = (
            control_accounts.opening_balance_account
        )
        self._opening_balance_service = OpeningBalanceService(
            opening_balance_account_number=(
                self._opening_balance_account_number
            ),
        )
        self._depreciation_expense_account_number = (
            control_accounts.depreciation_expense_account
        )
        self._vat_accounts = vat_accounts

        QMessageBox.information(
            self,
            "Kontenkonfiguration",
            "Die Kontenkonfiguration wurde gespeichert.",
        )

    def _refresh_e_bilanz_mapping_label(self) -> None:
        """Zeigt die E-Bilanz-Zuordnung des ausgewählten Kontos."""

        selected_rows = (
            self._account_table.selectionModel().selectedRows()
        )

        if not selected_rows:
            self._e_bilanz_mapping_label.setText(
                "Zuordnung: –"
            )
            return

        row = selected_rows[0].row()

        account_number_item = self._account_table.item(
            row,
            0,
        )

        if account_number_item is None:
            self._e_bilanz_mapping_label.setText(
                "Zuordnung: –"
            )
            return

        account_number = account_number_item.text()

        mappings = (
            self._workspace.load_account_taxonomy_concepts()
        )
        concept_name = mappings.get(account_number)

        if concept_name is None:
            self._e_bilanz_mapping_label.setText(
                "Zuordnung: keine spezielle Zuordnung"
            )
            return

        try:
            choices = self._workspace.account_taxonomy_choices(
                account_number=account_number,
                chart_of_accounts=self._chart_of_accounts,
            )
        except ValueError:
            self._e_bilanz_mapping_label.setText(
                "Zuordnung: nicht verfügbar"
            )
            return

        label_by_concept = {
            choice_concept_name: label
            for choice_concept_name, label in choices
        }

        label = label_by_concept.get(
            concept_name,
            concept_name,
        )

        self._e_bilanz_mapping_label.setText(
            f"Zuordnung: {label}"
        )

    def _refresh_accounts(self) -> None:
        """Aktualisiert die Kontenübersicht."""

        account_taxonomy_concepts = (
            self._workspace.load_account_taxonomy_concepts()
        )

        self._account_table.setRowCount(
            len(self._accounts)
        )

        for row, account in enumerate(self._accounts):
            debit = ZERO
            credit = ZERO
            debit_balance = ZERO
            credit_balance = ZERO

            try:
                ledger_account = self._workspace.ledger.get_account(
                    account.number
                )
            except KeyError:
                pass
            else:
                debit = ledger_account.debit
                credit = ledger_account.credit
                debit_balance = ledger_account.debit_balance
                credit_balance = ledger_account.credit_balance

            balance = self._display_account_balance(
                account_type=account.account_type,
                debit_balance=debit_balance,
                credit_balance=credit_balance,
            )

            e_bilanz_mapping = (
                "✓"
                if account.number in account_taxonomy_concepts
                else ""
            )

            values = (
                account.number,
                account.name,
                self._format_amount(debit),
                self._format_amount(credit),
                balance,
                e_bilanz_mapping,
            )

            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))

                if column in (2, 3, 4):
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignRight
                        | Qt.AlignmentFlag.AlignVCenter
                    )
                elif column == 5:
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignCenter
                    )

                self._account_table.setItem(
                    row,
                    column,
                    item,
                )

        self._account_table.resizeRowsToContents()
        self._refresh_e_bilanz_mapping_label()

    @staticmethod
    def _format_amount(amount: object) -> str:
        """Formatiert einen Betrag mit zwei Nachkommastellen."""

        value = Decimal(str(amount))
        formatted = f"{value:,.2f}"

        return (
            formatted
            .replace(",", "\x00")
            .replace(".", ",")
            .replace("\x00", ".")
        )

    @classmethod
    def _display_account_balance(
        cls,
        *,
        account_type: AccountType,
        debit_balance: object,
        credit_balance: object,
    ) -> str:
        """Formatiert den fachlichen Kontosaldo."""

        if account_type in (
            AccountType.ASSET,
            AccountType.EXPENSE,
        ):
            if debit_balance > ZERO:
                return cls._format_amount(debit_balance)

            if credit_balance > ZERO:
                return "-" + cls._format_amount(
                    credit_balance
                )

        if account_type in (
            AccountType.LIABILITY,
            AccountType.EQUITY,
            AccountType.REVENUE,
        ):
            if credit_balance > ZERO:
                return cls._format_amount(credit_balance)

            if debit_balance > ZERO:
                return "-" + cls._format_amount(
                    debit_balance
                )

        return cls._format_amount(ZERO)

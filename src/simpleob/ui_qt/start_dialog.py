"""PySide6-Startdialog für SimpleOB."""

from collections.abc import Callable
from pathlib import Path

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)
from sqlalchemy.engine import make_url

from simpleob.client_transfer.archive import (
    read_client_transfer_archive,
)
from simpleob.client_transfer.filename import client_backup_filename
from simpleob.client_transfer.model import ClientTransfer
from simpleob.core.config import (
    ApplicationConfig,
    save_database_configuration,
)
from simpleob.core.context import ApplicationContext
from simpleob.database.company_repository import CompanyRepository
from simpleob.domain.company import Company
from simpleob.domain.fiscal_year import FiscalYear
from simpleob.services.client_deletion_service import ClientDeletionCommitUnknown
from simpleob.ui_qt.database_configuration_dialog import (
    DatabaseConfigurationDialog,
)
from simpleob.ui_qt.new_company_dialog import NewCompanyDialog
from simpleob.ui_qt.new_fiscal_year_dialog import (
    NewFiscalYearDialog,
)


class StartDialog(QDialog):
    """Wählt Unternehmen und Geschäftsjahr für die Buchhaltung."""

    def __init__(
        self,
        *,
        repository: CompanyRepository,
        config: ApplicationConfig,
        import_client_transfer: (
            Callable[[ClientTransfer], None] | None
        ) = None,
        delete_client: Callable[[Company, Path], Path] | None = None,
    ) -> None:
        super().__init__()

        self._config = config

        self._repository = repository
        self._import_client_transfer = import_client_transfer
        self._delete_client = delete_client

        self.result: ApplicationContext | None = None
        self.opening_transfer_request: (
            tuple[FiscalYear, FiscalYear] | None
        ) = None

        self._companies: tuple[Company, ...] = ()
        self._fiscal_year_by_display_name: dict[
            str,
            FiscalYear,
        ] = {}

        window_title = "SimpleOB – Buchhaltung öffnen"

        database_url = make_url(self._config.database_url)

        if database_url.get_backend_name() == "postgresql":
            if database_url.username:
                window_title += f" – {database_url.username}"

        self.setWindowTitle(window_title)
        self.resize(850, 360)
        self.setMinimumSize(750, 340)

        self._create_ui()
        self._load_companies()

    def _create_ui(self) -> None:
        """Erzeugt die Benutzeroberfläche."""

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(24)

        # Linker Bereich: Mandanten- und Geschäftsjahrauswahl
        content_layout = QVBoxLayout()
        content_layout.setSpacing(12)

        title_label = QLabel("SimpleOB")
        title_label.setStyleSheet(
            "font-size: 22px; font-weight: bold;"
        )
        content_layout.addWidget(title_label)

        subtitle_label = QLabel("Buchhaltung öffnen")
        subtitle_label.setStyleSheet(
            "font-size: 14px; font-weight: bold;"
        )
        content_layout.addWidget(subtitle_label)

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

        content_layout.addLayout(form_layout)

        self._status_label = QLabel()
        content_layout.addWidget(self._status_label)

        content_layout.addStretch()

        main_layout.addLayout(content_layout, 1)

        # Rechter Bereich: Aktionen untereinander
        button_layout = QVBoxLayout()
        button_layout.setSpacing(8)

        new_company_button = QPushButton(
            "Neue Buchhaltung anlegen"
        )
        new_company_button.clicked.connect(
            self._create_new_company
        )
        button_layout.addWidget(new_company_button)

        self._import_company_button = QPushButton(
            "Mandant importieren …"
        )
        self._import_company_button.setEnabled(
            self._import_client_transfer is not None
        )
        self._import_company_button.clicked.connect(
            self._import_company
        )
        button_layout.addWidget(
            self._import_company_button
        )

        self._delete_company_button = QPushButton("Mandant vollständig löschen …")
        self._delete_company_button.clicked.connect(self._delete_company)
        button_layout.addWidget(self._delete_company_button)

        self._new_fiscal_year_button = QPushButton(
            "Neues Geschäftsjahr"
        )
        self._new_fiscal_year_button.clicked.connect(
            self._create_new_fiscal_year
        )
        button_layout.addWidget(
            self._new_fiscal_year_button
        )

        database_button = QPushButton(
            "Datenbank wechseln …"
        )
        database_button.clicked.connect(
            self._change_database
        )
        button_layout.addWidget(database_button)

        refresh_button = QPushButton("Aktualisieren")
        refresh_button.clicked.connect(
            self._load_companies
        )
        button_layout.addWidget(refresh_button)

        button_layout.addStretch()

        self._open_button = QPushButton("Öffnen")
        self._open_button.setEnabled(False)
        self._open_button.clicked.connect(self._open)
        button_layout.addWidget(self._open_button)

        cancel_button = QPushButton("Abbrechen")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        main_layout.addLayout(button_layout)

    def _load_companies(self) -> None:
        """Lädt die Mandanten und erhält möglichst die Auswahl."""

        selected_company = self._selected_company()
        selected_company_id = (
            selected_company.company_id
            if selected_company is not None
            else None
        )

        self._companies = self._repository.list_companies()

        self._company_box.blockSignals(True)
        self._company_box.clear()
        for company in self._companies:
            self._company_box.addItem(company.name, company)

        selected_index = 0

        if selected_company_id is not None:
            for index, company in enumerate(self._companies):
                if company.company_id == selected_company_id:
                    selected_index = index
                    break

        if self._companies:
            self._company_box.setCurrentIndex(
                selected_index
            )

        self._company_box.blockSignals(False)
        self._delete_company_button.setEnabled(
            bool(self._companies) and self._delete_client is not None
        )

        if not self._companies:
            self._status_label.setText(
                "Es ist noch keine Buchhaltung vorhanden."
            )
            self._fiscal_year_box.clear()
            self._fiscal_year_by_display_name = {}
            self._new_fiscal_year_button.setEnabled(False)
            self._open_button.setEnabled(False)
            return

        self._new_fiscal_year_button.setEnabled(True)
        self._load_fiscal_years(
            self._companies[selected_index]
        )

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

        return self._company_box.currentData()

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

    def _import_company(self) -> None:
        """Importiert eine portable SimpleOB-Mandantensicherung."""

        if self._import_client_transfer is None:
            return

        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Mandant importieren",
            "",
            "SimpleOB-Mandantensicherung (*.simpleob)",
        )

        if not filename:
            return

        try:
            transfer = read_client_transfer_archive(
                filename
            )
            self._import_client_transfer(
                transfer
            )
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Mandant importieren",
                "Der Mandant konnte nicht importiert werden.\n\n"
                f"{exc}",
            )
            return

        self._load_companies()

        imported_company_id = transfer.client.company_id

        for index in range(
            self._company_box.count()
        ):
            company = self._company_box.itemData(index)

            if (
                company is not None
                and company.company_id == imported_company_id
            ):
                self._company_box.setCurrentIndex(
                    index
                )
                break

        QMessageBox.information(
            self,
            "Mandant importieren",
            "Der Mandant wurde erfolgreich importiert.",
        )

    def _delete_company(self) -> None:
        """Sichert und löscht ausschließlich den per UUID ausgewählten Mandanten."""
        company = self._selected_company()
        if company is None or self._delete_client is None:
            return
        directory = QFileDialog.getExistingDirectory(
            self, "Ordner für die Mandantensicherung"
        )
        if not directory:
            return
        backup_path = Path(directory).absolute() / client_backup_filename(company.name)
        name, accepted = QInputDialog.getText(
            self,
            "Mandant vollständig löschen",
            f"Mandant: {company.name}\nID: {company.company_id}\n\n"
            "Alle Geschäftsjahre und zugehörigen Daten werden unwiderruflich gelöscht.\n"
            f"Die Sicherung wird zuvor erstellt und geprüft:\n{backup_path}\n\n"
            "Geben Sie zur Bestätigung den vollständigen Mandantennamen ein:",
        )
        if not accepted:
            return
        if name != company.name:
            QMessageBox.warning(
                self, "Mandant löschen", "Der Mandantenname stimmt nicht überein."
            )
            return
        self.setEnabled(False)
        try:
            self._delete_client(company, backup_path)
        except ClientDeletionCommitUnknown as exc:
            QMessageBox.critical(self, "Löschstatus unbestimmt", str(exc))
            # Keine erneute Aktion auf möglicherweise veraltetem Bestand erlauben.
            self.reject()
            return
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Mandant löschen",
                "Die Löschung wurde nicht abgeschlossen.\n"
                "Eine bereits erstellte Sicherung bleibt erhalten.\n"
                f"Sicherungspfad: {backup_path}\n\n{exc}",
            )
        else:
            self.result = None
            self.opening_transfer_request = None
            try:
                self._load_companies()
            except Exception as exc:
                QMessageBox.critical(
                    self,
                    "Mandant gelöscht – Auswahl nicht verfügbar",
                    f"Die Löschung wurde bestätigt. Sicherung: {backup_path}\n\n"
                    f"Die Mandantenliste konnte nicht geladen werden: {exc}\n"
                    "Bitte starten Sie SimpleOB erneut.",
                )
                self.reject()
                return
            QMessageBox.information(
                self,
                "Mandant gelöscht",
                f"Der Mandant wurde vollständig gelöscht.\n\nSicherung: {backup_path}",
            )
        finally:
            self.setEnabled(True)

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

    def _create_new_fiscal_year(self) -> None:
        """Legt für das ausgewählte Unternehmen ein Geschäftsjahr an."""

        company = self._selected_company()

        if company is None:
            return

        dialog = NewFiscalYearDialog(
            self,
            repository=self._repository,
            company=company,
        )

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        if dialog.result is None:
            return

        fiscal_year = dialog.result

        if dialog.requested_opening_source is not None:
            self.opening_transfer_request = (
                fiscal_year,
                dialog.requested_opening_source,
            )

        self.result = ApplicationContext(
            company=company,
            fiscal_year=fiscal_year,
        )

        self.accept()

    def _change_database(self) -> None:
        """Wechselt die Datenbank nach Prüfung und Bestätigung."""

        dialog = DatabaseConfigurationDialog(
            config=self._config
        )

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        selected_url = dialog.selected_database_url

        if (
            selected_url
            == self._config.database_url_override
        ):
            return

        try:
            save_database_configuration(
                self._config,
                selected_url,
            )
        except (OSError, ValueError) as exc:
            QMessageBox.warning(
                self,
                "Datenbankwechsel",
                "Die Datenbankkonfiguration konnte "
                f"nicht gespeichert werden:\n\n{exc}",
            )
            return

        QMessageBox.information(
            self,
            "Datenbankwechsel",
            "Die neue Datenbankverbindung wurde gespeichert.\n\n"
            "SimpleOB wird jetzt beendet. "
            "Bitte starten Sie die Anwendung erneut.",
        )

        self.reject()

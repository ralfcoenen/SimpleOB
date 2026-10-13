"""PySide6-Dialog zur Auswahl der SimpleOB-Datenbank."""

from __future__ import annotations

from dataclasses import replace

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)
from sqlalchemy.engine import URL, make_url

from openbilanz.core.config import ApplicationConfig
from openbilanz.database.migration_service import (
    DatabaseMigrationService,
)
from openbilanz.database.connection_credentials import (
    PostgreSQLCredentials,
)
from openbilanz.ui_qt.postgresql_password_dialog import (
    PostgreSQLPasswordDialog,
)

class DatabaseConfigurationDialog(QDialog):
    """Wählt und prüft eine Datenbankverbindung."""

    def __init__(
        self,
        *,
        config: ApplicationConfig,
    ) -> None:
        super().__init__()

        self._config = config
        self.selected_database_url: str | None = None

        self._checked_database_url: str | None = None
        self._checked_credentials: PostgreSQLCredentials | None = None

        self.setWindowTitle(
            "SimpleOB – Datenbank konfigurieren"
        )
        self.setMinimumWidth(480)

        self._create_ui()
        self._load_current_configuration()

    @property
    def checked_credentials(
        self,
    ) -> PostgreSQLCredentials | None:
        """Liefert die erfolgreich geprüften PostgreSQL-Zugangsdaten."""

        return self._checked_credentials

    def _create_ui(self) -> None:
        layout = QVBoxLayout(self)

        layout.addWidget(
            QLabel("Datenbankverbindung auswählen")
        )

        form = QFormLayout()

        self._backend_box = QComboBox()
        self._backend_box.addItem("SQLite", "sqlite")
        self._backend_box.addItem(
            "PostgreSQL",
            "postgresql",
        )
        self._backend_box.currentIndexChanged.connect(
            self._update_fields
        )
        form.addRow(
            "Datenbanksystem",
            self._backend_box,
        )

        self._host_edit = QLineEdit()
        self._port_edit = QLineEdit()
        self._user_edit = QLineEdit()
        self._database_edit = QLineEdit()

        form.addRow("Server", self._host_edit)
        form.addRow("Port", self._port_edit)
        form.addRow("Benutzer", self._user_edit)
        form.addRow("Datenbank", self._database_edit)

        layout.addLayout(form)

        self._status_label = QLabel()
        layout.addWidget(self._status_label)

        buttons = QHBoxLayout()

        self._test_button = QPushButton(
            "Verbindung prüfen"
        )
        self._test_button.clicked.connect(
            self._test_connection
        )
        buttons.addWidget(self._test_button)

        buttons.addStretch()

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(
            self._accept_configuration
        )
        button_box.rejected.connect(self.reject)

        buttons.addWidget(button_box)
        layout.addLayout(buttons)

    def _load_current_configuration(self) -> None:
        database_url = make_url(
            self._config.database_url
        )

        if database_url.get_backend_name() == "postgresql":
            self._backend_box.setCurrentIndex(1)

            self._host_edit.setText(
                database_url.host or "localhost"
            )
            self._port_edit.setText(
                str(database_url.port or 5432)
            )
            self._user_edit.setText(
                database_url.username or ""
            )
            self._database_edit.setText(
                database_url.database or ""
            )
        else:
            self._backend_box.setCurrentIndex(0)

        self._update_fields()

    def _update_fields(self) -> None:
        is_postgresql = (
            self._backend_box.currentData()
            == "postgresql"
        )

        for widget in (
            self._host_edit,
            self._port_edit,
            self._user_edit,
            self._database_edit,
        ):
            widget.setEnabled(is_postgresql)

        self._checked_database_url = None
        self._checked_credentials = None
        self._status_label.clear()

    def _selected_url(self) -> str | None:
        if self._backend_box.currentData() == "sqlite":
            return None

        host = self._host_edit.text().strip()
        user = self._user_edit.text().strip()
        database = self._database_edit.text().strip()
        port_text = self._port_edit.text().strip()

        if not host or not user or not database:
            raise ValueError(
                "Server, Benutzer und Datenbankname "
                "müssen angegeben werden."
            )

        try:
            port = int(port_text)
        except ValueError as exc:
            raise ValueError(
                "Der Port muss eine Zahl sein."
            ) from exc

        if not 1 <= port <= 65535:
            raise ValueError(
                "Der Port muss zwischen 1 und 65535 liegen."
            )

        return URL.create(
            drivername="postgresql+psycopg",
            username=user,
            host=host,
            port=port,
            database=database,
        ).render_as_string(hide_password=False)

    def _check_connection(self) -> str | None:
        database_url = self._selected_url()

        if database_url is None:
            self._checked_database_url = None
            self._checked_credentials = None
            return None

        if (
            database_url == self._checked_database_url
            and self._checked_credentials is not None
        ):
            return database_url

        self._checked_database_url = None
        self._checked_credentials = None

        credentials = self._request_credentials(
            database_url
        )

        if credentials is None:
            raise RuntimeError(
                "Die Passwortabfrage wurde abgebrochen."
            )

        test_config = replace(
            self._config,
            database_url_override=database_url,
        )

        DatabaseMigrationService(
            application_config=test_config,
            credentials=credentials,
        ).check_ready_for_start()

        self._checked_database_url = database_url
        self._checked_credentials = credentials

        return database_url

    def _test_connection(self) -> None:
        try:
            self._check_connection()
        except Exception as exc:
            self._status_label.setText(
                "Verbindungsprüfung fehlgeschlagen."
            )
            QMessageBox.warning(
                self,
                "Datenbankverbindung",
                str(exc),
            )
            return

        self._status_label.setText(
            "Datenbankprüfung erfolgreich."
        )

    def _accept_configuration(self) -> None:
        try:
            database_url = self._check_connection()
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Datenbankverbindung",
                str(exc),
            )
            return

        self.selected_database_url = database_url
        self.accept()

    def _request_credentials(
        self,
        database_url: str,
    ) -> PostgreSQLCredentials | None:
        url = make_url(database_url)

        dialog = PostgreSQLPasswordDialog(
            username=url.username or "",
            host=url.host or "",
            database=url.database or "",
            parent=self,
        )

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None

        return PostgreSQLCredentials(
            password=dialog.password,
        )

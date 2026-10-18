
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

from simpleob.core.config import ApplicationConfig
from simpleob.database.connection_credentials import (
    PostgreSQLCredentials,
)
from simpleob.database.migration_service import (
    DatabaseMigrationService,
)
from simpleob.database.postgresql_initialization_service import (
    PostgreSQLInitializationService,
)
from simpleob.ui_qt.postgresql_password_dialog import (
    PostgreSQLPasswordDialog,
)


class DatabaseConfigurationDialog(QDialog):
    """Wählt, prüft und gegebenenfalls initialisiert eine Datenbank."""

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

        for edit in (
            self._host_edit,
            self._port_edit,
            self._user_edit,
            self._database_edit,
        ):
            edit.textChanged.connect(
                self._invalidate_connection_check
            )

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

        self._initialize_button = QPushButton(
            "Neue PostgreSQL-Datenbank anlegen …"
        )
        self._initialize_button.clicked.connect(
            self._initialize_postgresql_database
        )
        buttons.addWidget(self._initialize_button)

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

    def _invalidate_connection_check(self) -> None:
        self._checked_database_url = None
        self._checked_credentials = None
        self._status_label.clear()

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

        self._initialize_button.setEnabled(
            is_postgresql
        )

        self._invalidate_connection_check()

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

    def _initialize_postgresql_database(self) -> None:
        try:
            database_url = self._selected_url()
        except ValueError as exc:
            QMessageBox.warning(
                self,
                "PostgreSQL-Ersteinrichtung",
                str(exc),
            )
            return

        if database_url is None:
            return

        target_url = make_url(database_url)
        database_name = target_url.database or ""
        owner_role = target_url.username or ""

        answer = QMessageBox.question(
            self,
            "Neue PostgreSQL-Datenbank anlegen",
            (
                "Soll die folgende neue PostgreSQL-Datenbank "
                "angelegt und initialisiert werden?\n\n"
                f"Datenbank: {database_name}\n"
                f"Eigentümer: {owner_role}\n"
                f"Server: {target_url.host}:{target_url.port}\n\n"
                "Eine bereits vorhandene Datenbank wird "
                "nicht überschrieben.\n\n"
                "Die Anlage erfordert eine administrative "
                "PostgreSQL-Rolle mit CREATEDB-Berechtigung."
            ),
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if answer != QMessageBox.StandardButton.Yes:
            return

        admin_username, accepted = self._request_admin_username()
        if not accepted:
            return

        admin_username = admin_username.strip()
        if not admin_username:
            QMessageBox.warning(
                self,
                "PostgreSQL-Ersteinrichtung",
                "Die administrative Rolle darf nicht leer sein.",
            )
            return

        admin_url = target_url.set(
            username=admin_username,
            database="postgres",
        ).render_as_string(hide_password=False)

        admin_credentials = self._request_credentials(
            admin_url
        )
        if admin_credentials is None:
            return

        application_credentials = self._request_credentials(
            database_url
        )
        if application_credentials is None:
            return

        self._invalidate_connection_check()

        test_config = replace(
            self._config,
            database_url_override=database_url,
        )

        try:
            PostgreSQLInitializationService().initialize_database(
                application_config=test_config,
                admin_username=admin_username,
                admin_credentials=admin_credentials,
                application_credentials=application_credentials,
                confirmed=True,
            )
        except Exception as exc:
            self._status_label.setText(
                "PostgreSQL-Ersteinrichtung fehlgeschlagen."
            )
            QMessageBox.warning(
                self,
                "PostgreSQL-Ersteinrichtung",
                str(exc),
            )
            return

        self._checked_database_url = database_url
        self._checked_credentials = application_credentials
        self._status_label.setText(
            "Neue PostgreSQL-Datenbank erfolgreich eingerichtet."
        )

        QMessageBox.information(
            self,
            "PostgreSQL-Ersteinrichtung",
            (
                f"Die Datenbank „{database_name}“ wurde "
                "angelegt und erfolgreich initialisiert.\n\n"
                "Die Konfiguration kann jetzt mit "
                "„OK“ übernommen werden."
            ),
        )

    def _request_admin_username(self) -> tuple[str, bool]:
        from PySide6.QtWidgets import QInputDialog

        return QInputDialog.getText(
            self,
            "Administrative PostgreSQL-Rolle",
            "PostgreSQL-Rolle mit CREATEDB-Berechtigung:",
            QLineEdit.EchoMode.Normal,
            "",
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

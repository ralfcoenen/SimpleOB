
"""PySide6-Dialog zur Auswahl der SimpleOB-Datenbank."""

from __future__ import annotations

from dataclasses import replace

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
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
    PostgreSQLSchemaStatus,
)
from simpleob.database.postgresql_existing_installation_inspector import (
    PostgreSQLExistingInstallationInspector,
    PostgreSQLOwnershipAssessment,
)
from simpleob.database.postgresql_initialization_service import (
    PostgreSQLInitializationService,
)
from simpleob.database.postgresql_role_separation_service import (
    PostgreSQLRoleSeparationService,
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
        configuration_notice: str | None = None,
    ) -> None:
        super().__init__()

        self._config = config
        self._configuration_notice = configuration_notice
        self._configuration_notice_label: QLabel | None = None
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
        if self._configuration_notice is not None:
            self._configuration_notice_label = QLabel(self._configuration_notice)
            self._configuration_notice_label.setWordWrap(True)
            layout.addWidget(self._configuration_notice_label)

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
        self._migration_user_edit = QLineEdit()
        self._database_edit = QLineEdit()

        form.addRow("Server", self._host_edit)
        form.addRow("Port", self._port_edit)
        form.addRow("Benutzer", self._user_edit)
        form.addRow("Migrationsrolle (nur Ersteinrichtung)", self._migration_user_edit)
        form.addRow("Datenbank", self._database_edit)

        for edit in (
            self._host_edit,
            self._port_edit,
            self._user_edit,
            self._migration_user_edit,
            self._database_edit,
        ):
            edit.textChanged.connect(
                self._invalidate_connection_check
            )

        layout.addLayout(form)

        self._user_management_buttons = []
        for label, new_database in (
            ("Neue Datenbank samt neuem Benutzer …", True),
            ("Neuen Benutzer für vorhandene Datenbank anlegen …", False),
        ):
            button = QPushButton(label)
            button.clicked.connect(
                lambda checked=False, new=new_database: self._open_user_management(new)
            )
            self._user_management_buttons.append(button)
            layout.addWidget(button)

        self._separate_roles_button = QPushButton(
            "Bestehende PostgreSQL-Installation auf getrennte Rollen umstellen …"
        )
        self._separate_roles_button.clicked.connect(self._separate_postgresql_roles)
        layout.addWidget(self._separate_roles_button)

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
            self._migration_user_edit,
            self._database_edit,
        ):
            widget.setEnabled(is_postgresql)

        self._initialize_button.setEnabled(
            is_postgresql
        )
        self._separate_roles_button.setEnabled(is_postgresql)
        for button in self._user_management_buttons:
            button.setEnabled(is_postgresql)

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

        migration_service = DatabaseMigrationService(
            application_config=test_config,
            credentials=credentials,
        )
        try:
            migration_service.check_ready_for_start()
        except Exception:
            # Eine bekannte ältere Datenbank darf ausgewählt werden. Der
            # Startablauf hält den Betrieb bis zum bestätigten Upgrade gesperrt.
            inspection = migration_service.inspect_postgresql_schema()
            if inspection.status != PostgreSQLSchemaStatus.OUTDATED:
                raise

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
        operating_role = target_url.username or ""
        migration_role = self._migration_user_edit.text().strip()
        if not migration_role:
            QMessageBox.warning(
                self,
                "PostgreSQL-Ersteinrichtung",
                "Bitte die getrennte Migrationsrolle angeben.",
            )
            return

        answer = QMessageBox.question(
            self,
            "Neue PostgreSQL-Datenbank anlegen",
            (
                "Soll die folgende neue PostgreSQL-Datenbank "
                "angelegt und initialisiert werden?\n\n"
                f"Datenbank: {database_name}\n"
                f"Betriebsrolle: {operating_role}\n"
                f"Migrationsrolle (Datenbank- und Schemaeigentümerin): {migration_role}\n"
                f"Server: {target_url.host}:{target_url.port}\n\n"
                "Eine bereits vorhandene Datenbank wird "
                "nicht überschrieben.\n\n"
                "Je nach vorhandenen Rollenrechten benötigt die Administration "
                "CREATEDB und die Berechtigung zur Übernahme der Migrationsrolle, "
                "oder CREATEROLE zum Entfernen eines nur für die Ersteinrichtung "
                "vergebenen CREATEDB-Rechts. Unter PostgreSQL vor Version 15 kann "
                "zusätzlich Schema-Eigentümerrecht erforderlich sein."
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

        migration_url = target_url.set(
            username=migration_role,
            database=database_name,
        ).render_as_string(hide_password=False)
        migration_credentials = self._request_credentials(migration_url)
        if migration_credentials is None:
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
                migration_username=migration_role,
                migration_credentials=migration_credentials,
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

    def _open_user_management(self, new_database: bool) -> None:
        from simpleob.ui_qt.postgresql_user_dialog import PostgreSQLUserDialog

        try:
            database_url = self._selected_url()
        except ValueError as exc:
            QMessageBox.warning(self, "Benutzerverwaltung", str(exc))
            return
        if database_url is None:
            return
        PostgreSQLUserDialog(
            config=replace(self._config, database_url_override=database_url),
            new_database=new_database, parent=self,
        ).exec()

    def _separate_postgresql_roles(self) -> None:
        try:
            database_url = self._selected_url()
        except ValueError as exc:
            QMessageBox.warning(self, "PostgreSQL-Rollenaufteilung", str(exc))
            return
        if database_url is None:
            return

        owner_url = make_url(database_url)
        owner_credentials = self._request_credentials(database_url)
        if owner_credentials is None:
            return
        owner_config = replace(
            self._config,
            database_url_override=database_url,
        )
        try:
            assessment = PostgreSQLExistingInstallationInspector(
                application_config=owner_config,
                credentials=owner_credentials,
            ).inspect()
        except Exception as exc:
            QMessageBox.warning(
                self,
                "PostgreSQL-Bestandsprüfung",
                str(exc),
            )
            return

        if assessment.ownership_assessment == PostgreSQLOwnershipAssessment.SPLIT_ROLES_COMPATIBLE:
            QMessageBox.information(
                self,
                "PostgreSQL-Rollenaufteilung",
                "Diese Installation verwendet bereits getrennte Rollen. "
                "Es wurden keine Änderungen vorgenommen.",
            )
            return
        if (
            assessment.ownership_assessment
            != PostgreSQLOwnershipAssessment.UNIFORM_OWNERSHIP
            or assessment.operating_role != assessment.migration_role_candidate
            or assessment.database_owner != assessment.migration_role_candidate
            or assessment.schema_status != PostgreSQLSchemaStatus.CURRENT
            or assessment.blockers
        ):
            details = "\n".join(assessment.blockers) or (
                f"Bewertung: {assessment.ownership_assessment.value}; "
                f"Schema: {assessment.schema_status.value}."
            )
            QMessageBox.warning(
                self,
                "PostgreSQL-Rollenaufteilung nicht möglich",
                "Die Bestandsprüfung bestätigt keine einheitliche, aktuelle "
                "SimpleOB-Eigentümerschaft. Es wurden keine Änderungen vorgenommen.\n\n"
                + details,
            )
            return

        role_choices = (
            "Neue Betriebsrolle anlegen",
            "Vorhandene Betriebsrolle verwenden",
        )
        role_choice, accepted = QInputDialog.getItem(
            self,
            "Betriebsrolle auswählen",
            "Wie soll die neue Betriebsrolle bereitgestellt werden?",
            role_choices,
            0,
            False,
        )
        if not accepted:
            return
        create_role = role_choice == role_choices[0]
        operating_username, accepted = QInputDialog.getText(
            self,
            "Betriebsrolle",
            "Name der künftigen Betriebsrolle:",
            QLineEdit.EchoMode.Normal,
            "simpleob_app",
        )
        if not accepted:
            return
        operating_username = operating_username.strip()
        if not operating_username:
            QMessageBox.warning(
                self,
                "PostgreSQL-Rollenaufteilung",
                "Der Name der Betriebsrolle darf nicht leer sein.",
            )
            return

        owner_role = assessment.migration_role_candidate or owner_url.username or ""
        if operating_username == owner_role:
            QMessageBox.warning(
                self,
                "PostgreSQL-Rollenaufteilung",
                "Betriebs- und Migrationsrolle müssen verschieden sein.",
            )
            return
        answer = QMessageBox.question(
            self,
            "Rollenaufteilung ausdrücklich bestätigen",
            (
                "Die Installation wird auf getrennte PostgreSQL-Rollen umgestellt.\n\n"
                f"Bisherige Eigentümerin und künftige Migrationsrolle: {owner_role}\n"
                f"Künftige Betriebsrolle: {operating_username}\n"
                f"Datenbank: {assessment.database_name}\n\n"
                "Die vorhandenen Tabellen, Sequenzen und Buchungsdaten behalten "
                "ihre Eigentümerschaft. Die Betriebsrolle erhält nur die für den "
                "Anwendungsbetrieb nötigen Rechte. Es werden keine Migrationen "
                "ausgeführt. Die Anwendungskonfiguration wird erst nach "
                "erfolgreicher Rechte- und Verbindungsprüfung auf die Betriebsrolle "
                "umgestellt. Die Migrationsrolle bleibt für spätere, separat "
                "bestätigte Upgrades erforderlich."
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        operating_url = owner_url.set(username=operating_username).render_as_string(
            hide_password=True
        )
        operating_credentials = self._request_credentials(operating_url)
        if operating_credentials is None:
            return

        admin_username = None
        admin_credentials = None
        if create_role:
            admin_username, accepted = self._request_admin_username()
            if not accepted or not admin_username.strip():
                return
            admin_username = admin_username.strip()
            admin_url = owner_url.set(
                username=admin_username,
                database=owner_url.database,
            ).render_as_string(hide_password=True)
            admin_credentials = self._request_credentials(admin_url)
            if admin_credentials is None:
                return

        self._invalidate_connection_check()
        try:
            result = PostgreSQLRoleSeparationService().separate_roles(
                application_config=owner_config,
                owner_credentials=owner_credentials,
                operating_username=operating_username,
                operating_credentials=operating_credentials,
                create_operating_role=create_role,
                admin_username=admin_username,
                admin_credentials=admin_credentials,
                confirmed=True,
            )
        except Exception as exc:
            QMessageBox.warning(
                self,
                "PostgreSQL-Rollenaufteilung fehlgeschlagen",
                str(exc),
            )
            return

        self._user_edit.setText(result.operating_role)
        self._checked_database_url = result.database_url
        self._checked_credentials = operating_credentials
        self._status_label.setText(
            "Getrennte PostgreSQL-Rollen wurden geprüft. Betriebsrolle ist ausgewählt."
        )
        QMessageBox.information(
            self,
            "PostgreSQL-Rollenaufteilung erfolgreich",
            (
                f"Betriebsrolle: {result.operating_role}\n"
                f"Migrationsrolle und bisherige Eigentümerin: {result.migration_role}\n\n"
                "Die Auswahl wird erst dauerhaft gespeichert, wenn Sie diesen "
                "Datenbankdialog mit „OK“ abschließen. Passwörter werden nicht "
                "in der Konfiguration gespeichert."
            ),
        )

    def _request_admin_username(self) -> tuple[str, bool]:
        from PySide6.QtWidgets import QInputDialog

        return QInputDialog.getText(
            self,
            "Administrative PostgreSQL-Rolle",
            "Administrationsrolle mit erforderlichen Datenbank- oder "
            "Rollenverwaltungsrechten:",
            QLineEdit.EchoMode.Normal,
            "",
        )

    def _accept_configuration(self) -> None:
        if self._configuration_notice is not None:
            try:
                selected_url = self._selected_url()
            except ValueError as exc:
                QMessageBox.warning(
                    self,
                    "Datenbankverbindung",
                    str(exc),
                )
                return

            if selected_url is None:
                database_target = f"SQLite-Datei: {self._config.database_file}\n" + (
                    "Die Datei ist bereits vorhanden."
                    if self._config.database_file.is_file()
                    else "Die Datei ist noch nicht vorhanden und kann erst nach Ihrer Auswahl angelegt werden."
                )
            else:
                url = make_url(selected_url)
                database_target = (
                    f"PostgreSQL-Datenbank: {url.database or '(ohne Namen)'}\n"
                    f"Server: {url.host or '(ohne Server)'}:{url.port or 5432}\n"
                    f"Betriebsrolle: {url.username or '(ohne Benutzer)'}"
                )
            answer = QMessageBox.question(
                self,
                "Datenbankauswahl bestätigen",
                f"Soll SimpleOB diese Datenbankauswahl verwenden?\n\n"
                f"{database_target}\n\n"
                "Die Konfiguration wird erst gespeichert, nachdem die "
                "Datenbankprüfung beim Programmstart erfolgreich war. Bei "
                "Abbruch bleibt die vorhandene Konfigurationsdatei unverändert.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return

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

"""Separater Verwaltungsdialog für zusätzliche PostgreSQL-Benutzer."""

from dataclasses import replace

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
)
from sqlalchemy.engine import make_url

from simpleob.database.connection_credentials import PostgreSQLCredentials
from simpleob.database.postgresql_user_service import PostgreSQLUserService


class PostgreSQLUserDialog(QDialog):
    def __init__(self, *, config, new_database, parent=None):
        super().__init__(parent)
        self._config = config
        self._new_database = new_database
        self.setWindowTitle(
            "Neue Datenbank samt Benutzer"
            if new_database
            else "Neuer Benutzer für vorhandene Datenbank"
        )
        layout = QVBoxLayout(self)
        description = QLabel(
            "Geben Sie die ausdrücklich bereitgestellte Administrationsrolle und "
            "die Zugangsdaten für die neuen Rollen ein. Vorhandene Benutzer werden "
            "nicht verändert. Bei einer neuen Datenbank werden Betriebs- und "
            "Migrationsrolle getrennt angelegt. Die Migrationsrolle erhält "
            "CREATEDB nur vorübergehend für die Datenbankanlage; SimpleOB entzieht "
            "dieses Recht vor den Migrationen wieder."
        )
        description.setWordWrap(True)
        layout.addWidget(description)
        url = make_url(config.database_url)
        form = QFormLayout()
        form.addRow("Server", QLabel(f"{url.host}:{url.port}"))
        form.addRow("Datenbank", QLabel(url.database))
        self._username = QLineEdit(url.username or "")
        self._password = QLineEdit()
        self._repeat = QLineEdit()
        self._migration_username = QLineEdit("simpleob_migrator")
        self._migration_password = QLineEdit()
        self._migration_repeat = QLineEdit()
        self._admin_username = QLineEdit()
        self._admin_password = QLineEdit()
        form.addRow("Neuer Benutzer", self._username)
        for label, edit in (
            ("Neues Passwort", self._password),
            ("Passwort wiederholen", self._repeat),
        ):
            edit.setEchoMode(QLineEdit.EchoMode.Password)
            form.addRow(label, edit)
        if new_database:
            form.addRow("Neue Migrationsrolle", self._migration_username)
            for label, edit in (
                ("Passwort der Migrationsrolle", self._migration_password),
                ("Passwort wiederholen", self._migration_repeat),
            ):
                edit.setEchoMode(QLineEdit.EchoMode.Password)
                form.addRow(label, edit)
        form.addRow("Administrationsrolle", self._admin_username)
        form.addRow("Passwort der Administrationsrolle", self._admin_password)
        self._admin_password.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addLayout(form)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Anlegen …")
        buttons.accepted.connect(self._create_user)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def done(self, result):
        self._password.clear()
        self._repeat.clear()
        self._migration_password.clear()
        self._migration_repeat.clear()
        self._admin_password.clear()
        super().done(result)

    def _create_user(self):
        username = self._username.text().strip()
        if (
            not username
            or not self._password.text()
            or not self._admin_username.text().strip()
            or not self._admin_password.text()
        ):
            QMessageBox.warning(
                self,
                "Benutzeranlage",
                "Betriebsrolle, Administrationsrolle und die zugehörigen Passwörter sind erforderlich.",
            )
            return
        if self._password.text() != self._repeat.text():
            QMessageBox.warning(
                self, "Benutzeranlage", "Die Passwörter stimmen nicht überein."
            )
            return
        if self._new_database and (
            not self._migration_username.text().strip()
            or not self._migration_password.text()
        ):
            QMessageBox.warning(
                self,
                "Benutzeranlage",
                "Migrationsrolle und Passwort sind erforderlich.",
            )
            return
        if (
            self._new_database
            and self._migration_password.text() != self._migration_repeat.text()
        ):
            QMessageBox.warning(
                self,
                "Benutzeranlage",
                "Die Passwörter der Migrationsrolle stimmen nicht überein.",
            )
            return
        url = make_url(self._config.database_url).set(username=username)
        action = (
            "Datenbank samt Benutzer anlegen"
            if self._new_database
            else "Benutzer anlegen und Zugriff erteilen"
        )
        if (
            QMessageBox.question(
                self,
                "Benutzeranlage bestätigen",
                f"{action}?\n\nServer: {url.host}:{url.port}\n"
                f"Datenbank: {url.database}\nBetriebsrolle: {username}\n"
                f"Migrationsrolle: {self._migration_username.text().strip() if self._new_database else 'nicht betroffen'}\n"
                f"Administrationsrolle: {self._admin_username.text().strip()}",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            != QMessageBox.StandardButton.Yes
        ):
            return
        try:
            PostgreSQLUserService().create_user(
                application_config=replace(
                    self._config, database_url_override=str(url)
                ),
                admin_username=self._admin_username.text().strip(),
                admin_credentials=PostgreSQLCredentials(self._admin_password.text()),
                application_credentials=PostgreSQLCredentials(self._password.text()),
                migration_username=(
                    self._migration_username.text().strip()
                    if self._new_database
                    else None
                ),
                migration_credentials=(
                    PostgreSQLCredentials(self._migration_password.text())
                    if self._new_database
                    else None
                ),
                new_database=self._new_database,
                confirmed=True,
            )
        except Exception as exc:
            QMessageBox.warning(self, "Benutzeranlage", str(exc))
            return
        finally:
            self._admin_password.clear()
            self._migration_password.clear()
            self._migration_repeat.clear()
            self._password.clear()
            self._repeat.clear()
        QMessageBox.information(
            self,
            "Benutzeranlage",
            f"Der Benutzer „{username}“ wurde eingerichtet und geprüft.\n\n"
            "Tragen Sie ihn bei Bedarf im Feld Benutzer der Datenbankkonfiguration "
            "ein und verwenden Sie die bestehende Verbindungsprüfung.",
        )
        self.accept()

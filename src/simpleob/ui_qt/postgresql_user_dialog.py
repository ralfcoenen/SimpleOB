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
            "Die Einrichtung erfolgt über postgres. Geben Sie einen neuen "
            "Benutzernamen und dessen Passwort ein.\n"
            "Vorhandene Benutzer werden nicht verändert."
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
        self._admin_password = QLineEdit()
        form.addRow("Neuer Benutzer", self._username)
        for label, edit in (
            ("Neues Passwort", self._password),
            ("Passwort wiederholen", self._repeat),
            ("Passwort von postgres", self._admin_password),
        ):
            edit.setEchoMode(QLineEdit.EchoMode.Password)
            form.addRow(label, edit)
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
        self._admin_password.clear()
        super().done(result)

    def _create_user(self):
        username = self._username.text().strip()
        if not username or not self._password.text():
            QMessageBox.warning(
                self, "Benutzeranlage", "Benutzername und Passwort fehlen."
            )
            return
        if self._password.text() != self._repeat.text():
            QMessageBox.warning(
                self, "Benutzeranlage", "Die Passwörter stimmen nicht überein."
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
                f"Datenbank: {url.database}\nBenutzer: {username}",
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
                admin_credentials=PostgreSQLCredentials(self._admin_password.text()),
                application_credentials=PostgreSQLCredentials(self._password.text()),
                new_database=self._new_database,
                confirmed=True,
            )
        except Exception as exc:
            QMessageBox.warning(self, "Benutzeranlage", str(exc))
            return
        finally:
            self._admin_password.clear()
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

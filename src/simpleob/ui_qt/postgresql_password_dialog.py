"""Passwortabfrage für die PostgreSQL-Anmeldung."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)


class PostgreSQLPasswordDialog(QDialog):
    """Fragt das PostgreSQL-Passwort für die laufende Sitzung ab."""

    def __init__(
        self,
        *,
        username: str,
        host: str,
        database: str,
        parent=None,
    ) -> None:
        super().__init__(parent)

        self.setWindowTitle("SimpleOB – PostgreSQL-Anmeldung")

        layout = QVBoxLayout(self)

        layout.addWidget(
            QLabel(
                "Bitte geben Sie Ihr persönliches "
                "PostgreSQL-Passwort ein."
            )
        )

        form = QFormLayout()

        form.addRow("Server:", QLabel(host))
        form.addRow("Datenbank:", QLabel(database))
        form.addRow("Benutzer:", QLabel(username))

        self._password_edit = QLineEdit()
        self._password_edit.setEchoMode(
            QLineEdit.EchoMode.Password
        )
        form.addRow("Passwort:", self._password_edit)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )

        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout.addWidget(buttons)

        self._password_edit.setFocus()

    @property
    def password(self) -> str:
        return self._password_edit.text()

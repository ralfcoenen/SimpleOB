"""Dialog zur Kenntnisnahme der ERiC-Datenschutzinformationen."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
)


class EricPrivacyDialog(QDialog):
    """Zeigt die vorgeschriebenen Datenschutzinformationen."""

    def __init__(
        self,
        *,
        privacy_notice_file: Path,
        privacy_information_file: Path,
    ) -> None:
        super().__init__()

        self.setWindowTitle(
            "SimpleOB – Datenschutzinformationen"
        )
        self.resize(850, 720)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            24,
            24,
            24,
            24,
        )
        layout.setSpacing(12)

        title_label = QLabel(
            "Datenschutzinformationen der Finanzverwaltung"
        )
        title_label.setStyleSheet(
            "font-size: 18px; font-weight: bold;"
        )
        layout.addWidget(title_label)

        introduction_label = QLabel(
            "SimpleOB verwendet ERiC zur elektronischen "
            "Übermittlung von Steuerdaten. Vor der Nutzung "
            "sind die folgenden Datenschutzinformationen "
            "der Finanzverwaltung zur Kenntnis zu nehmen."
        )
        introduction_label.setWordWrap(True)
        layout.addWidget(introduction_label)

        privacy_notice = QTextBrowser()
        privacy_notice.setPlainText(
            privacy_notice_file.read_text(
                encoding="utf-8"
            )
        )
        privacy_notice.setMaximumHeight(210)
        layout.addWidget(privacy_notice)

        information_label = QLabel(
            "Allgemeine Datenschutzinformationen "
            "der Steuerverwaltung:"
        )
        information_label.setStyleSheet(
            "font-weight: bold;"
        )
        layout.addWidget(information_label)

        privacy_information = QTextBrowser()
        privacy_information.setPlainText(
            privacy_information_file.read_text(
                encoding="utf-8"
            )
        )
        layout.addWidget(privacy_information)

        self._acknowledgement_box = QCheckBox(
            "Ich habe die vorstehenden "
            "Datenschutzinformationen zur Kenntnis genommen."
        )
        self._acknowledgement_box.setChecked(False)
        self._acknowledgement_box.stateChanged.connect(
            self._update_accept_button
        )
        layout.addWidget(
            self._acknowledgement_box
        )

        button_box = QDialogButtonBox()

        self._accept_button = QPushButton(
            "Bestätigen und fortfahren"
        )
        self._accept_button.setEnabled(False)
        self._accept_button.clicked.connect(
            self.accept
        )
        button_box.addButton(
            self._accept_button,
            QDialogButtonBox.ButtonRole.AcceptRole,
        )

        cancel_button = QPushButton(
            "SimpleOB beenden"
        )
        cancel_button.clicked.connect(
            self.reject
        )
        button_box.addButton(
            cancel_button,
            QDialogButtonBox.ButtonRole.RejectRole,
        )

        layout.addWidget(button_box)

    def _update_accept_button(
        self,
        _state: int,
    ) -> None:
        """Aktiviert die Fortsetzung erst nach Kenntnisnahme."""

        self._accept_button.setEnabled(
            self._acknowledgement_box.isChecked()
        )

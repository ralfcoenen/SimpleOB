"""Informationen zu ERiC, Datenschutz und Datensicherung."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
)


class EricInformationDialog(QDialog):
    """Zeigt dauerhaft erreichbare Informationen zu ERiC an."""

    def __init__(
        self,
        *,
        privacy_notice_file: Path,
        privacy_information_file: Path,
        parent=None,
    ) -> None:
        super().__init__(parent)

        self._privacy_notice_file = privacy_notice_file
        self._privacy_information_file = privacy_information_file

        self.setWindowTitle(
            "SimpleOB – Datenschutz und ERiC-Hinweise"
        )
        self.resize(760, 560)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            24,
            24,
            24,
            24,
        )
        layout.setSpacing(14)

        title_label = QLabel(
            "Datenschutz und ERiC-Hinweise"
        )
        title_label.setStyleSheet(
            "font-size: 18px; font-weight: bold;"
        )
        layout.addWidget(title_label)

        information = QTextBrowser()
        information.setPlainText(
            "ERiC-Protokolldateien\n\n"
            "Bei der Nutzung von ERiC werden Protokolldateien "
            "erstellt und lokal auf Ihrem Computer gespeichert. "
            "Diese Protokolldateien verbleiben grundsätzlich auf "
            "Ihrem Computer. SimpleOB übermittelt sie nicht "
            "automatisch an den Hersteller oder an die "
            "Finanzverwaltung.\n\n"
            "In einem Supportfall dürfen Protokolldateien nur "
            "nach Ihrer ausdrücklichen Erlaubnis weitergegeben "
            "werden. Eine Weiterleitung an die Finanzverwaltung "
            "erfolgt ebenfalls nur nach Ihrer ausdrücklichen "
            "Erlaubnis.\n\n"
            "Datensicherung\n\n"
            "Die mit SimpleOB verwalteten Daten enthalten "
            "geschäftliche und steuerlich relevante "
            "Informationen. Erstellen Sie deshalb regelmäßig "
            "geeignete Datensicherungen und bewahren Sie diese "
            "an einem sicheren Ort auf."
        )
        layout.addWidget(information)

        privacy_button = QPushButton(
            "Datenschutzinformationen der Finanzverwaltung anzeigen"
        )
        privacy_button.clicked.connect(
            self._show_privacy_information
        )
        layout.addWidget(privacy_button)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Close
        )
        button_box.rejected.connect(
            self.reject
        )
        layout.addWidget(button_box)

    def _show_privacy_information(self) -> None:
        """Zeigt die amtlichen Datenschutzinformationen."""

        dialog = QDialog(self)
        dialog.setWindowTitle(
            "Datenschutzinformationen der Finanzverwaltung"
        )
        dialog.resize(850, 720)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(
            24,
            24,
            24,
            24,
        )
        layout.setSpacing(12)

        notice = QTextBrowser()
        notice.setPlainText(
            self._privacy_notice_file.read_text(
                encoding="utf-8"
            )
        )
        notice.setMaximumHeight(210)
        layout.addWidget(notice)

        information = QTextBrowser()
        information.setPlainText(
            self._privacy_information_file.read_text(
                encoding="utf-8"
            )
        )
        layout.addWidget(information)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Close
        )
        button_box.rejected.connect(
            dialog.reject
        )
        layout.addWidget(button_box)

        dialog.exec()

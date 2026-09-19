"""PySide6-Arbeitsbereich für die E-Bilanz."""

from collections.abc import Callable

from PySide6.QtWidgets import (
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class EBilanzFrame(QWidget):
    """Bedienelemente für Vorbereitung und Erzeugung der E-Bilanz."""

    def __init__(
        self,
        *,
        on_install_taxonomy: Callable[[], None],
        on_save_bvv: Callable[[], None],
        on_prepare: Callable[[], None],
        on_build: Callable[[], None],
        on_validate: Callable[[], None],
        on_export_xbrl: Callable[[], None],
        on_export_pdf: Callable[[], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self)

        title_label = QLabel("E-Bilanz")
        title_label.setStyleSheet(
            "font-size: 18px; font-weight: bold;"
        )
        layout.addWidget(title_label)

        description_label = QLabel(
            "Vorbereitung und Erzeugung der E-Bilanz "
            "für das aktuelle Geschäftsjahr."
        )
        layout.addWidget(description_label)

        self._taxonomy_status_label = QLabel("")
        self._taxonomy_status_label.setWordWrap(True)
        layout.addWidget(self._taxonomy_status_label)

        self._install_taxonomy_button = QPushButton(
            "Taxonomie installieren"
        )
        self._install_taxonomy_button.clicked.connect(
            on_install_taxonomy
        )
        self._install_taxonomy_button.setEnabled(False)
        layout.addWidget(
            self._install_taxonomy_button,
            alignment=self._left_alignment(),
        )

        self._status_label = QLabel("")
        self._status_label.setWordWrap(True)
        layout.addWidget(self._status_label)

        bvv_group = QGroupBox("BVV-Jahresdaten")
        bvv_layout = QFormLayout(bvv_group)

        self._effective_previous_hgb_equity_label = QLabel("–")
        bvv_layout.addRow(
            "HGB-Vorjahreseigenkapital",
            self._effective_previous_hgb_equity_label,
        )

        self._previous_hgb_equity_source_label = QLabel("")
        bvv_layout.addRow(
            "Herkunft",
            self._previous_hgb_equity_source_label,
        )

        self._previous_hgb_equity_override_edit = QLineEdit()
        self._previous_hgb_equity_override_edit.setMaximumWidth(180)
        bvv_layout.addRow(
            "Manueller Korrekturwert",
            self._previous_hgb_equity_override_edit,
        )

        hint_label = QLabel(
            "Leer lassen, um den automatisch ermittelten "
            "Wert zu verwenden."
        )
        hint_label.setWordWrap(True)
        bvv_layout.addRow("", hint_label)

        self._contribution_edit = QLineEdit("0,00")
        self._contribution_edit.setMaximumWidth(180)
        bvv_layout.addRow(
            "Einlagen",
            self._contribution_edit,
        )

        self._withdrawal_distribution_edit = QLineEdit("0,00")
        self._withdrawal_distribution_edit.setMaximumWidth(180)
        bvv_layout.addRow(
            "Entnahmen / Ausschüttungen",
            self._withdrawal_distribution_edit,
        )

        save_bvv_button = QPushButton("BVV-Daten speichern")
        save_bvv_button.clicked.connect(on_save_bvv)
        bvv_layout.addRow("", save_bvv_button)

        layout.addWidget(bvv_group)

        actions_widget = QWidget()
        actions_layout = QGridLayout(actions_widget)

        self._prepare_button = QPushButton(
            "E-Bilanz vorbereiten"
        )
        self._prepare_button.clicked.connect(on_prepare)
        actions_layout.addWidget(self._prepare_button, 0, 0)

        self._build_button = QPushButton(
            "E-Bilanz erzeugen"
        )
        self._build_button.clicked.connect(on_build)
        actions_layout.addWidget(self._build_button, 0, 1)

        self._validate_button = QPushButton(
            "E-Bilanz validieren"
        )
        self._validate_button.clicked.connect(on_validate)
        actions_layout.addWidget(self._validate_button, 1, 0)

        self._export_xbrl_button = QPushButton(
            "E-Bilanz XBRL exportieren"
        )
        self._export_xbrl_button.clicked.connect(on_export_xbrl)
        actions_layout.addWidget(self._export_xbrl_button, 1, 1)

        self._export_pdf_button = QPushButton(
            "E-Bilanz PDF exportieren"
        )
        self._export_pdf_button.clicked.connect(on_export_pdf)
        actions_layout.addWidget(self._export_pdf_button, 2, 0)

        layout.addWidget(actions_widget)
        layout.addStretch()

        self._prepare_button.setEnabled(False)
        self._build_button.setEnabled(False)
        self._validate_button.setEnabled(False)
        self._export_xbrl_button.setEnabled(False)
        self._export_pdf_button.setEnabled(False)

    @staticmethod
    def _left_alignment():
        """Liefert die linksbündige Widget-Ausrichtung."""

        from PySide6.QtCore import Qt

        return Qt.AlignmentFlag.AlignLeft

    @property
    def previous_hgb_equity_override(self) -> str:
        """Liefert den eingegebenen manuellen Korrekturwert."""

        return self._previous_hgb_equity_override_edit.text()

    @property
    def contribution(self) -> str:
        """Liefert die eingegebenen Einlagen."""

        return self._contribution_edit.text()

    @property
    def withdrawal_distribution(self) -> str:
        """Liefert die eingegebenen Entnahmen/Ausschüttungen."""

        return self._withdrawal_distribution_edit.text()

    def set_taxonomy_status(
        self,
        *,
        text: str,
        install_enabled: bool,
    ) -> None:
        """Aktualisiert Taxonomiestatus und Installationsaktion."""

        self._taxonomy_status_label.setText(text)
        self._install_taxonomy_button.setEnabled(
            install_enabled
        )

    def set_bvv_values(
        self,
        *,
        effective_previous_hgb_equity: str,
        previous_hgb_equity_source: str,
        previous_hgb_equity_override: str,
        contribution: str,
        withdrawal_distribution: str,
    ) -> None:
        """Aktualisiert die angezeigten BVV-Jahresdaten."""

        self._effective_previous_hgb_equity_label.setText(
            effective_previous_hgb_equity
        )
        self._previous_hgb_equity_source_label.setText(
            previous_hgb_equity_source
        )
        self._previous_hgb_equity_override_edit.setText(
            previous_hgb_equity_override
        )
        self._contribution_edit.setText(contribution)
        self._withdrawal_distribution_edit.setText(
            withdrawal_distribution
        )

    def set_workflow_state(
        self,
        *,
        status_text: str,
        prepare_enabled: bool,
        build_enabled: bool,
        validate_enabled: bool,
        export_enabled: bool,
    ) -> None:
        """Aktualisiert Zustand und Aktionen des E-Bilanz-Workflows."""

        self._status_label.setText(status_text)
        self._prepare_button.setEnabled(prepare_enabled)
        self._build_button.setEnabled(build_enabled)
        self._validate_button.setEnabled(validate_enabled)
        self._export_xbrl_button.setEnabled(export_enabled)
        self._export_pdf_button.setEnabled(export_enabled)

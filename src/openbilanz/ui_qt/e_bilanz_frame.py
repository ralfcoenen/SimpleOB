"""PySide6-Arbeitsbereich für die E-Bilanz."""

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class EBilanzFrame(QWidget):
    """Bedienelemente für Vorbereitung und Erzeugung der E-Bilanz."""

    def __init__(
        self,
        *,
        on_install_taxonomy: Callable[[], None],
        on_prepare: Callable[[], None],
        on_build: Callable[[], None],
        on_validate: Callable[[], None],
        on_export_xbrl: Callable[[], None],
        on_export_pdf: Callable[[], None],
        on_send_test: Callable[[], None],
        on_send_production: Callable[[], None],
        on_export_bvv_pdf: Callable[[], None],
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

        columns_layout = QHBoxLayout()
        columns_layout.setAlignment(
            Qt.AlignmentFlag.AlignTop
        )

        taxonomy_group = self._create_taxonomy_group(
            on_install_taxonomy=on_install_taxonomy,
        )
        bvv_group = self._create_bvv_group(
            on_export_bvv_pdf=on_export_bvv_pdf,
        )
        actions_group = self._create_actions_group(
            on_prepare=on_prepare,
            on_build=on_build,
            on_validate=on_validate,
            on_export_xbrl=on_export_xbrl,
            on_export_pdf=on_export_pdf,
            on_send_test=on_send_test,
            on_send_production=on_send_production,
        )

        columns_layout.addWidget(taxonomy_group, 2)
        columns_layout.addWidget(bvv_group, 3)
        columns_layout.addWidget(actions_group, 2)

        layout.addLayout(columns_layout)
        layout.addStretch()

        self._prepare_button.setEnabled(False)
        self._build_button.setEnabled(False)
        self._validate_button.setEnabled(False)
        self._export_xbrl_button.setEnabled(False)
        self._export_pdf_button.setEnabled(False)
        self._send_test_button.setEnabled(False)
        self._send_production_button.setEnabled(False)

    def _create_taxonomy_group(
        self,
        *,
        on_install_taxonomy: Callable[[], None],
    ) -> QGroupBox:
        """Erzeugt den Bereich für Taxonomie und Workflowstatus."""

        group = QGroupBox("Taxonomie und Status")
        layout = QVBoxLayout(group)

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
        self._configure_action_button(
            self._install_taxonomy_button
        )
        layout.addWidget(
            self._install_taxonomy_button,
            alignment=Qt.AlignmentFlag.AlignLeft,
        )

        self._status_label = QLabel("")
        self._status_label.setWordWrap(True)
        layout.addWidget(self._status_label)

        layout.addStretch()

        return group

    def _create_bvv_group(
        self,
        *,
        on_export_bvv_pdf: Callable[[], None],
    ) -> QGroupBox:
        """Erzeugt die Anzeige des Betriebsvermögensvergleichs."""

        group = QGroupBox(
            "Steuerliche Gewinnermittlung (BVV)"
        )
        layout = QFormLayout(group)

        self._bvv_current_hgb_equity_label = QLabel("–")
        layout.addRow(
            "HGB-Eigenkapital",
            self._bvv_current_hgb_equity_label,
        )

        self._bvv_current_book_value_difference_label = QLabel("–")
        layout.addRow(
            "Buchwertabweichung aus steuerlicher AfA",
            self._bvv_current_book_value_difference_label,
        )

        self._bvv_current_tax_equity_label = QLabel("–")
        layout.addRow(
            "Steuerliches Betriebsvermögen Ende",
            self._bvv_current_tax_equity_label,
        )

        separator = QLabel("")
        separator.setMinimumHeight(8)
        layout.addRow(separator)

        self._bvv_previous_hgb_equity_label = QLabel("–")
        layout.addRow(
            "HGB-Eigenkapital zu Jahresbeginn",
            self._bvv_previous_hgb_equity_label,
        )

        self._bvv_previous_book_value_difference_label = QLabel("–")
        layout.addRow(
            "Buchwertabweichung zu Jahresbeginn",
            self._bvv_previous_book_value_difference_label,
        )

        self._bvv_previous_tax_equity_label = QLabel("–")
        layout.addRow(
            "Steuerliches Betriebsvermögen Vorjahr",
            self._bvv_previous_tax_equity_label,
        )

        self._bvv_change_in_tax_equity_label = QLabel("–")
        layout.addRow(
            "Veränderung des Betriebsvermögens",
            self._bvv_change_in_tax_equity_label,
        )

        self._bvv_contribution_label = QLabel("–")
        layout.addRow(
            "− gebuchte Einlagen",
            self._bvv_contribution_label,
        )

        self._bvv_withdrawal_distribution_label = QLabel("–")
        layout.addRow(
            "+ gebuchte Entnahmen / Ausschüttungen",
            self._bvv_withdrawal_distribution_label,
        )

        self._bvv_profit_loss_label = QLabel("–")
        self._bvv_profit_loss_label.setStyleSheet(
            "font-weight: bold;"
        )
        layout.addRow(
            "Steuerlicher Gewinn / Verlust",
            self._bvv_profit_loss_label,
        )

        self._bvv_source_label = QLabel(
            "Alle Werte werden aus der Buchführung ermittelt."
        )
        self._bvv_source_label.setWordWrap(True)
        layout.addRow("", self._bvv_source_label)

        self._export_bvv_pdf_button = QPushButton(
            "BVV als PDF exportieren"
        )
        self._export_bvv_pdf_button.clicked.connect(
            on_export_bvv_pdf
        )
        self._configure_action_button(
            self._export_bvv_pdf_button
        )
        self._export_bvv_pdf_button.setEnabled(False)

        layout.addRow(
            "",
            self._export_bvv_pdf_button,
        )

        return group

    def _create_actions_group(
        self,
        *,
        on_prepare: Callable[[], None],
        on_build: Callable[[], None],
        on_validate: Callable[[], None],
        on_export_xbrl: Callable[[], None],
        on_export_pdf: Callable[[], None],
        on_send_test: Callable[[], None],
        on_send_production: Callable[[], None],
    ) -> QGroupBox:
        """Erzeugt den Bereich für die E-Bilanz-Aktionen."""

        group = QGroupBox("E-Bilanz-Aktionen")
        layout = QVBoxLayout(group)

        self._prepare_button = QPushButton(
            "E-Bilanz vorbereiten"
        )
        self._prepare_button.clicked.connect(on_prepare)

        self._build_button = QPushButton(
            "E-Bilanz erzeugen"
        )
        self._build_button.clicked.connect(on_build)

        self._validate_button = QPushButton(
            "E-Bilanz validieren"
        )
        self._validate_button.clicked.connect(on_validate)

        self._export_xbrl_button = QPushButton(
            "E-Bilanz XBRL exportieren"
        )
        self._export_xbrl_button.clicked.connect(on_export_xbrl)

        self._export_pdf_button = QPushButton(
            "E-Bilanz PDF exportieren"
        )
        self._export_pdf_button.clicked.connect(on_export_pdf)

        self._send_test_button = QPushButton(
            "ELSTER-Testübermittlung"
        )
        self._send_test_button.clicked.connect(on_send_test)

        self._send_production_button = QPushButton(
            "ELSTER-Produktivübermittlung"
        )
        self._send_production_button.clicked.connect(
            on_send_production
        )

        buttons = (
            self._prepare_button,
            self._build_button,
            self._validate_button,
            self._export_xbrl_button,
            self._export_pdf_button,
            self._send_test_button,
            self._send_production_button,
        )

        for button in buttons:
            self._configure_action_button(button)
            layout.addWidget(
                button,
                alignment=Qt.AlignmentFlag.AlignLeft,
            )

        layout.addStretch()

        return group

    @staticmethod
    def _configure_action_button(
        button: QPushButton,
    ) -> None:
        """Hält Aktionsschaltflächen kompakt und gut lesbar."""

        button.setSizePolicy(
            QSizePolicy.Policy.Maximum,
            QSizePolicy.Policy.Fixed,
        )
        button.setMaximumWidth(260)

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

    def set_bvv_evaluation(
        self,
        *,
        current_hgb_equity: str,
        current_book_value_difference: str,
        current_tax_equity: str,
        previous_hgb_equity: str,
        previous_book_value_difference: str,
        previous_tax_equity: str,
        change_in_tax_equity: str,
        contribution: str,
        withdrawal_distribution: str,
        profit_loss: str,
    ) -> None:
        """Zeigt den aus der Buchführung ermittelten BVV an."""

        self._bvv_current_hgb_equity_label.setText(
            current_hgb_equity
        )
        self._bvv_current_book_value_difference_label.setText(
            current_book_value_difference
        )
        self._bvv_current_tax_equity_label.setText(
            current_tax_equity
        )
        self._bvv_previous_hgb_equity_label.setText(
            previous_hgb_equity
        )
        self._bvv_previous_book_value_difference_label.setText(
            previous_book_value_difference
        )
        self._bvv_previous_tax_equity_label.setText(
            previous_tax_equity
        )
        self._bvv_change_in_tax_equity_label.setText(
            change_in_tax_equity
        )
        self._bvv_contribution_label.setText(contribution)
        self._bvv_withdrawal_distribution_label.setText(
            withdrawal_distribution
        )
        self._bvv_profit_loss_label.setText(profit_loss)
        self._export_bvv_pdf_button.setEnabled(True)

    def clear_bvv_evaluation(self) -> None:
        """Leert die BVV-Anzeige, wenn noch keine Auswertung möglich ist."""

        labels = (
            self._bvv_current_hgb_equity_label,
            self._bvv_current_book_value_difference_label,
            self._bvv_current_tax_equity_label,
            self._bvv_previous_hgb_equity_label,
            self._bvv_previous_book_value_difference_label,
            self._bvv_previous_tax_equity_label,
            self._bvv_change_in_tax_equity_label,
            self._bvv_contribution_label,
            self._bvv_withdrawal_distribution_label,
            self._bvv_profit_loss_label,
        )

        for label in labels:
            label.setText("–")

        self._export_bvv_pdf_button.setEnabled(False)

    def set_workflow_state(
        self,
        *,
        status_text: str,
        prepare_enabled: bool,
        build_enabled: bool,
        validate_enabled: bool,
        export_enabled: bool,
        transmission_enabled: bool = False,
    ) -> None:
        """Aktualisiert Zustand und Aktionen des E-Bilanz-Workflows."""

        self._status_label.setText(status_text)
        self._prepare_button.setEnabled(prepare_enabled)
        self._build_button.setEnabled(build_enabled)
        self._validate_button.setEnabled(validate_enabled)
        self._export_xbrl_button.setEnabled(export_enabled)
        self._export_pdf_button.setEnabled(export_enabled)
        self._send_test_button.setEnabled(transmission_enabled)
        self._send_production_button.setEnabled(
            transmission_enabled
        )

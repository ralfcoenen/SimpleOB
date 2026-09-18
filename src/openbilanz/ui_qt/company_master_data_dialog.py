"""PySide6-Dialog zur Pflege der Unternehmensstammdaten."""

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from openbilanz.domain.company_master_data import CompanyMasterData


FEDERAL_STATES = (
    ("BW", "Baden-Württemberg"),
    ("BY", "Bayern"),
    ("BE", "Berlin"),
    ("BB", "Brandenburg"),
    ("HB", "Bremen"),
    ("HH", "Hamburg"),
    ("HE", "Hessen"),
    ("MV", "Mecklenburg-Vorpommern"),
    ("NI", "Niedersachsen"),
    ("NW", "Nordrhein-Westfalen"),
    ("RP", "Rheinland-Pfalz"),
    ("SL", "Saarland"),
    ("SN", "Sachsen"),
    ("ST", "Sachsen-Anhalt"),
    ("SH", "Schleswig-Holstein"),
    ("TH", "Thüringen"),
)


class CompanyMasterDataDialog(QDialog):
    """Bearbeitet die Stammdaten eines Unternehmens."""

    def __init__(
        self,
        parent,
        *,
        master_data: CompanyMasterData,
    ) -> None:
        super().__init__(parent)

        self._master_data = master_data
        self.result: CompanyMasterData | None = None

        self.setWindowTitle(
            "SimpleOB – Unternehmensstammdaten"
        )
        self.resize(760, 720)
        self.setMinimumSize(700, 650)

        self._create_ui()
        self._load_values()

    def _create_ui(self) -> None:
        """Erzeugt die Benutzeroberfläche."""

        layout = QVBoxLayout(self)

        title_label = QLabel("Unternehmensstammdaten")
        title_label.setStyleSheet(
            "font-size: 18px; font-weight: bold;"
        )
        layout.addWidget(title_label)

        company_label = QLabel(
            self._master_data.company.name
        )
        layout.addWidget(company_label)

        required_label = QLabel(
            "* Pflichtfeld für die E-Bilanz"
        )
        layout.addWidget(required_label)

        form = QFormLayout()
        layout.addLayout(form)

        self._legal_form_edit = QLineEdit()
        self._tax_number_edit = QLineEdit()
        self._tax_office_edit = QLineEdit()
        self._tax_id_edit = QLineEdit()
        self._tax_economic_id_edit = QLineEdit()
        self._bf4_edit = QLineEdit()
        self._street_edit = QLineEdit()
        self._house_number_edit = QLineEdit()
        self._postal_code_edit = QLineEdit()
        self._city_edit = QLineEdit()
        self._country_edit = QLineEdit()
        self._business_edit = QLineEdit()

        form.addRow(
            "Rechtsform *",
            self._legal_form_edit,
        )
        form.addRow(
            "Steuernummer *",
            self._tax_number_edit,
        )
        form.addRow(
            "Finanzamt",
            self._tax_office_edit,
        )
        form.addRow(
            "Steuer-ID",
            self._tax_id_edit,
        )
        form.addRow(
            "Wirtschafts-ID",
            self._tax_economic_id_edit,
        )
        form.addRow(
            "BF4",
            self._bf4_edit,
        )
        form.addRow(
            "Straße *",
            self._street_edit,
        )
        form.addRow(
            "Hausnummer *",
            self._house_number_edit,
        )
        form.addRow(
            "PLZ *",
            self._postal_code_edit,
        )
        form.addRow(
            "Ort *",
            self._city_edit,
        )
        form.addRow(
            "Land *",
            self._country_edit,
        )
        form.addRow(
            "Geschäftstätigkeit *",
            self._business_edit,
        )

        self._federal_state_box = QComboBox()
        self._federal_state_box.addItem("", "")

        for code, name in FEDERAL_STATES:
            self._federal_state_box.addItem(
                name,
                code,
            )

        form.addRow(
            "Bundesland *",
            self._federal_state_box,
        )

        layout.addStretch()

        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_button = QPushButton("Abbrechen")
        cancel_button.clicked.connect(
            self.reject
        )
        button_layout.addWidget(cancel_button)

        save_button = QPushButton("Speichern")
        save_button.clicked.connect(
            self._save
        )
        save_button.setDefault(True)
        button_layout.addWidget(save_button)

        layout.addLayout(button_layout)

    def _load_values(self) -> None:
        """Übernimmt die vorhandenen Stammdaten."""

        self._legal_form_edit.setText(
            self._master_data.legal_form
        )
        self._tax_number_edit.setText(
            self._master_data.tax_number
        )
        self._tax_office_edit.setText(
            self._master_data.tax_office
        )
        self._tax_id_edit.setText(
            self._master_data.tax_id
        )
        self._tax_economic_id_edit.setText(
            self._master_data.tax_economic_id
        )
        self._bf4_edit.setText(
            self._master_data.bf4
        )
        self._street_edit.setText(
            self._master_data.street
        )
        self._house_number_edit.setText(
            self._master_data.house_number
        )
        self._postal_code_edit.setText(
            self._master_data.postal_code
        )
        self._city_edit.setText(
            self._master_data.city
        )
        self._country_edit.setText(
            self._master_data.country
        )
        self._business_edit.setText(
            self._master_data.business
        )

        index = self._federal_state_box.findData(
            self._master_data.federal_state
        )

        if index >= 0:
            self._federal_state_box.setCurrentIndex(
                index
            )

    def _save(self) -> None:
        """Erzeugt die geänderten Stammdaten."""

        try:
            master_data = CompanyMasterData(
                company=self._master_data.company,
                legal_form=self._legal_form_edit.text().strip(),
                tax_number=self._tax_number_edit.text().strip(),
                tax_office=self._tax_office_edit.text().strip(),
                tax_id=self._tax_id_edit.text().strip(),
                tax_economic_id=(
                    self._tax_economic_id_edit.text().strip()
                ),
                bf4=self._bf4_edit.text().strip(),
                street=self._street_edit.text().strip(),
                house_number=(
                    self._house_number_edit.text().strip()
                ),
                postal_code=(
                    self._postal_code_edit.text().strip()
                ),
                city=self._city_edit.text().strip(),
                country=self._country_edit.text().strip(),
                federal_state=(
                    self._federal_state_box.currentData()
                    or ""
                ),
                business=self._business_edit.text().strip(),
            )

            master_data.validate_e_bilanz_ready()

        except (TypeError, ValueError) as exc:
            QMessageBox.critical(
                self,
                "Ungültige Stammdaten",
                str(exc),
            )
            return

        self.result = master_data
        self.accept()

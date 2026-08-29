"""Dialog zur Pflege der Unternehmensstammdaten."""

from dataclasses import dataclass
from datetime import date

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from openbilanz.domain.company_master_data import (
    CompanyMasterData,
)
from openbilanz.domain.vat_configuration import (
    VatConfiguration,
)
from openbilanz.domain.vat_taxation_method import (
    VatTaxationMethod,
)
from openbilanz.domain.vat_taxation_type import (
    VatTaxationType,
)

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

FEDERAL_STATE_LABELS = {
    code: name
    for code, name in FEDERAL_STATES
}

FEDERAL_STATE_CODES = {
    name: code
    for code, name in FEDERAL_STATES
}

_STANDARD_VAT = "Regelbesteuerung"
_SMALL_BUSINESS_VAT = (
    "Kleinunternehmer gemäß § 19 UStG"
)
_AGREED_TAXATION = "Sollversteuerung"
_RECEIVED_TAXATION = "Istversteuerung"


@dataclass(frozen=True, slots=True)
class CompanyMasterDataDialogResult:
    """Ergebnis des Stammdatendialogs."""

    master_data: CompanyMasterData
    vat_configuration: VatConfiguration


class CompanyMasterDataDialog(QDialog):
    """Bearbeitet die Stammdaten eines Unternehmens."""

    def __init__(
        self,
        *,
        master_data: CompanyMasterData,
        vat_configuration: VatConfiguration,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._master_data = master_data
        self._vat_configuration = vat_configuration

        self.result: (
            CompanyMasterDataDialogResult | None
        ) = None

        self.setWindowTitle(
            "OpenBilanz – Unternehmensstammdaten"
        )
        self.resize(760, 690)
        self.setMinimumWidth(680)

        self._create_ui()
        self._load_values()

    def _create_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            24,
            20,
            24,
            20,
        )
        layout.setSpacing(14)

        header = self._create_header()
        layout.addWidget(header)

        layout.addWidget(
            self._create_company_group()
        )
        layout.addWidget(
            self._create_tax_group()
        )
        layout.addWidget(
            self._create_address_group()
        )
        layout.addWidget(
            self._create_vat_group()
        )

        layout.addStretch()

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )

        buttons.button(
            QDialogButtonBox.StandardButton.Save
        ).setText("Speichern")

        buttons.button(
            QDialogButtonBox.StandardButton.Cancel
        ).setText("Abbrechen")

        buttons.accepted.connect(
            self._save
        )
        buttons.rejected.connect(
            self.reject
        )

        layout.addWidget(buttons)

    def _create_header(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        layout.setContentsMargins(
            0,
            0,
            0,
            4,
        )
        layout.setSpacing(3)

        title = QLabel(
            "Unternehmensstammdaten"
        )

        font = title.font()
        font.setPointSize(18)
        font.setBold(True)
        title.setFont(font)

        company = QLabel(
            self._master_data.company.name
        )

        company_font = company.font()
        company_font.setPointSize(11)
        company.setFont(company_font)

        layout.addWidget(title)
        layout.addWidget(company)

        return widget

    def _create_company_group(
        self,
    ) -> QGroupBox:
        group = QGroupBox(
            "Unternehmen"
        )

        form = QFormLayout(group)
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(8)

        self._legal_form = QLineEdit()
        self._business = QLineEdit()

        form.addRow(
            "Rechtsform",
            self._legal_form,
        )
        form.addRow(
            "Geschäftstätigkeit",
            self._business,
        )

        return group

    def _create_tax_group(
        self,
    ) -> QGroupBox:
        group = QGroupBox(
            "Steuerliche Angaben"
        )

        grid = QGridLayout(group)
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(8)

        self._tax_number = QLineEdit()
        self._tax_office = QLineEdit()
        self._tax_id = QLineEdit()
        self._tax_economic_id = QLineEdit()
        self._bf4 = QLineEdit()

        grid.addWidget(
            QLabel("Steuernummer"),
            0,
            0,
        )
        grid.addWidget(
            self._tax_number,
            0,
            1,
        )

        grid.addWidget(
            QLabel("Finanzamt"),
            0,
            2,
        )
        grid.addWidget(
            self._tax_office,
            0,
            3,
        )

        grid.addWidget(
            QLabel("Steuer-ID"),
            1,
            0,
        )
        grid.addWidget(
            self._tax_id,
            1,
            1,
        )

        grid.addWidget(
            QLabel("Wirtschafts-ID"),
            1,
            2,
        )
        grid.addWidget(
            self._tax_economic_id,
            1,
            3,
        )

        grid.addWidget(
            QLabel("BF4"),
            2,
            0,
        )
        grid.addWidget(
            self._bf4,
            2,
            1,
        )

        grid.setColumnStretch(
            1,
            1,
        )
        grid.setColumnStretch(
            3,
            1,
        )

        return group

    def _create_address_group(
        self,
    ) -> QGroupBox:
        group = QGroupBox(
            "Anschrift"
        )

        grid = QGridLayout(group)
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(8)

        self._street = QLineEdit()
        self._house_number = QLineEdit()
        self._postal_code = QLineEdit()
        self._city = QLineEdit()
        self._country = QLineEdit()

        self._federal_state = QComboBox()
        self._federal_state.addItem("")

        for _, name in FEDERAL_STATES:
            self._federal_state.addItem(
                name
            )

        self._house_number.setMaximumWidth(
            120
        )
        self._postal_code.setMaximumWidth(
            120
        )

        grid.addWidget(
            QLabel("Straße"),
            0,
            0,
        )
        grid.addWidget(
            self._street,
            0,
            1,
        )

        grid.addWidget(
            QLabel("Hausnummer"),
            0,
            2,
        )
        grid.addWidget(
            self._house_number,
            0,
            3,
        )

        grid.addWidget(
            QLabel("PLZ"),
            1,
            0,
        )
        grid.addWidget(
            self._postal_code,
            1,
            1,
        )

        grid.addWidget(
            QLabel("Ort"),
            1,
            2,
        )
        grid.addWidget(
            self._city,
            1,
            3,
        )

        grid.addWidget(
            QLabel("Bundesland"),
            2,
            0,
        )
        grid.addWidget(
            self._federal_state,
            2,
            1,
        )

        grid.addWidget(
            QLabel("Land"),
            2,
            2,
        )
        grid.addWidget(
            self._country,
            2,
            3,
        )

        grid.setColumnStretch(
            1,
            1,
        )
        grid.setColumnStretch(
            3,
            1,
        )

        return group

    def _create_vat_group(
        self,
    ) -> QGroupBox:
        group = QGroupBox(
            "Umsatzsteuer"
        )

        form = QFormLayout(group)
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(8)

        self._vat_taxation_type = QComboBox()

        self._vat_taxation_type.addItems(
            (
                _STANDARD_VAT,
                _SMALL_BUSINESS_VAT,
            )
        )

        self._vat_taxation_method = QComboBox()

        self._vat_taxation_method.addItems(
            (
                _AGREED_TAXATION,
                _RECEIVED_TAXATION,
            )
        )

        self._vat_effective_from = QDateEdit()
        self._vat_effective_from.setCalendarPopup(
            True
        )
        self._vat_effective_from.setDisplayFormat(
            "dd.MM.yyyy"
        )

        form.addRow(
            "Umsatzsteuerliche Behandlung",
            self._vat_taxation_type,
        )

        form.addRow(
            "Besteuerung nach",
            self._vat_taxation_method,
        )

        form.addRow(
            "Gültig ab",
            self._vat_effective_from,
        )

        hint = QLabel(
            "Bei Anwendung der "
            "Kleinunternehmerregelung werden "
            "Ausgangsrechnungen ohne Umsatzsteuer "
            "erstellt."
        )
        hint.setWordWrap(True)

        form.addRow(
            "",
            hint,
        )

        return group

    def _load_values(self) -> None:
        self._legal_form.setText(
            self._master_data.legal_form
        )

        self._business.setText(
            self._master_data.business
        )

        self._tax_number.setText(
            self._master_data.tax_number
        )

        self._tax_office.setText(
            self._master_data.tax_office
        )

        self._tax_id.setText(
            self._master_data.tax_id
        )

        self._tax_economic_id.setText(
            self._master_data.tax_economic_id
        )

        self._bf4.setText(
            self._master_data.bf4
        )

        self._street.setText(
            self._master_data.street
        )

        self._house_number.setText(
            self._master_data.house_number
        )

        self._postal_code.setText(
            self._master_data.postal_code
        )

        self._city.setText(
            self._master_data.city
        )

        self._country.setText(
            self._master_data.country
        )

        self._federal_state.setCurrentText(
            FEDERAL_STATE_LABELS.get(
                self._master_data.federal_state,
                "",
            )
        )

        if (
            self._vat_configuration.is_small_business
        ):
            self._vat_taxation_type.setCurrentText(
                _SMALL_BUSINESS_VAT
            )
        else:
            self._vat_taxation_type.setCurrentText(
                _STANDARD_VAT
            )

        if (
            self._vat_configuration.taxation_method
            is VatTaxationMethod.RECEIVED
        ):
            self._vat_taxation_method.setCurrentText(
                _RECEIVED_TAXATION
            )
        else:
            self._vat_taxation_method.setCurrentText(
                _AGREED_TAXATION
            )

        effective_from = (
            self._vat_configuration.effective_from
        )

        self._vat_effective_from.setDate(
            QDate(
                effective_from.year,
                effective_from.month,
                effective_from.day,
            )
        )

    def _save(self) -> None:
        try:
            master_data = CompanyMasterData(
                company=self._master_data.company,
                legal_form=self._value(
                    self._legal_form
                ),
                tax_number=self._value(
                    self._tax_number
                ),
                tax_office=self._value(
                    self._tax_office
                ),
                tax_id=self._value(
                    self._tax_id
                ),
                tax_economic_id=self._value(
                    self._tax_economic_id
                ),
                bf4=self._value(
                    self._bf4
                ),
                street=self._value(
                    self._street
                ),
                house_number=self._value(
                    self._house_number
                ),
                postal_code=self._value(
                    self._postal_code
                ),
                city=self._value(
                    self._city
                ),
                country=self._value(
                    self._country
                ),
                federal_state=(
                    FEDERAL_STATE_CODES.get(
                        self._federal_state.currentText(),
                        "",
                    )
                ),
                business=self._value(
                    self._business
                ),
            )

            taxation_type = (
                VatTaxationType.SMALL_BUSINESS
                if (
                    self._vat_taxation_type.currentText()
                    == _SMALL_BUSINESS_VAT
                )
                else VatTaxationType.STANDARD
            )

            taxation_method = (
                VatTaxationMethod.RECEIVED
                if (
                    self._vat_taxation_method.currentText()
                    == _RECEIVED_TAXATION
                )
                else VatTaxationMethod.AGREED
            )

            qt_date = (
                self._vat_effective_from.date()
            )

            effective_from = date(
                qt_date.year(),
                qt_date.month(),
                qt_date.day(),
            )

            vat_configuration = VatConfiguration(
                taxation_type=taxation_type,
                effective_from=effective_from,
                taxation_method=taxation_method,
            )

        except (TypeError, ValueError) as exc:
            QMessageBox.critical(
                self,
                "Ungültige Stammdaten",
                str(exc),
            )
            return

        self.result = CompanyMasterDataDialogResult(
            master_data=master_data,
            vat_configuration=vat_configuration,
        )

        self.accept()

    @staticmethod
    def _value(
        widget: QLineEdit,
    ) -> str:
        return widget.text().strip()

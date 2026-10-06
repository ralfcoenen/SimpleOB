"""PySide6-Dialog zur Pflege des ELSTER-Datenlieferanten."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from openbilanz.domain.elster_data_supplier import (
    ElsterDataSupplier,
)


class ElsterDataSupplierDialog(QDialog):
    """Bearbeitet die Daten des Erstellers einer E-Bilanz."""

    def __init__(
        self,
        parent,
        *,
        data_supplier: ElsterDataSupplier | None,
    ) -> None:
        super().__init__(parent)

        self._data_supplier = (
            data_supplier
            if data_supplier is not None
            else ElsterDataSupplier()
        )
        self.result: ElsterDataSupplier | None = None

        self.setWindowTitle(
            "SimpleOB – ELSTER-Datenlieferant"
        )
        self.resize(620, 520)
        self.setMinimumWidth(560)

        self._create_ui()
        self._load_values()

    def _create_ui(self) -> None:
        """Erzeugt die Benutzeroberfläche."""

        layout = QVBoxLayout(self)

        title_label = QLabel(
            "ELSTER-Datenlieferant"
        )
        title_label.setStyleSheet(
            "font-size: 18px; font-weight: bold;"
        )
        layout.addWidget(title_label)

        information_label = QLabel(
            "Hier werden die Daten des Erstellers der "
            "E-Bilanz hinterlegt. Der Ersteller muss nicht "
            "mit dem Unternehmen übereinstimmen, dessen "
            "E-Bilanz übermittelt wird."
        )
        information_label.setWordWrap(True)
        layout.addWidget(information_label)

        form = QFormLayout()
        layout.addLayout(form)

        self._name_edit = QLineEdit()
        self._street_edit = QLineEdit()
        self._house_number_edit = QLineEdit()
        self._house_number_suffix_edit = QLineEdit()
        self._address_addition_edit = QLineEdit()
        self._postal_code_edit = QLineEdit()
        self._city_edit = QLineEdit()
        self._country_edit = QLineEdit()
        self._phone_edit = QLineEdit()
        self._email_edit = QLineEdit()

        form.addRow(
            "Name des Erstellers",
            self._name_edit,
        )
        form.addRow(
            "Straße",
            self._street_edit,
        )
        form.addRow(
            "Hausnummer",
            self._house_number_edit,
        )
        form.addRow(
            "Hausnummerzusatz",
            self._house_number_suffix_edit,
        )
        form.addRow(
            "Adresszusatz",
            self._address_addition_edit,
        )
        form.addRow(
            "PLZ",
            self._postal_code_edit,
        )
        form.addRow(
            "Ort",
            self._city_edit,
        )
        form.addRow(
            "Land",
            self._country_edit,
        )
        form.addRow(
            "Telefon",
            self._phone_edit,
        )
        form.addRow(
            "E-Mail-Adresse",
            self._email_edit,
        )

        layout.addStretch()

        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_button = QPushButton(
            "Abbrechen"
        )
        cancel_button.clicked.connect(
            self.reject
        )
        button_layout.addWidget(
            cancel_button
        )

        save_button = QPushButton(
            "Speichern"
        )
        save_button.clicked.connect(
            self._save
        )
        save_button.setDefault(True)
        button_layout.addWidget(
            save_button
        )

        layout.addLayout(
            button_layout
        )

    def _load_values(self) -> None:
        """Übernimmt die vorhandenen Daten."""

        self._name_edit.setText(
            self._data_supplier.name
        )
        self._street_edit.setText(
            self._data_supplier.street
        )
        self._house_number_edit.setText(
            self._data_supplier.house_number
        )
        self._house_number_suffix_edit.setText(
            self._data_supplier.house_number_suffix
        )
        self._address_addition_edit.setText(
            self._data_supplier.address_addition
        )
        self._postal_code_edit.setText(
            self._data_supplier.postal_code
        )
        self._city_edit.setText(
            self._data_supplier.city
        )
        self._country_edit.setText(
            self._data_supplier.country
        )
        self._phone_edit.setText(
            self._data_supplier.phone
        )
        self._email_edit.setText(
            self._data_supplier.email
        )

    def _save(self) -> None:
        """Erzeugt die geänderten Daten des Erstellers."""

        try:
            data_supplier = ElsterDataSupplier(
                name=self._name_edit.text(),
                street=self._street_edit.text(),
                house_number=self._house_number_edit.text(),
                house_number_suffix=(
                    self._house_number_suffix_edit.text()
                ),
                address_addition=(
                    self._address_addition_edit.text()
                ),
                postal_code=self._postal_code_edit.text(),
                city=self._city_edit.text(),
                country=self._country_edit.text(),
                phone=self._phone_edit.text(),
                email=self._email_edit.text(),
            )
        except (TypeError, ValueError) as exc:
            QMessageBox.critical(
                self,
                "Ungültige Daten",
                str(exc),
            )
            return

        if not data_supplier.is_configured:
            QMessageBox.warning(
                self,
                "ELSTER-Datenlieferant",
                (
                    "Es wurden keine Daten des "
                    "ELSTER-Datenlieferanten eingegeben."
                ),
            )
            return

        self.result = data_supplier
        self.accept()

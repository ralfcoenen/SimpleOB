"""Kleine Mandantenverwaltung für Geschäftspartner der OP-Stufe 1."""

from uuid import UUID

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from simpleob.database.business_partner_repository import (
    BusinessPartnerRepository,
)
from simpleob.domain.business_partner import BusinessPartner


class BusinessPartnerDialog(QDialog):
    """Legt mandantenbezogene Kunden/Lieferanten an und zeigt sie an."""

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        company_id: UUID,
        repository: BusinessPartnerRepository,
    ) -> None:
        super().__init__(parent)
        self._company_id = company_id
        self._repository = repository
        self.setWindowTitle("Geschäftspartner")
        self.resize(560, 420)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Geschäftspartner dieses Mandanten"))

        form = QFormLayout()
        self._name_entry = QLineEdit()
        self._customer_check = QCheckBox("Kunde")
        self._customer_check.setChecked(True)
        self._supplier_check = QCheckBox("Lieferant")
        roles = QHBoxLayout()
        roles.addWidget(self._customer_check)
        roles.addWidget(self._supplier_check)
        form.addRow("Name", self._name_entry)
        form.addRow("Rolle", roles)
        layout.addLayout(form)

        actions = QHBoxLayout()
        actions.addStretch()
        add_button = QPushButton("Anlegen")
        add_button.clicked.connect(self._add_partner)
        actions.addWidget(add_button)
        close_button = QPushButton("Schließen")
        close_button.clicked.connect(self.accept)
        actions.addWidget(close_button)
        layout.addLayout(actions)

        self._table = QTableWidget(0, 3)
        self._table.setHorizontalHeaderLabels(("Name", "Kunde", "Lieferant"))
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self._table)
        self._refresh()

    def _add_partner(self) -> None:
        try:
            self._repository.add(
                BusinessPartner(
                    company_id=self._company_id,
                    name=self._name_entry.text(),
                    is_customer=self._customer_check.isChecked(),
                    is_supplier=self._supplier_check.isChecked(),
                )
            )
        except (TypeError, ValueError) as exc:
            QMessageBox.warning(self, "Geschäftspartner", str(exc))
            return
        self._name_entry.clear()
        self._customer_check.setChecked(True)
        self._supplier_check.setChecked(False)
        self._refresh()

    def _refresh(self) -> None:
        partners = self._repository.list_for_company(
            self._company_id,
            active_only=False,
        )
        self._table.setRowCount(len(partners))
        for row, partner in enumerate(partners):
            self._table.setItem(row, 0, QTableWidgetItem(partner.name))
            self._table.setItem(
                row, 1, QTableWidgetItem("Ja" if partner.is_customer else "Nein")
            )
            self._table.setItem(
                row, 2, QTableWidgetItem("Ja" if partner.is_supplier else "Nein")
            )

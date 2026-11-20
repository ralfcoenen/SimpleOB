"""Dialog zur gemeinsamen Pflege von Personenkonto und Geschäftspartner."""

from uuid import UUID

from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from simpleob.database.person_account_repository import PersonAccountRepository
from simpleob.domain.person_account import PersonAccount
from simpleob.domain.person_account_role import PersonAccountRole


class PersonAccountDialog(QDialog):
    """Erfasst ein Debitoren- oder Kreditorenkonto ohne HGB-Zuordnungsfelder."""

    def __init__(
        self,
        parent: QWidget | None,
        *,
        company_id: UUID,
        role: PersonAccountRole = PersonAccountRole.DEBITOR,
        repository: PersonAccountRepository,
        existing: PersonAccount | None = None,
    ) -> None:
        super().__init__(parent)
        self._company_id = company_id
        self._role = role
        self._repository = repository
        self._existing = existing
        self.saved: PersonAccount | None = None
        self._number_is_manual = False
        self._updating_number = False
        label = "Debitor" if role is PersonAccountRole.DEBITOR else "Kreditor"
        self.setWindowTitle(
            f"Personenkonto {label} bearbeiten" if existing else "Neues Personenkonto"
        )
        self.setMinimumWidth(520)

        layout = QVBoxLayout(self)
        self._heading = QLabel(f"{label} – Geschäftspartner und Personenkonto")
        layout.addWidget(self._heading)
        form = QFormLayout()

        self._debtor_radio: QRadioButton | None = None
        self._creditor_radio: QRadioButton | None = None
        self._role_button_group: QButtonGroup | None = None
        if existing is None:
            role_layout = QHBoxLayout()
            self._role_button_group = QButtonGroup(self)
            self._role_button_group.setExclusive(True)
            self._debtor_radio = QRadioButton("Debitor")
            self._creditor_radio = QRadioButton("Kreditor")
            self._role_button_group.addButton(self._debtor_radio)
            self._role_button_group.addButton(self._creditor_radio)
            self._debtor_radio.setChecked(role is PersonAccountRole.DEBITOR)
            self._creditor_radio.setChecked(role is PersonAccountRole.KREDITOR)
            self._debtor_radio.toggled.connect(
                lambda checked: checked
                and self._role_changed(PersonAccountRole.DEBITOR)
            )
            self._creditor_radio.toggled.connect(
                lambda checked: checked
                and self._role_changed(PersonAccountRole.KREDITOR)
            )
            role_layout.addWidget(self._debtor_radio)
            role_layout.addWidget(self._creditor_radio)
            role_layout.addStretch()
            form.addRow("Kontoart", role_layout)

        self._number = QLineEdit()
        if existing is None:
            self._number.setText(repository.suggest_account_number(company_id=company_id, role=role))
            self._number.setPlaceholderText("Fünfstellige Kontonummer")
            self._number.textEdited.connect(self._number_edited)
        else:
            self._number.setText(existing.account_number)
            self._number.setReadOnly(True)
        form.addRow("Kontonummer", self._number)

        self._partner_choice: QComboBox | None = None
        if existing is None:
            self._partner_choice = QComboBox()
            self._partner_choice.addItem("Neuen Geschäftspartner anlegen", None)
            self._available_partners = {
                str(partner.partner_id): partner
                for partner in repository.available_partners(
                    company_id=company_id, role=role
                )
            }
            for partner in self._available_partners.values():
                self._partner_choice.addItem(partner.name, str(partner.partner_id))
            self._partner_choice.currentIndexChanged.connect(self._partner_changed)
            form.addRow("Geschäftspartner", self._partner_choice)

        self._name = QLineEdit()
        if existing is not None:
            self._name.setText(existing.partner.name)
        form.addRow("Name / Firma", self._name)

        self._active = QCheckBox("Personenkonto aktiv")
        self._active.setChecked(existing.account.is_active if existing else True)
        if existing is None:
            self._active.setVisible(False)
        form.addRow("Status", self._active)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self._partner_changed()

    def _number_edited(self, _text: str) -> None:
        if not self._updating_number:
            self._number_is_manual = True

    def _role_changed(self, role: PersonAccountRole) -> None:
        if self._existing is not None:
            return
        if role is self._role:
            return
        replace_number = not self._number_is_manual

        self._role = role
        self._heading.setText(
            f"{'Debitor' if role is PersonAccountRole.DEBITOR else 'Kreditor'} "
            "– Geschäftspartner und Personenkonto"
        )
        self._refresh_partners()
        try:
            suggestion = self._repository.suggest_account_number(
                company_id=self._company_id, role=role
            )
        except (TypeError, ValueError) as exc:
            QMessageBox.warning(self, "Personenkonto", str(exc))
            return

        if self._number_is_manual:
            answer = QMessageBox.question(
                self,
                "Kontonummer ändern?",
                f"Die Kontonummer wurde manuell geändert. Soll sie durch den "
                f"Nummernvorschlag {suggestion} für die neue Kontoart ersetzt werden?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            replace_number = answer == QMessageBox.StandardButton.Yes

        if replace_number:
            self._updating_number = True
            self._number.setText(suggestion)
            self._updating_number = False
            self._number_is_manual = False

    def _refresh_partners(self) -> None:
        if self._partner_choice is None:
            return
        selected_id = self._partner_choice.currentData()
        partners = self._repository.available_partners(
            company_id=self._company_id, role=self._role
        )
        self._available_partners = {str(partner.partner_id): partner for partner in partners}
        self._partner_choice.blockSignals(True)
        self._partner_choice.clear()
        self._partner_choice.addItem("Neuen Geschäftspartner anlegen", None)
        for partner in partners:
            self._partner_choice.addItem(partner.name, str(partner.partner_id))
        index = self._partner_choice.findData(selected_id)
        if selected_id is not None and index < 0:
            self._name.clear()
        self._partner_choice.setCurrentIndex(index if index >= 0 else 0)
        self._partner_choice.blockSignals(False)
        self._partner_changed()

    def _partner_changed(self, *_args: object) -> None:
        if self._partner_choice is None:
            return
        partner_id = self._partner_choice.currentData()
        partner = self._available_partners.get(partner_id) if partner_id else None
        if partner is None:
            self._name.setEnabled(True)
            if not self._name.text():
                self._name.setText("")
        else:
            self._name.setText(partner.name)
            self._name.setEnabled(False)

    def _save(self) -> None:
        try:
            if self._existing is None:
                partner_id_value = (
                    self._partner_choice.currentData()
                    if self._partner_choice is not None
                    else None
                )
                self.saved = self._repository.create(
                    company_id=self._company_id,
                    role=self._role,
                    name=self._name.text(),
                    account_number=self._number.text(),
                    partner_id=UUID(partner_id_value) if partner_id_value else None,
                )
            else:
                self.saved = self._repository.update(
                    company_id=self._company_id,
                    account_number=self._existing.account_number,
                    name=self._name.text(),
                    is_active=self._active.isChecked(),
                )
        except (TypeError, ValueError) as exc:
            QMessageBox.warning(self, "Personenkonto", str(exc))
            return
        self.accept()

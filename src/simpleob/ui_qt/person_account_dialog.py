"""Dialog zur gemeinsamen Pflege von Personenkonten und Geschäftspartnern."""

from uuid import UUID

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from simpleob.database.person_account_repository import PersonAccountRepository
from simpleob.domain.business_partner import BusinessPartner
from simpleob.domain.person_account import PersonAccount
from simpleob.domain.person_account_role import PersonAccountRole


class PersonAccountDialog(QDialog):
    """Erfasst oder bearbeitet Personenkonten eines Geschäftspartners."""

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
        self._repository = repository
        self._existing = existing
        self._role = existing.role if existing is not None else role
        self._selected_partner: BusinessPartner | None = None
        self._partner_accounts: dict[PersonAccountRole, PersonAccount] = {}
        self._number_fields: dict[PersonAccountRole, QLineEdit] = {}
        self._number_labels: dict[PersonAccountRole, QLabel] = {}
        self._role_checks: dict[PersonAccountRole, QCheckBox] = {}
        self._manual_numbers: set[PersonAccountRole] = set()
        self._updating_numbers: set[PersonAccountRole] = set()
        self._initial_role = role
        self._new_role_selection = {
            PersonAccountRole.DEBITOR: role is PersonAccountRole.DEBITOR,
            PersonAccountRole.KREDITOR: role is PersonAccountRole.KREDITOR,
        }
        self._last_partner_id: str | None = None
        self.saved: PersonAccount | None = None
        self.saved_accounts: tuple[PersonAccount, ...] = ()

        label = "Debitor" if role is PersonAccountRole.DEBITOR else "Kreditor"
        self.setWindowTitle(
            f"Personenkonto {label} bearbeiten"
            if existing
            else "Neues Personenkonto"
        )
        self.setMinimumWidth(560)

        layout = QVBoxLayout(self)
        self._heading = QLabel(
            f"{label} – Geschäftspartner und Personenkonto"
            if existing
            else "Geschäftspartner und Personenkonten"
        )
        layout.addWidget(self._heading)
        form = QFormLayout()

        self._partner_choice: QComboBox | None = None
        if existing is None:
            self._partner_choice = QComboBox()
            self._partner_choice.addItem("Neuen Geschäftspartner anlegen", None)
            self._available_partners = {
                str(partner.partner_id): partner
                for partner in repository.partners_for_company(company_id=company_id)
            }
            for partner in self._available_partners.values():
                self._partner_choice.addItem(partner.name, str(partner.partner_id))
            self._partner_choice.currentIndexChanged.connect(self._partner_changed)
            form.addRow("Geschäftspartner", self._partner_choice)

        self._name = QLineEdit()
        if existing is not None:
            self._name.setText(existing.partner.name)
        form.addRow("Name / Firma", self._name)

        self._number: QLineEdit | None = None
        if existing is None:
            role_layout = QHBoxLayout()
            for account_role, text in (
                (PersonAccountRole.DEBITOR, "Debitor"),
                (PersonAccountRole.KREDITOR, "Kreditor"),
            ):
                check = QCheckBox(text)
                check.setChecked(self._new_role_selection[account_role])
                check.toggled.connect(
                    lambda checked, current_role=account_role: self._role_toggled(
                        current_role, checked
                    )
                )
                self._role_checks[account_role] = check
                role_layout.addWidget(check)
            role_layout.addStretch()
            form.addRow("Personenkonten", role_layout)

            for account_role, text in (
                (PersonAccountRole.DEBITOR, "Debitorenkontonummer"),
                (PersonAccountRole.KREDITOR, "Kreditorenkontonummer"),
            ):
                number_label = QLabel(text)
                number = QLineEdit()
                number.setPlaceholderText("Fünfstellige Kontonummer")
                number.textEdited.connect(
                    lambda _value, current_role=account_role: self._number_edited(
                        current_role
                    )
                )
                self._number_labels[account_role] = number_label
                self._number_fields[account_role] = number
                form.addRow(number_label, number)
            self._number = self._number_fields[role]
        else:
            self._number = QLineEdit(existing.account_number)
            self._number.setReadOnly(True)
            form.addRow("Kontonummer", self._number)

        self._active = QCheckBox("Personenkonto aktiv")
        self._active.setChecked(existing.account.is_active if existing else True)
        if existing is None:
            self._active.setVisible(False)
        form.addRow("Status", self._active)
        layout.addLayout(form)

        self._validation_message = QLabel()
        self._validation_message.setWordWrap(True)
        layout.addWidget(self._validation_message)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        if existing is None:
            self._refresh_new_partner_roles()
            self._partner_changed()

    def _number_edited(self, role: PersonAccountRole) -> None:
        if role not in self._updating_numbers:
            self._manual_numbers.add(role)

    def _set_number(self, role: PersonAccountRole, value: str) -> None:
        self._updating_numbers.add(role)
        self._number_fields[role].setText(value)
        self._updating_numbers.discard(role)

    def _ensure_number_suggestion(self, role: PersonAccountRole) -> None:
        if self._number_fields[role].text() or role in self._manual_numbers:
            return
        try:
            number = self._repository.suggest_account_number(
                company_id=self._company_id, role=role
            )
        except (TypeError, ValueError) as exc:
            QMessageBox.warning(self, "Personenkonto", str(exc))
            return
        self._set_number(role, number)

    def _role_toggled(self, role: PersonAccountRole, checked: bool) -> None:
        if self._selected_partner is None:
            self._new_role_selection[role] = checked
        self._update_role_row(role)
        self._update_validation_message()

    def _refresh_new_partner_roles(self) -> None:
        for role, check in self._role_checks.items():
            check.blockSignals(True)
            check.setEnabled(True)
            check.setChecked(self._new_role_selection[role])
            check.blockSignals(False)
        self._partner_accounts = {}
        for role in self._role_checks:
            self._update_role_row(role)
        self._update_validation_message()

    def _partner_changed(self, *_args: object) -> None:
        if self._partner_choice is None:
            return
        partner_id = self._partner_choice.currentData()
        if partner_id is None:
            if self._last_partner_id is not None:
                self._name.clear()
                self._name.setEnabled(True)
                self._refresh_new_partner_roles()
            else:
                self._name.setEnabled(True)
            self._selected_partner = None
            self._partner_accounts = {}
            self._last_partner_id = None
            self._update_validation_message()
            return

        if self._last_partner_id is None:
            self._new_role_selection = {
                role: check.isChecked()
                for role, check in self._role_checks.items()
            }
        partner = self._available_partners[partner_id]
        self._selected_partner = partner
        self._last_partner_id = partner_id
        self._name.setText(partner.name)
        self._name.setEnabled(False)
        self._manual_numbers.clear()
        for account_role in self._number_fields:
            self._set_number(account_role, "")
        self._partner_accounts = {
            account.role: account
            for account in self._repository.accounts_for_partner(
                company_id=self._company_id, partner_id=partner.partner_id
            )
        }
        self._refresh_existing_partner_roles(partner)

    def _refresh_existing_partner_roles(self, partner: BusinessPartner) -> None:
        for role, check in self._role_checks.items():
            role_exists = (
                partner.is_customer
                if role is PersonAccountRole.DEBITOR
                else partner.is_supplier
            )
            account_exists = role in self._partner_accounts
            check.blockSignals(True)
            check.setChecked(role_exists or account_exists)
            check.setEnabled(not role_exists and not account_exists)
            check.blockSignals(False)
            self._update_role_row(role)
        self._update_validation_message()

    def _update_role_row(self, role: PersonAccountRole) -> None:
        check = self._role_checks[role]
        number = self._number_fields[role]
        label = self._number_labels[role]
        existing_account = self._partner_accounts.get(role)
        is_checked = check.isChecked()
        show_number = is_checked or existing_account is not None
        label.setVisible(show_number)
        number.setVisible(show_number)

        if existing_account is not None:
            self._set_number(role, existing_account.account_number)
            number.setReadOnly(True)
            return

        number.setReadOnly(False)
        number.setEnabled(is_checked)
        if is_checked:
            self._ensure_number_suggestion(role)

    def _update_validation_message(self) -> None:
        if self._selected_partner is None:
            selected = any(check.isChecked() for check in self._role_checks.values())
            message = "" if selected else "Mindestens eine Kontoart muss ausgewählt sein."
        else:
            roles_to_create = [
                role
                for role, check in self._role_checks.items()
                if check.isChecked() and role not in self._partner_accounts
            ]
            addable_roles = any(
                role not in self._partner_accounts for role in self._role_checks
            )
            if roles_to_create:
                message = ""
            elif addable_roles:
                message = "Mindestens eine fehlende Rolle zur Anlage auswählen."
            else:
                message = "Für diesen Geschäftspartner sind bereits alle Rollen angelegt."
        self._validation_message.setText(message)

    def _save(self) -> None:
        try:
            if self._existing is None:
                roles_to_create = {
                    role: self._number_fields[role].text()
                    for role, check in self._role_checks.items()
                    if check.isChecked() and role not in self._partner_accounts
                }
                if not roles_to_create:
                    QMessageBox.warning(
                        self,
                        "Personenkonto",
                        "Mindestens ein noch fehlendes Personenkonto muss ausgewählt sein.",
                    )
                    return
                partner_id = (
                    self._selected_partner.partner_id
                    if self._selected_partner is not None
                    else None
                )
                self.saved_accounts = self._repository.create_many(
                    company_id=self._company_id,
                    account_numbers=roles_to_create,
                    name=self._name.text(),
                    partner_id=partner_id,
                )
                self.saved = self.saved_accounts[0]
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

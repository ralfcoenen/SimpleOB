"""PySide6-Dialog zum Anlegen und Bearbeiten eines Kontos."""

from dataclasses import dataclass

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
)

from openbilanz.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
from openbilanz.accounting.statement_category import StatementCategory
from openbilanz.domain.account import Account
from openbilanz.domain.account_mapping_rule import AccountMappingRule
from openbilanz.domain.account_type import AccountType
from openbilanz.domain.template_account import TemplateAccount


@dataclass(frozen=True, slots=True)
class AccountEditorResult:
    """Ergebnis des Konteneditors."""

    account: Account
    mapping_rule: AccountMappingRule


class AccountEditorDialog(QDialog):
    """Erfasst oder bearbeitet ein Konto."""

    _ACCOUNT_TYPE_LABELS = {
        "Aktivkonto": AccountType.ASSET,
        "Passivkonto": AccountType.LIABILITY,
        "Eigenkapital": AccountType.EQUITY,
        "Ertragskonto": AccountType.REVENUE,
        "Aufwandskonto": AccountType.EXPENSE,
    }

    def __init__(
        self,
        parent,
        *,
        assets: FinancialStatementPosition,
        liabilities: FinancialStatementPosition,
        income_statement: FinancialStatementPosition,
        account: Account | None = None,
        mapping_rule: AccountMappingRule | None = None,
    ) -> None:
        super().__init__(parent)

        self._assets = assets
        self._liabilities = liabilities
        self._income_statement = income_statement
        self._account = account
        self._mapping_rule = mapping_rule
        self._is_edit_mode = account is not None

        self.result: AccountEditorResult | None = None

        self._debit_positions: dict[
            str,
            FinancialStatementPosition,
        ] = {}

        self._credit_positions: dict[
            str,
            FinancialStatementPosition,
        ] = {}

        self.setWindowTitle(
            "SimpleOB – Konto bearbeiten"
            if self._is_edit_mode
            else "SimpleOB – Neues Konto"
        )
        self.setFixedSize(850, 430)

        self._create_ui()
        self._update_mapping_choices()

        if self._is_edit_mode:
            self._load_account()
            self._name_entry.setFocus()
        else:
            self._account_number_entry.setFocus()

    def _create_ui(self) -> None:
        """Erzeugt die Benutzeroberfläche."""

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        title_label = QLabel(
            "Konto bearbeiten"
            if self._is_edit_mode
            else "Neues Konto"
        )
        title_label.setStyleSheet(
            "font-size: 18px; font-weight: bold;"
        )
        layout.addWidget(title_label)

        form = QFormLayout()
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)

        self._account_number_entry = QLineEdit()
        if self._is_edit_mode:
            self._account_number_entry.setEnabled(False)
        form.addRow(
            "Kontonummer",
            self._account_number_entry,
        )

        self._name_entry = QLineEdit()
        self._name_entry.setMinimumWidth(450)
        form.addRow(
            "Bezeichnung",
            self._name_entry,
        )

        self._account_type_box = QComboBox()
        self._account_type_box.addItems(
            tuple(self._ACCOUNT_TYPE_LABELS)
        )
        self._account_type_box.currentTextChanged.connect(
            self._on_account_type_changed
        )
        form.addRow(
            "Kontotyp",
            self._account_type_box,
        )

        self._debit_position_box = QComboBox()
        form.addRow(
            "HGB-Zuordnung Soll",
            self._debit_position_box,
        )

        self._credit_position_box = QComboBox()
        form.addRow(
            "HGB-Zuordnung Haben",
            self._credit_position_box,
        )

        self._is_active_box = QCheckBox(
            "Konto ist aktiv"
        )
        self._is_active_box.setChecked(True)
        form.addRow(
            "",
            self._is_active_box,
        )

        layout.addLayout(form)

        explanation = QLabel(
            "Die HGB-Struktur ist fest vorgegeben. "
            "Hier wird nur die Zuordnung des Kontos "
            "zu einer vorhandenen HGB-Position festgelegt."
        )
        explanation.setWordWrap(True)
        layout.addWidget(explanation)

        layout.addStretch()

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )

        save_button = buttons.button(
            QDialogButtonBox.StandardButton.Save
        )
        save_button.setText("Speichern")

        cancel_button = buttons.button(
            QDialogButtonBox.StandardButton.Cancel
        )
        cancel_button.setText("Abbrechen")

        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)

        layout.addWidget(buttons)

    def _on_account_type_changed(
        self,
        _text: str,
    ) -> None:
        """Aktualisiert die möglichen HGB-Zuordnungen."""

        self._update_mapping_choices()

    def _update_mapping_choices(self) -> None:
        """Stellt passende HGB-Positionen zum Kontotyp bereit."""

        account_type = self._selected_account_type()

        self._debit_position_box.clear()
        self._credit_position_box.clear()

        if account_type is AccountType.ASSET:
            positions = self._descendants(
                self._assets
            )

            self._set_debit_positions(
                positions
            )
            self._set_credit_positions(
                positions
            )

            self._debit_position_box.setEnabled(True)
            self._credit_position_box.setEnabled(True)

        elif account_type in (
            AccountType.LIABILITY,
            AccountType.EQUITY,
        ):
            positions = self._descendants(
                self._liabilities
            )

            self._set_debit_positions(
                positions
            )
            self._set_credit_positions(
                positions
            )

            self._debit_position_box.setEnabled(True)
            self._credit_position_box.setEnabled(True)

        elif account_type is AccountType.REVENUE:
            positions = tuple(
                position
                for position in self._descendants(
                    self._income_statement
                )
                if (
                    position.category
                    is StatementCategory.INCOME
                )
            )

            self._set_debit_positions(())
            self._set_credit_positions(
                positions
            )

            self._debit_position_box.setEnabled(False)
            self._credit_position_box.setEnabled(True)

        else:
            positions = tuple(
                position
                for position in self._descendants(
                    self._income_statement
                )
                if (
                    position.category
                    is StatementCategory.EXPENSE
                )
            )

            self._set_debit_positions(
                positions
            )
            self._set_credit_positions(())

            self._debit_position_box.setEnabled(True)
            self._credit_position_box.setEnabled(False)

    def _set_debit_positions(
        self,
        positions: tuple[
            FinancialStatementPosition,
            ...,
        ],
    ) -> None:
        """Setzt die auswählbaren Sollpositionen."""

        self._debit_positions = {
            self._position_display_name(position):
                position
            for position in positions
        }

        self._debit_position_box.addItem("")

        for display_name in self._debit_positions:
            self._debit_position_box.addItem(
                display_name
            )

    def _set_credit_positions(
        self,
        positions: tuple[
            FinancialStatementPosition,
            ...,
        ],
    ) -> None:
        """Setzt die auswählbaren Habenpositionen."""

        self._credit_positions = {
            self._position_display_name(position):
                position
            for position in positions
        }

        self._credit_position_box.addItem("")

        for display_name in self._credit_positions:
            self._credit_position_box.addItem(
                display_name
            )

    def _save(self) -> None:
        """Validiert die Eingaben und erzeugt das Konto."""

        try:
            account_number = (
                self._account_number_entry
                .text()
                .strip()
            )

            name = (
                self._name_entry
                .text()
                .strip()
            )

            account_type = (
                self._selected_account_type()
            )

            template = TemplateAccount(
                account_number=account_number,
                name=name,
                account_type=account_type,
            )

            account = Account(
                template=template,
                is_active=self._is_active_box.isChecked(),
            )

            debit_position = (
                self._debit_positions.get(
                    self._debit_position_box.currentText()
                )
            )

            credit_position = (
                self._credit_positions.get(
                    self._credit_position_box.currentText()
                )
            )

            self._validate_mapping(
                account_type=account_type,
                debit_position=debit_position,
                credit_position=credit_position,
            )

            mapping_rule = AccountMappingRule(
                account_number=account.number,
                debit_position=debit_position,
                credit_position=credit_position,
            )

        except (TypeError, ValueError) as exc:
            QMessageBox.critical(
                self,
                (
                    "Konto kann nicht geändert werden"
                    if self._is_edit_mode
                    else "Konto kann nicht angelegt werden"
                ),
                str(exc),
            )
            return

        self.result = AccountEditorResult(
            account=account,
            mapping_rule=mapping_rule,
        )

        self.accept()

    @staticmethod
    def _validate_mapping(
        *,
        account_type: AccountType,
        debit_position: (
            FinancialStatementPosition | None
        ),
        credit_position: (
            FinancialStatementPosition | None
        ),
    ) -> None:
        """Prüft die notwendige HGB-Zuordnung."""

        if (
            account_type is AccountType.REVENUE
            and credit_position is None
        ):
            raise ValueError(
                "Für ein Ertragskonto muss eine "
                "Haben-HGB-Zuordnung gewählt werden."
            )

        if (
            account_type is AccountType.EXPENSE
            and debit_position is None
        ):
            raise ValueError(
                "Für ein Aufwandskonto muss eine "
                "Soll-HGB-Zuordnung gewählt werden."
            )

        if (
            account_type
            in (
                AccountType.ASSET,
                AccountType.LIABILITY,
                AccountType.EQUITY,
            )
            and debit_position is None
            and credit_position is None
        ):
            raise ValueError(
                "Für ein Bilanzkonto muss mindestens "
                "eine HGB-Zuordnung gewählt werden."
            )

    def _selected_account_type(
        self,
    ) -> AccountType:
        """Liefert den ausgewählten Kontotyp."""

        try:
            return self._ACCOUNT_TYPE_LABELS[
                self._account_type_box.currentText()
            ]
        except KeyError as exc:
            raise ValueError(
                "Bitte wählen Sie einen Kontotyp."
            ) from exc

    @staticmethod
    def _descendants(
        root: FinancialStatementPosition,
    ) -> tuple[
        FinancialStatementPosition,
        ...,
    ]:
        """Liefert alle Positionen unterhalb einer HGB-Wurzel."""

        result: list[
            FinancialStatementPosition
        ] = []

        def collect(
            position: FinancialStatementPosition,
        ) -> None:
            for child in position.children:
                result.append(
                    child
                )
                collect(
                    child
                )

        collect(root)

        return tuple(result)

    @staticmethod
    def _position_display_name(
        position: FinancialStatementPosition,
    ) -> str:
        """Liefert die lesbare Darstellung einer HGB-Position."""

        return (
            f"{position.code} – "
            f"{position.name}"
        )

    def _load_account(self) -> None:
        """Übernimmt die Werte eines vorhandenen Kontos."""

        if self._account is None:
            return

        self._account_number_entry.setText(
            self._account.number
        )
        self._name_entry.setText(
            self._account.name
        )
        self._is_active_box.setChecked(
            self._account.is_active
        )

        account_type_label = next(
            label
            for label, account_type
            in self._ACCOUNT_TYPE_LABELS.items()
            if account_type is self._account.account_type
        )

        self._account_type_box.setCurrentText(
            account_type_label
        )

        self._update_mapping_choices()

        if self._mapping_rule is None:
            return

        if self._mapping_rule.debit_position is not None:
            self._debit_position_box.setCurrentText(
                self._position_display_name(
                    self._mapping_rule.debit_position
                )
            )

        if self._mapping_rule.credit_position is not None:
            self._credit_position_box.setCurrentText(
                self._position_display_name(
                    self._mapping_rule.credit_position
                )
            )

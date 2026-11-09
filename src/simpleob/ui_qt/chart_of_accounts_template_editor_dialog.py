"""Editor für Kontenrahmen-Vorlagen ohne Datenbankzugriff."""

from collections.abc import Callable
from dataclasses import fields, replace
from pathlib import Path

from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from simpleob.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
from simpleob.domain.account import Account
from simpleob.domain.account_mapping_rule import AccountMappingRule
from simpleob.domain.account_type import AccountType
from simpleob.domain.chart_of_accounts_template import (
    ChartOfAccountsTemplate,
)
from simpleob.domain.template_account import TemplateAccount
from simpleob.importers.chart_of_accounts_template_bundle_importer import (
    ChartOfAccountsTemplateBundle,
    ChartOfAccountsTemplateBundleImporter,
)
from simpleob.ui_qt.account_configuration_dialog import (
    AccountConfigurationDialog,
)
from simpleob.ui_qt.account_editor_dialog import AccountEditorDialog


class ChartOfAccountsTemplateEditorDialog(QDialog):
    """Bearbeitet ein Kontenrahmen-Bundle ausschließlich im Arbeitsspeicher."""

    _TYPE_LABELS = {
        AccountType.ASSET: "Aktivkonto",
        AccountType.LIABILITY: "Passivkonto",
        AccountType.EQUITY: "Eigenkapital",
        AccountType.REVENUE: "Ertragskonto",
        AccountType.EXPENSE: "Aufwandskonto",
    }
    _CONTROL_LABELS = {
        "opening_balance_account": "Eröffnungsbilanzkonto",
        "income_summary_account": "GuV-Sammelkonto",
        "profit_account": "Jahresüberschuss",
        "loss_account": "Jahresfehlbetrag",
        "profit_loss_carryforward_account": "Gewinn-/Verlustvortrag",
        "statutory_reserve_account": "Gesetzliche Rücklage",
        "other_revenue_reserves_account": "Andere Gewinnrücklagen",
        "distribution_liability_account": "Ausschüttungsverbindlichkeit",
        "depreciation_expense_account": "Abschreibungsaufwand",
        "fixed_asset_disposal_gain_account": "Ertrag aus Anlagenabgang",
        "fixed_asset_disposal_loss_account": "Verlust aus Anlagenabgang",
    }
    _VAT_LABELS = {
        "input_tax_7": "Vorsteuer 7 %",
        "input_tax_19": "Vorsteuer 19 %",
        "output_tax_7": "Umsatzsteuer 7 %",
        "output_tax_19": "Umsatzsteuer 19 %",
    }
    _ROLE_LABELS = {
        "cash_accounts": "Kontenrolle: Kasse",
        "bank_accounts": "Kontenrolle: Bank",
        "general_rate_sales_accounts": "Kontenrolle: Umsatzerlöse",
        "customer_receivables": "Kontenrolle: Kundenforderungen",
        "supplier_payables": "Kontenrolle: Lieferantenverbindlichkeiten",
        "customer_credit_balances": "Kontenrolle: Kundenguthaben",
        "supplier_credit_balances": "Kontenrolle: Lieferantenguthaben",
    }

    def __init__(
        self,
        parent,
        *,
        bundle: ChartOfAccountsTemplateBundle,
        bundle_importer: ChartOfAccountsTemplateBundleImporter,
        templates_directory: Path | None = None,
        prepare_bundle_for_save: (
            Callable[
                [ChartOfAccountsTemplateBundle],
                ChartOfAccountsTemplateBundle | None,
            ]
            | None
        ) = None,
        taxonomy_choices_provider: (
            Callable[
                [FinancialStatementPosition],
                tuple[tuple[str, str], ...],
            ]
            | None
        ) = None,
        assets: FinancialStatementPosition,
        liabilities: FinancialStatementPosition,
        income_statement: FinancialStatementPosition,
    ) -> None:
        super().__init__(parent)
        self._bundle_importer = bundle_importer
        self._templates_directory = templates_directory
        self._prepare_bundle_for_save = prepare_bundle_for_save
        self._taxonomy_choices_provider = taxonomy_choices_provider
        self._assets = assets
        self._liabilities = liabilities
        self._income_statement = income_statement
        self._bundle = replace(
            bundle,
            taxonomy_mappings=(
                dict(bundle.taxonomy_mappings)
                if bundle.taxonomy_mappings is not None
                else None
            ),
        )
        self._confirmed_hgb_exceptions: set[str] = set()
        self.result: ChartOfAccountsTemplateBundle | None = None

        self.setWindowTitle("Kontenrahmen bearbeiten")
        self.resize(1050, 650)
        self.setMinimumSize(800, 480)
        self._create_ui()
        self._refresh_table()

    def _create_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Kontenrahmen bearbeiten"))

        self._search_entry = QLineEdit()
        self._search_entry.setPlaceholderText(
            "Kontonummer oder Bezeichnung suchen …"
        )
        self._search_entry.textChanged.connect(self._filter_rows)
        layout.addWidget(self._search_entry)

        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(
            ("Kontonummer", "Bezeichnung", "Kontotyp", "HGB-Zuordnung")
        )
        self._table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self._table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self._table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self._table.setSortingEnabled(False)
        self._table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self._table, 1)

        actions = QHBoxLayout()
        new_button = QPushButton("Neues Konto")
        new_button.clicked.connect(self._add_account)
        actions.addWidget(new_button)
        edit_button = QPushButton("Bearbeiten")
        edit_button.clicked.connect(self._edit_account)
        actions.addWidget(edit_button)
        remove_button = QPushButton("Entfernen")
        remove_button.clicked.connect(self._remove_account)
        actions.addWidget(remove_button)
        self._configure_accounts_button = QPushButton(
            "Systemkonten und Kontenrollen …"
        )
        self._configure_accounts_button.clicked.connect(
            self._configure_account_settings
        )
        actions.addWidget(self._configure_accounts_button)
        save_template_button = QPushButton("Als Vorlage speichern …")
        save_template_button.clicked.connect(self._save_as_template)
        actions.addWidget(save_template_button)
        actions.addStretch()
        layout.addLayout(actions)

        buttons = QDialogButtonBox()
        apply_button = QPushButton("Änderungen übernehmen")
        apply_button.clicked.connect(self._apply)
        buttons.addButton(
            apply_button,
            QDialogButtonBox.ButtonRole.AcceptRole,
        )
        cancel_button = QPushButton("Abbrechen")
        cancel_button.clicked.connect(self.reject)
        buttons.addButton(
            cancel_button,
            QDialogButtonBox.ButtonRole.RejectRole,
        )
        layout.addWidget(buttons)

    def _configure_account_settings(self) -> None:
        """Bearbeitet Kontenzuordnungen in der Vorlagen-Arbeitskopie."""

        accounts = tuple(
            Account(template=account)
            for account in self._bundle.chart.accounts
        )
        dialog = AccountConfigurationDialog(
            self,
            accounts=accounts,
            control_accounts=self._bundle.control_accounts,
            vat_accounts=self._bundle.vat_accounts,
            account_roles=self._bundle.account_roles,
            for_new_company=True,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted or dialog.result is None:
            return

        control_accounts, vat_accounts, account_roles = dialog.result
        candidate = replace(
            self._bundle,
            control_accounts=control_accounts,
            vat_accounts=vat_accounts,
            account_roles=account_roles,
        )
        try:
            self._bundle_importer.validate(
                candidate,
                require_account_configuration=False,
            )
        except (TypeError, ValueError) as exc:
            QMessageBox.critical(
                self,
                "Kontenkonfiguration ungültig",
                str(exc),
            )
            return

        self._bundle = candidate

    def _refresh_table(self) -> None:
        self._table.setRowCount(len(self._bundle.chart.accounts))
        rules = {
            rule.account_number: rule
            for rule in self._bundle.chart.account_mapping_rules
        }
        for row, account in enumerate(self._bundle.chart.accounts):
            rule = rules.get(account.account_number)
            mapping = self._mapping_label(rule)
            for column, value in enumerate(
                (
                    account.account_number,
                    account.name,
                    self._TYPE_LABELS[account.account_type],
                    mapping,
                )
            ):
                self._table.setItem(row, column, QTableWidgetItem(value))
        self._filter_rows(self._search_entry.text())
        self._table.resizeColumnsToContents()

    @staticmethod
    def _mapping_label(rule: AccountMappingRule | None) -> str:
        if rule is None:
            return "Keine Zuordnung"
        labels = []
        if rule.debit_position is not None:
            labels.append(f"Soll: {rule.debit_position.code}")
        if rule.credit_position is not None:
            labels.append(f"Haben: {rule.credit_position.code}")
        return "; ".join(labels)

    def _filter_rows(self, search_text: str) -> None:
        needle = search_text.strip().casefold()
        for row in range(self._table.rowCount()):
            number = self._table.item(row, 0).text().casefold()
            name = self._table.item(row, 1).text().casefold()
            self._table.setRowHidden(
                row,
                bool(needle and needle not in number and needle not in name),
            )

    def _selected_account(self) -> TemplateAccount | None:
        rows = self._table.selectionModel().selectedRows()
        if not rows:
            return None
        account_number = self._table.item(rows[0].row(), 0).text()
        return next(
            (
                account
                for account in self._bundle.chart.accounts
                if account.account_number == account_number
            ),
            None,
        )

    def _edit_dialog(
        self,
        *,
        account: TemplateAccount | None,
        mapping_rule: AccountMappingRule | None,
        hgb_mapping_required: bool = True,
    ) -> AccountEditorDialog:
        return AccountEditorDialog(
            self,
            assets=self._assets,
            liabilities=self._liabilities,
            income_statement=self._income_statement,
            account=(Account(template=account) if account is not None else None),
            mapping_rule=mapping_rule,
            template_mode=True,
            hgb_mapping_required=hgb_mapping_required,
            taxonomy_concept_name=(
                (self._bundle.taxonomy_mappings or {}).get(
                    account.account_number
                )
                if account is not None
                else None
            ),
            taxonomy_choices_provider=self._taxonomy_choices_provider,
        )

    def _add_account(self) -> None:
        dialog = self._edit_dialog(account=None, mapping_rule=None)
        dialog.exec()
        if dialog.result is None:
            return
        self._store_edited_account(old_number=None, result=dialog.result)

    def _edit_account(self) -> None:
        account = self._selected_account()
        if account is None:
            QMessageBox.information(
                self,
                "Konto bearbeiten",
                "Bitte wählen Sie zuerst ein Konto aus.",
            )
            return
        current_rule = next(
            (
                rule
                for rule in self._bundle.chart.account_mapping_rules
                if rule.account_number == account.account_number
            ),
            None,
        )
        old_number = account.account_number
        dialog = self._edit_dialog(
            account=account,
            mapping_rule=current_rule,
            hgb_mapping_required=(
                old_number not in self._confirmed_hgb_exceptions
            ),
        )
        dialog.exec()
        if dialog.result is None:
            return
        self._store_edited_account(old_number=old_number, result=dialog.result)

    def _store_edited_account(self, *, old_number: str | None, result) -> None:
        new_number = result.account.number
        accounts = list(self._bundle.chart.accounts)
        if any(
            account.account_number == new_number
            and account.account_number != old_number
            for account in accounts
        ):
            QMessageBox.critical(
                self,
                "Kontonummer bereits vorhanden",
                f"Die Kontonummer {new_number} ist bereits vergeben.",
            )
            return

        references: tuple[str, ...] = ()
        if old_number is not None and old_number != new_number:
            references = self._references_for(old_number)
            if references:
                details = "\n".join(f"• {reference}" for reference in references)
                answer = QMessageBox.question(
                    self,
                    "Referenzen übernehmen?",
                    f"Die Kontonummer {old_number} wird in folgenden "
                    "Zuordnungen verwendet:\n\n"
                    f"{details}\n\n"
                    f"Sollen diese Referenzen gemeinsam auf {new_number} "
                    "umgeschrieben werden? Ohne Übernahme kann die "
                    "Nummernänderung nicht durchgeführt werden.",
                    QMessageBox.StandardButton.Yes
                    | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                if answer != QMessageBox.StandardButton.Yes:
                    return

        if old_number is None:
            accounts.append(result.account.template)
            rules = list(self._bundle.chart.account_mapping_rules)
        else:
            accounts = [
                result.account.template
                if account.account_number == old_number
                else account
                for account in accounts
            ]
            rules = [
                rule
                for rule in self._bundle.chart.account_mapping_rules
                if rule.account_number != old_number
            ]
            if old_number in self._confirmed_hgb_exceptions:
                self._confirmed_hgb_exceptions.remove(old_number)

        if result.mapping_rule is not None:
            rules.append(result.mapping_rule)
        if not result.hgb_mapping_required and result.mapping_rule is None:
            self._confirmed_hgb_exceptions.add(new_number)

        self._bundle = replace(
            self._bundle,
            chart=ChartOfAccountsTemplate(
                name=self._bundle.chart.name,
                accounts=tuple(accounts),
                account_mapping_rules=tuple(rules),
            ),
        )
        if old_number is not None and old_number != new_number and references:
            self._rewrite_references(old_number, new_number)
        elif old_number is not None and old_number != new_number:
            self._move_hgb_exception(old_number, new_number)
        if result.taxonomy_mapping_changed:
            mappings = dict(self._bundle.taxonomy_mappings or {})
            if old_number is not None:
                mappings.pop(old_number, None)
            if result.taxonomy_concept_name is not None:
                mappings[new_number] = result.taxonomy_concept_name
            else:
                mappings.pop(new_number, None)
            self._bundle = replace(
                self._bundle,
                taxonomy_mappings=mappings,
            )
        self._refresh_table()

    def _move_hgb_exception(self, old_number: str, new_number: str) -> None:
        if old_number in self._confirmed_hgb_exceptions:
            self._confirmed_hgb_exceptions.remove(old_number)
            self._confirmed_hgb_exceptions.add(new_number)

    def _references_for(self, account_number: str) -> tuple[str, ...]:
        references: list[str] = []
        if self._bundle.control_accounts is not None:
            for field in fields(self._bundle.control_accounts):
                if getattr(self._bundle.control_accounts, field.name) == account_number:
                    references.append(
                        "Systemkonto: "
                        + self._CONTROL_LABELS.get(field.name, field.name)
                    )
        if self._bundle.vat_accounts is not None:
            for field in fields(self._bundle.vat_accounts):
                if getattr(self._bundle.vat_accounts, field.name) == account_number:
                    references.append(
                        "Steuerkonto: "
                        + self._VAT_LABELS.get(field.name, field.name)
                    )
        if self._bundle.account_roles is not None:
            for field in fields(self._bundle.account_roles):
                if account_number in getattr(self._bundle.account_roles, field.name):
                    references.append(
                        self._ROLE_LABELS.get(field.name, field.name)
                    )
        if account_number in (self._bundle.taxonomy_mappings or {}):
            concept = self._bundle.taxonomy_mappings[account_number]
            references.append(f"E-Bilanz-Taxonomiezuordnung: {concept}")
        return tuple(references)

    def _rewrite_references(self, old_number: str, new_number: str) -> None:
        controls = self._bundle.control_accounts
        if controls is not None:
            changes = {
                field.name: new_number
                for field in fields(controls)
                if getattr(controls, field.name) == old_number
            }
            if changes:
                controls = replace(controls, **changes)

        vat = self._bundle.vat_accounts
        if vat is not None:
            changes = {
                field.name: new_number
                for field in fields(vat)
                if getattr(vat, field.name) == old_number
            }
            if changes:
                vat = replace(vat, **changes)

        roles = self._bundle.account_roles
        if roles is not None:
            changes = {}
            for field in fields(roles):
                numbers = getattr(roles, field.name)
                if old_number in numbers:
                    changes[field.name] = frozenset(
                        new_number if number == old_number else number
                        for number in numbers
                    )
            if changes:
                roles = replace(roles, **changes)

        mappings = dict(self._bundle.taxonomy_mappings or {})
        if old_number in mappings:
            mappings[new_number] = mappings.pop(old_number)
        self._bundle = replace(
            self._bundle,
            control_accounts=controls,
            vat_accounts=vat,
            account_roles=roles,
            taxonomy_mappings=mappings,
        )

    def _remove_account(self) -> None:
        account = self._selected_account()
        if account is None:
            QMessageBox.information(
                self,
                "Konto entfernen",
                "Bitte wählen Sie zuerst ein Konto aus.",
            )
            return
        references = self._references_for(account.account_number)
        if references:
            details = "\n".join(f"• {reference}" for reference in references)
            QMessageBox.warning(
                self,
                "Konto wird verwendet",
                "Das Konto kann erst entfernt werden, wenn folgende "
                "Zuordnungen korrigiert wurden:\n\n"
                f"{details}",
            )
            return
        if len(self._bundle.chart.accounts) <= 1:
            QMessageBox.information(
                self,
                "Konto entfernen",
                "Ein Kontenrahmen muss mindestens ein Konto enthalten.",
            )
            return
        answer = QMessageBox.question(
            self,
            "Konto entfernen",
            f"Konto {account.account_number} – {account.name} "
            "aus dieser Arbeitskopie entfernen?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        number = account.account_number
        self._bundle = replace(
            self._bundle,
            chart=ChartOfAccountsTemplate(
                name=self._bundle.chart.name,
                accounts=tuple(
                    item
                    for item in self._bundle.chart.accounts
                    if item.account_number != number
                ),
                account_mapping_rules=tuple(
                    rule
                    for rule in self._bundle.chart.account_mapping_rules
                    if rule.account_number != number
                ),
            ),
        )
        self._confirmed_hgb_exceptions.discard(number)
        self._refresh_table()

    def _apply(self) -> None:
        try:
            self._bundle_importer.validate(
                self._bundle,
                require_account_configuration=False,
            )
        except (TypeError, ValueError) as exc:
            QMessageBox.critical(
                self,
                "Kontenrahmen ungültig",
                str(exc),
            )
            return
        self.result = replace(
            self._bundle,
            taxonomy_mappings=(
                dict(self._bundle.taxonomy_mappings)
                if self._bundle.taxonomy_mappings is not None
                else None
            ),
        )
        self.accept()

    def _save_as_template(self) -> None:
        if self._templates_directory is None:
            QMessageBox.critical(
                self,
                "Vorlagenordner fehlt",
                "Der Speicherort für eigene Kontenrahmenvorlagen ist nicht "
                "konfiguriert.",
            )
            return

        name, accepted = QInputDialog.getText(
            self,
            "Kontenrahmen als Vorlage speichern",
            "Name der eigenen Vorlage:",
            QLineEdit.EchoMode.Normal,
            self._bundle.chart.name,
        )
        if not accepted:
            return

        bundle = self._bundle
        if (
            bundle.control_accounts is None
            or bundle.vat_accounts is None
            or bundle.account_roles is None
        ):
            if self._prepare_bundle_for_save is None:
                QMessageBox.critical(
                    self,
                    "Kontenzuordnungen fehlen",
                    "Vor dem Speichern der wiederverwendbaren Vorlage müssen "
                    "Systemkonten, Umsatzsteuer- und Vorsteuerkonten sowie "
                    "Kontenrollen vollständig konfiguriert sein.",
                )
                return
            bundle = self._prepare_bundle_for_save(bundle)
            if bundle is None:
                return

        try:
            saved_path = self._bundle_importer.save_template(
                bundle,
                self._templates_directory,
                name,
            )
        except (OSError, TypeError, ValueError) as exc:
            QMessageBox.critical(
                self,
                "Vorlage konnte nicht gespeichert werden",
                str(exc),
            )
            return

        self._bundle = replace(
            bundle,
            taxonomy_version=bundle.taxonomy_version or "6.9",
            taxonomy_mappings=(
                dict(bundle.taxonomy_mappings)
                if bundle.taxonomy_mappings is not None
                else None
            ),
        )
        QMessageBox.information(
            self,
            "Vorlage gespeichert",
            "Die eigene Kontenrahmenvorlage wurde gespeichert. Der Editor "
            "bleibt geöffnet.\n\n"
            f"{saved_path}",
        )

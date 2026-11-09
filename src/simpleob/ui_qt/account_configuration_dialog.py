"""PySide6-Dialog zur mandantenspezifischen Kontenkonfiguration."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from simpleob.domain.account import Account
from simpleob.domain.accounting_account_roles import (
    AccountingAccountRoles,
)
from simpleob.domain.accounting_control_accounts import (
    AccountingControlAccounts,
)
from simpleob.domain.vat_accounts import VatAccounts


class AccountConfigurationDialog(QDialog):
    """Bearbeitet Systemkonten, USt-Konten und funktionale Kontenrollen."""

    def __init__(
        self,
        parent,
        *,
        accounts: tuple[Account, ...],
        control_accounts: AccountingControlAccounts | None,
        vat_accounts: VatAccounts | None,
        account_roles: AccountingAccountRoles | None,
        for_new_company: bool = False,
    ) -> None:
        super().__init__(parent)

        self._accounts = tuple(
            sorted(
                (
                    account
                    for account in accounts
                    if account.is_active
                ),
                key=lambda account: account.number,
            )
        )

        self._control_accounts = control_accounts
        self._vat_accounts = vat_accounts
        self._for_new_company = for_new_company
        self._account_roles = account_roles or AccountingAccountRoles(
            cash_accounts=frozenset(),
            bank_accounts=frozenset(),
            general_rate_sales_accounts=frozenset(),
        )
        self._role_definitions = (
            ("Kasse", "cash_accounts"),
            ("Bank", "bank_accounts"),
            ("Umsatzerlöse allgemeiner Steuersatz", "general_rate_sales_accounts"),
            ("Kundenforderungen", "customer_receivables"),
            ("Lieferantenverbindlichkeiten", "supplier_payables"),
            ("Kundenguthaben", "customer_credit_balances"),
            ("Lieferantenguthaben", "supplier_credit_balances"),
        )
        self._role_assignments = {
            field_name: set(getattr(self._account_roles, field_name))
            for _label, field_name in self._role_definitions
        }
        self._current_role_key: str | None = None

        self.result: (
            tuple[
                AccountingControlAccounts,
                VatAccounts,
                AccountingAccountRoles,
            ]
            | None
        ) = None

        self.setWindowTitle(
            "SimpleOB – Kontenkonfiguration"
        )
        self.resize(900, 760)
        self.setMinimumSize(820, 680)

        self._create_ui()
        self._load_values()

    def _create_ui(self) -> None:
        """Erzeugt die Benutzeroberfläche."""

        layout = QVBoxLayout(self)

        title_label = QLabel("Kontenkonfiguration")
        title_label.setStyleSheet(
            "font-size: 18px; font-weight: bold;"
        )
        layout.addWidget(title_label)

        layout.addWidget(
            QLabel(
                "Die Einstellungen gelten für den neuen Kontenrahmen."
                if self._for_new_company
                else "Die Einstellungen gelten für den aktuell "
                "geöffneten Mandanten."
            )
        )

        notebook = QTabWidget()
        layout.addWidget(notebook)

        system_tab = QWidget()
        vat_tab = QWidget()
        roles_tab = QWidget()

        notebook.addTab(
            system_tab,
            "Systemkonten",
        )
        notebook.addTab(
            vat_tab,
            "USt-Konten",
        )
        notebook.addTab(
            roles_tab,
            "Kontenrollen",
        )

        self._create_system_accounts_ui(
            system_tab
        )
        self._create_vat_accounts_ui(
            vat_tab
        )
        self._create_account_roles_ui(
            roles_tab
        )

        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_button = QPushButton("Abbrechen")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        save_button = QPushButton("Übernehmen")
        save_button.clicked.connect(self._save)
        save_button.setDefault(True)
        button_layout.addWidget(save_button)

        layout.addLayout(button_layout)

    def _create_system_accounts_ui(
        self,
        parent: QWidget,
    ) -> None:
        """Erzeugt die Auswahl der technischen Systemkonten."""

        form = QFormLayout(parent)

        self._opening_balance_box = (
            self._create_account_combobox()
        )
        self._income_summary_box = (
            self._create_account_combobox()
        )
        self._profit_box = (
            self._create_account_combobox()
        )
        self._loss_box = (
            self._create_account_combobox()
        )
        self._profit_loss_carryforward_box = (
            self._create_account_combobox()
        )
        self._statutory_reserve_box = (
            self._create_account_combobox()
        )
        self._other_revenue_reserves_box = (
            self._create_account_combobox()
        )
        self._distribution_liability_box = (
            self._create_account_combobox()
        )
        self._depreciation_expense_box = (
            self._create_account_combobox()
        )
        self._fixed_asset_disposal_gain_box = (
            self._create_account_combobox()
        )
        self._fixed_asset_disposal_loss_box = (
            self._create_account_combobox()
        )

        form.addRow(
            "Eröffnungsbilanzkonto",
            self._opening_balance_box,
        )
        form.addRow(
            "GuV-Sammelkonto",
            self._income_summary_box,
        )
        form.addRow(
            "Jahresüberschuss",
            self._profit_box,
        )
        form.addRow(
            "Jahresfehlbetrag",
            self._loss_box,
        )
        form.addRow(
            "Gewinn-/Verlustvortrag",
            self._profit_loss_carryforward_box,
        )
        form.addRow(
            "Gesetzliche Rücklage",
            self._statutory_reserve_box,
        )
        form.addRow(
            "Andere Gewinnrücklagen",
            self._other_revenue_reserves_box,
        )
        form.addRow(
            "Verbindlichkeiten für offene Ausschüttungen",
            self._distribution_liability_box,
        )
        form.addRow(
            "Abschreibungsaufwand",
            self._depreciation_expense_box,
        )
        form.addRow(
            "Gewinn aus Anlagenabgang",
            self._fixed_asset_disposal_gain_box,
        )
        form.addRow(
            "Verlust aus Anlagenabgang",
            self._fixed_asset_disposal_loss_box,
        )

    def _create_vat_accounts_ui(
        self,
        parent: QWidget,
    ) -> None:
        """Erzeugt die Auswahl der Umsatzsteuerkonten."""

        form = QFormLayout(parent)

        self._input_tax_7_box = (
            self._create_account_combobox()
        )
        self._input_tax_19_box = (
            self._create_account_combobox()
        )
        self._output_tax_7_box = (
            self._create_account_combobox()
        )
        self._output_tax_19_box = (
            self._create_account_combobox()
        )

        form.addRow(
            "Vorsteuer 7 %",
            self._input_tax_7_box,
        )
        form.addRow(
            "Vorsteuer 19 %",
            self._input_tax_19_box,
        )
        form.addRow(
            "Umsatzsteuer 7 %",
            self._output_tax_7_box,
        )
        form.addRow(
            "Umsatzsteuer 19 %",
            self._output_tax_19_box,
        )

    def _create_account_roles_ui(
        self,
        parent: QWidget,
    ) -> None:
        """Erzeugt die zweigeteilte Auswahl funktionaler Kontenrollen."""

        layout = QVBoxLayout(parent)

        description = QLabel(
            "Mehrere Konten können je Rolle ausgewählt werden. "
            "Ein Konto darf nur einer dieser Rollen angehören."
        )
        description.setWordWrap(True)
        layout.addWidget(description)

        panes = QHBoxLayout()
        panes.setSpacing(12)
        layout.addLayout(panes, 1)

        roles_pane = QWidget()
        roles_layout = QVBoxLayout(roles_pane)
        roles_layout.setContentsMargins(0, 0, 0, 0)
        roles_title = QLabel("Kontenrollen")
        roles_title.setStyleSheet("font-weight: bold;")
        roles_layout.addWidget(roles_title)
        self._role_list = QListWidget()
        self._role_list.setMinimumWidth(230)
        self._role_list.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        for label, field_name in self._role_definitions:
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, field_name)
            self._role_list.addItem(item)
        self._role_list.currentRowChanged.connect(self._on_role_changed)
        roles_layout.addWidget(self._role_list, 1)
        roles_pane.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Expanding,
        )
        panes.addWidget(roles_pane)

        accounts_pane = QWidget()
        accounts_layout = QVBoxLayout(accounts_pane)
        accounts_layout.setContentsMargins(0, 0, 0, 0)
        accounts_title = QLabel("Konten der ausgewählten Rolle")
        accounts_title.setStyleSheet("font-weight: bold;")
        accounts_layout.addWidget(accounts_title)
        self._role_account_list = QListWidget()
        self._role_account_list.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self._role_account_list.itemChanged.connect(
            self._on_role_account_changed
        )
        accounts_layout.addWidget(self._role_account_list, 1)
        accounts_pane.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        panes.addWidget(accounts_pane, 1)

        self._role_list.setCurrentRow(0)

    def _on_role_changed(self, _row: int) -> None:
        """Speichert den sichtbaren Entwurf und zeigt die neue Rolle."""

        self._capture_visible_role_assignments()
        current_item = self._role_list.currentItem()
        self._current_role_key = (
            current_item.data(Qt.ItemDataRole.UserRole)
            if current_item is not None
            else None
        )
        self._populate_role_account_list()

    def _capture_visible_role_assignments(self) -> None:
        if self._current_role_key is None:
            return
        self._role_assignments[self._current_role_key] = {
            str(
                self._role_account_list.item(index).data(
                    Qt.ItemDataRole.UserRole
                )
            )
            for index in range(self._role_account_list.count())
            if self._role_account_list.item(index).checkState()
            == Qt.CheckState.Checked
        }

    def _populate_role_account_list(self) -> None:
        self._role_account_list.blockSignals(True)
        try:
            self._role_account_list.clear()
            if self._current_role_key is None:
                return
            assigned_here = self._role_assignments[self._current_role_key]
            assigned_elsewhere = {
                account_number: label
                for label, field_name in self._role_definitions
                if field_name != self._current_role_key
                for account_number in self._role_assignments[field_name]
            }
            for account in self._accounts:
                other_role = assigned_elsewhere.get(account.number)
                item = QListWidgetItem(str(account))
                item.setData(Qt.ItemDataRole.UserRole, account.number)
                if other_role is None:
                    item.setFlags(
                        item.flags()
                        | Qt.ItemFlag.ItemIsUserCheckable
                        | Qt.ItemFlag.ItemIsEnabled
                    )
                    item.setCheckState(
                        Qt.CheckState.Checked
                        if account.number in assigned_here
                        else Qt.CheckState.Unchecked
                    )
                else:
                    item.setFlags(
                        item.flags()
                        & ~Qt.ItemFlag.ItemIsUserCheckable
                        & ~Qt.ItemFlag.ItemIsEnabled
                    )
                    item.setToolTip(
                        f"Dieses Konto ist bereits der Rolle „{other_role}“ zugeordnet."
                    )
                self._role_account_list.addItem(item)
        finally:
            self._role_account_list.blockSignals(False)

    def _on_role_account_changed(self, _item: QListWidgetItem) -> None:
        self._capture_visible_role_assignments()

    def _create_account_combobox(
        self,
    ) -> QComboBox:
        """Erzeugt eine schreibgeschützte Kontenauswahl."""

        combo_box = QComboBox()
        combo_box.addItem("Bitte auswählen …", None)

        for account in self._accounts:
            combo_box.addItem(
                str(account),
                account.number,
            )

        return combo_box

    def _create_role_list(
        self,
        parent_layout: QHBoxLayout,
        *,
        title: str,
    ) -> QListWidget:
        """Erzeugt eine Mehrfachauswahlliste für eine Kontenrolle."""

        container = QWidget()
        layout = QVBoxLayout(container)

        title_label = QLabel(title)
        title_label.setStyleSheet(
            "font-weight: bold;"
        )
        title_label.setWordWrap(True)
        layout.addWidget(title_label)

        list_widget = QListWidget()
        list_widget.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
        )

        for account in self._accounts:
            item = QListWidgetItem(str(account))
            item.setData(
                256,
                account.number,
            )
            list_widget.addItem(item)

        layout.addWidget(list_widget)
        parent_layout.addWidget(container)

        return list_widget

    def _load_values(self) -> None:
        """Übernimmt die vorhandene Kontenkonfiguration."""

        if self._control_accounts is not None:
            self._select_account(
                self._opening_balance_box,
                self._control_accounts.opening_balance_account,
            )
            self._select_account(
                self._income_summary_box,
                self._control_accounts.income_summary_account,
            )
            self._select_account(
                self._profit_box,
                self._control_accounts.profit_account,
            )
            self._select_account(
                self._loss_box,
                self._control_accounts.loss_account,
            )
            self._select_account(
                self._profit_loss_carryforward_box,
                self._control_accounts.profit_loss_carryforward_account,
            )
            self._select_account(
                self._statutory_reserve_box,
                self._control_accounts.statutory_reserve_account,
            )
            self._select_account(
                self._other_revenue_reserves_box,
                self._control_accounts.other_revenue_reserves_account,
            )
            self._select_account(
                self._distribution_liability_box,
                self._control_accounts.distribution_liability_account,
            )
            self._select_account(
                self._depreciation_expense_box,
                self._control_accounts.depreciation_expense_account,
            )
            self._select_account(
                self._fixed_asset_disposal_gain_box,
                self._control_accounts.fixed_asset_disposal_gain_account,
            )
            self._select_account(
                self._fixed_asset_disposal_loss_box,
                self._control_accounts.fixed_asset_disposal_loss_account,
            )
        if self._vat_accounts is not None:
            self._select_account(self._input_tax_7_box, self._vat_accounts.input_tax_7)
            self._select_account(self._input_tax_19_box, self._vat_accounts.input_tax_19)
            self._select_account(self._output_tax_7_box, self._vat_accounts.output_tax_7)
            self._select_account(self._output_tax_19_box, self._vat_accounts.output_tax_19)

    @staticmethod
    def _select_account(
        combo_box: QComboBox,
        account_number: str,
    ) -> None:
        """Wählt ein Konto anhand seiner Kontonummer aus."""

        index = combo_box.findData(account_number)

        if index >= 0:
            combo_box.setCurrentIndex(index)
        else:
            combo_box.setCurrentIndex(-1)

    @staticmethod
    def _selected_account_number(
        combo_box: QComboBox,
    ) -> str:
        """Liefert die ausgewählte Kontonummer."""

        account_number = combo_box.currentData()

        if not isinstance(account_number, str):
            raise ValueError(
                "Bitte für jedes Feld ein vorhandenes Konto auswählen."
            )

        return account_number

    def _save(self) -> None:
        """Prüft die Eingaben und stellt das Dialogergebnis bereit."""

        self._capture_visible_role_assignments()
        try:
            control_accounts = AccountingControlAccounts(
                opening_balance_account=(
                    self._selected_account_number(
                        self._opening_balance_box
                    )
                ),
                income_summary_account=(
                    self._selected_account_number(
                        self._income_summary_box
                    )
                ),
                profit_account=(
                    self._selected_account_number(
                        self._profit_box
                    )
                ),
                loss_account=(
                    self._selected_account_number(
                        self._loss_box
                    )
                ),
                profit_loss_carryforward_account=(
                    self._selected_account_number(
                        self._profit_loss_carryforward_box
                    )
                ),
                statutory_reserve_account=(
                    self._selected_account_number(
                        self._statutory_reserve_box
                    )
                ),
                other_revenue_reserves_account=(
                    self._selected_account_number(
                        self._other_revenue_reserves_box
                    )
                ),
                distribution_liability_account=(
                    self._selected_account_number(
                        self._distribution_liability_box
                    )
                ),
                depreciation_expense_account=(
                    self._selected_account_number(
                        self._depreciation_expense_box
                    )
                ),
                fixed_asset_disposal_gain_account=(
                    self._selected_account_number(
                        self._fixed_asset_disposal_gain_box
                    )
                ),
                fixed_asset_disposal_loss_account=(
                    self._selected_account_number(
                        self._fixed_asset_disposal_loss_box
                    )
                ),
            )

            vat_accounts = VatAccounts(
                input_tax_7=(
                    self._selected_account_number(
                        self._input_tax_7_box
                    )
                ),
                input_tax_19=(
                    self._selected_account_number(
                        self._input_tax_19_box
                    )
                ),
                output_tax_7=(
                    self._selected_account_number(
                        self._output_tax_7_box
                    )
                ),
                output_tax_19=(
                    self._selected_account_number(
                        self._output_tax_19_box
                    )
                ),
            )

            account_roles = AccountingAccountRoles(
                cash_accounts=frozenset(self._role_assignments["cash_accounts"]),
                bank_accounts=frozenset(self._role_assignments["bank_accounts"]),
                general_rate_sales_accounts=frozenset(
                    self._role_assignments["general_rate_sales_accounts"]
                ),
                customer_receivables=frozenset(
                    self._role_assignments["customer_receivables"]
                ),
                supplier_payables=frozenset(
                    self._role_assignments["supplier_payables"]
                ),
                customer_credit_balances=frozenset(
                    self._role_assignments["customer_credit_balances"]
                ),
                supplier_credit_balances=frozenset(
                    self._role_assignments["supplier_credit_balances"]
                ),
            )

        except (TypeError, ValueError) as exc:
            QMessageBox.critical(
                self,
                "Kontenkonfiguration",
                str(exc),
            )
            return

        self.result = (
            control_accounts,
            vat_accounts,
            account_roles,
        )
        self.accept()

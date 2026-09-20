"""PySide6-Dialog zur mandantenspezifischen Kontenkonfiguration."""

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
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from openbilanz.domain.account import Account
from openbilanz.domain.accounting_account_roles import (
    AccountingAccountRoles,
)
from openbilanz.domain.accounting_control_accounts import (
    AccountingControlAccounts,
)
from openbilanz.domain.vat_accounts import VatAccounts


class AccountConfigurationDialog(QDialog):
    """Bearbeitet Systemkonten, USt-Konten und funktionale Kontenrollen."""

    def __init__(
        self,
        parent,
        *,
        accounts: tuple[Account, ...],
        control_accounts: AccountingControlAccounts,
        vat_accounts: VatAccounts,
        account_roles: AccountingAccountRoles,
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
        self._account_roles = account_roles

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
                "Die Einstellungen gelten für den aktuell "
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
        """Erzeugt die Mehrfachauswahl für funktionale Kontenrollen."""

        layout = QVBoxLayout(parent)

        description = QLabel(
            "Mehrere Konten können je Rolle ausgewählt werden. "
            "Ein Konto darf nur einer dieser Rollen angehören."
        )
        description.setWordWrap(True)
        layout.addWidget(description)

        roles_layout = QHBoxLayout()
        layout.addLayout(roles_layout)

        self._cash_list = self._create_role_list(
            roles_layout,
            title="Kasse",
        )
        self._bank_list = self._create_role_list(
            roles_layout,
            title="Bank",
        )
        self._general_rate_sales_list = (
            self._create_role_list(
                roles_layout,
                title=(
                    "Umsatzerlöse allgemeiner Steuersatz"
                ),
            )
        )

    def _create_account_combobox(
        self,
    ) -> QComboBox:
        """Erzeugt eine schreibgeschützte Kontenauswahl."""

        combo_box = QComboBox()

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
            (
                self._control_accounts
                .profit_loss_carryforward_account
            ),
        )
        self._select_account(
            self._depreciation_expense_box,
            (
                self._control_accounts
                .depreciation_expense_account
            ),
        )
        self._select_account(
            self._fixed_asset_disposal_gain_box,
            (
                self._control_accounts
                .fixed_asset_disposal_gain_account
            ),
        )
        self._select_account(
            self._fixed_asset_disposal_loss_box,
            (
                self._control_accounts
                .fixed_asset_disposal_loss_account
            ),
        )
        self._select_account(
            self._input_tax_7_box,
            self._vat_accounts.input_tax_7,
        )
        self._select_account(
            self._input_tax_19_box,
            self._vat_accounts.input_tax_19,
        )
        self._select_account(
            self._output_tax_7_box,
            self._vat_accounts.output_tax_7,
        )
        self._select_account(
            self._output_tax_19_box,
            self._vat_accounts.output_tax_19,
        )

        self._select_role_accounts(
            self._cash_list,
            self._account_roles.cash_accounts,
        )
        self._select_role_accounts(
            self._bank_list,
            self._account_roles.bank_accounts,
        )
        self._select_role_accounts(
            self._general_rate_sales_list,
            (
                self._account_roles
                .general_rate_sales_accounts
            ),
        )

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
    def _select_role_accounts(
        list_widget: QListWidget,
        account_numbers: frozenset[str],
    ) -> None:
        """Markiert die Konten einer vorhandenen Kontenrolle."""

        for index in range(list_widget.count()):
            item = list_widget.item(index)

            item.setSelected(
                item.data(256) in account_numbers
            )

    @staticmethod
    def _selected_account_numbers(
        list_widget: QListWidget,
    ) -> frozenset[str]:
        """Liefert die Kontonummern der markierten Einträge."""

        return frozenset(
            str(item.data(256))
            for item in list_widget.selectedItems()
        )

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
                cash_accounts=(
                    self._selected_account_numbers(
                        self._cash_list
                    )
                ),
                bank_accounts=(
                    self._selected_account_numbers(
                        self._bank_list
                    )
                ),
                general_rate_sales_accounts=(
                    self._selected_account_numbers(
                        self._general_rate_sales_list
                    )
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

"""Dialog zur mandantenspezifischen Kontenkonfiguration."""

import tkinter as tk
from tkinter import messagebox, ttk

from openbilanz.domain.account import Account
from openbilanz.domain.accounting_account_roles import (
    AccountingAccountRoles,
)
from openbilanz.domain.accounting_control_accounts import (
    AccountingControlAccounts,
)
from openbilanz.domain.vat_accounts import VatAccounts


class AccountConfigurationDialog(tk.Toplevel):
    """Bearbeitet Systemkonten, USt-Konten und funktionale Kontenrollen."""

    def __init__(
        self,
        parent: tk.Misc,
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

        self._accounts_by_display = {
            str(account): account
            for account in self._accounts
        }

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

        self.title("SimpleOB – Kontenkonfiguration")
        self.geometry("900x760")
        self.minsize(820, 680)

        self.transient(parent)
        self.grab_set()

        self._create_variables()
        self._create_ui()

    def _create_variables(self) -> None:
        """Erzeugt die Tk-Variablen für die Einzelauswahlfelder."""

        self._opening_balance_var = tk.StringVar(
            value=self._display_for_account_number(
                self._control_accounts.opening_balance_account
            )
        )
        self._income_summary_var = tk.StringVar(
            value=self._display_for_account_number(
                self._control_accounts.income_summary_account
            )
        )
        self._profit_var = tk.StringVar(
            value=self._display_for_account_number(
                self._control_accounts.profit_account
            )
        )
        self._loss_var = tk.StringVar(
            value=self._display_for_account_number(
                self._control_accounts.loss_account
            )
        )
        self._profit_loss_carryforward_var = tk.StringVar(
            value=self._display_for_account_number(
                self._control_accounts
                .profit_loss_carryforward_account
            )
        )
        self._depreciation_expense_var = tk.StringVar(
            value=self._display_for_account_number(
                self._control_accounts
                .depreciation_expense_account
            )
        )

        self._input_tax_7_var = tk.StringVar(
            value=self._display_for_account_number(
                self._vat_accounts.input_tax_7
            )
        )
        self._input_tax_19_var = tk.StringVar(
            value=self._display_for_account_number(
                self._vat_accounts.input_tax_19
            )
        )
        self._output_tax_7_var = tk.StringVar(
            value=self._display_for_account_number(
                self._vat_accounts.output_tax_7
            )
        )
        self._output_tax_19_var = tk.StringVar(
            value=self._display_for_account_number(
                self._vat_accounts.output_tax_19
            )
        )

    def _create_ui(self) -> None:
        """Erzeugt die Benutzeroberfläche."""

        container = ttk.Frame(
            self,
            padding=24,
        )
        container.pack(
            fill="both",
            expand=True,
        )

        ttk.Label(
            container,
            text="Kontenkonfiguration",
            font=("TkDefaultFont", 18, "bold"),
        ).pack(
            anchor="w",
        )

        ttk.Label(
            container,
            text=(
                "Die Einstellungen gelten für den aktuell "
                "geöffneten Mandanten."
            ),
        ).pack(
            anchor="w",
            pady=(4, 18),
        )

        notebook = ttk.Notebook(
            container
        )
        notebook.pack(
            fill="both",
            expand=True,
        )

        system_frame = ttk.Frame(
            notebook,
            padding=18,
        )
        vat_frame = ttk.Frame(
            notebook,
            padding=18,
        )
        roles_frame = ttk.Frame(
            notebook,
            padding=18,
        )

        notebook.add(
            system_frame,
            text="Systemkonten",
        )
        notebook.add(
            vat_frame,
            text="USt-Konten",
        )
        notebook.add(
            roles_frame,
            text="Kontenrollen",
        )

        self._create_system_accounts_ui(
            system_frame
        )
        self._create_vat_accounts_ui(
            vat_frame
        )
        self._create_account_roles_ui(
            roles_frame
        )

        buttons = ttk.Frame(
            container
        )
        buttons.pack(
            fill="x",
            pady=(18, 0),
        )

        ttk.Button(
            buttons,
            text="Abbrechen",
            command=self.destroy,
        ).pack(
            side="right",
        )

        ttk.Button(
            buttons,
            text="Übernehmen",
            command=self._save,
        ).pack(
            side="right",
            padx=(0, 8),
        )

    def _create_system_accounts_ui(
        self,
        parent: ttk.Frame,
    ) -> None:
        """Erzeugt die Auswahl der technischen Systemkonten."""

        parent.columnconfigure(
            1,
            weight=1,
        )

        rows = (
            (
                "Eröffnungsbilanzkonto",
                self._opening_balance_var,
            ),
            (
                "GuV-Sammelkonto",
                self._income_summary_var,
            ),
            (
                "Jahresüberschuss",
                self._profit_var,
            ),
            (
                "Jahresfehlbetrag",
                self._loss_var,
            ),
            (
                "Gewinn-/Verlustvortrag",
                self._profit_loss_carryforward_var,
            ),
            (
                "Abschreibungsaufwand",
                self._depreciation_expense_var,
            ),
        )

        for row_index, (
            label_text,
            variable,
        ) in enumerate(rows):
            ttk.Label(
                parent,
                text=label_text,
            ).grid(
                row=row_index,
                column=0,
                sticky="w",
                padx=(0, 16),
                pady=8,
            )

            self._create_account_combobox(
                parent=parent,
                variable=variable,
            ).grid(
                row=row_index,
                column=1,
                sticky="ew",
                pady=8,
            )

    def _create_vat_accounts_ui(
        self,
        parent: ttk.Frame,
    ) -> None:
        """Erzeugt die Auswahl der Umsatzsteuerkonten."""

        parent.columnconfigure(
            1,
            weight=1,
        )

        rows = (
            (
                "Vorsteuer 7 %",
                self._input_tax_7_var,
            ),
            (
                "Vorsteuer 19 %",
                self._input_tax_19_var,
            ),
            (
                "Umsatzsteuer 7 %",
                self._output_tax_7_var,
            ),
            (
                "Umsatzsteuer 19 %",
                self._output_tax_19_var,
            ),
        )

        for row_index, (
            label_text,
            variable,
        ) in enumerate(rows):
            ttk.Label(
                parent,
                text=label_text,
            ).grid(
                row=row_index,
                column=0,
                sticky="w",
                padx=(0, 16),
                pady=8,
            )

            self._create_account_combobox(
                parent=parent,
                variable=variable,
            ).grid(
                row=row_index,
                column=1,
                sticky="ew",
                pady=8,
            )

    def _create_account_roles_ui(
        self,
        parent: ttk.Frame,
    ) -> None:
        """Erzeugt die Mehrfachauswahl für funktionale Kontenrollen."""

        parent.columnconfigure(
            0,
            weight=1,
        )
        parent.columnconfigure(
            1,
            weight=1,
        )
        parent.columnconfigure(
            2,
            weight=1,
        )
        parent.rowconfigure(
            1,
            weight=1,
        )

        ttk.Label(
            parent,
            text=(
                "Mehrere Konten können je Rolle ausgewählt werden. "
                "Ein Konto darf nur einer dieser Rollen angehören."
            ),
            wraplength=760,
        ).grid(
            row=0,
            column=0,
            columnspan=3,
            sticky="w",
            pady=(0, 16),
        )

        self._cash_listbox = self._create_role_listbox(
            parent=parent,
            column=0,
            title="Kasse",
            selected_account_numbers=(
                self._account_roles.cash_accounts
            ),
        )

        self._bank_listbox = self._create_role_listbox(
            parent=parent,
            column=1,
            title="Bank",
            selected_account_numbers=(
                self._account_roles.bank_accounts
            ),
        )

        self._general_rate_sales_listbox = (
            self._create_role_listbox(
                parent=parent,
                column=2,
                title="Umsatzerlöse allgemeiner Steuersatz",
                selected_account_numbers=(
                    self._account_roles
                    .general_rate_sales_accounts
                ),
            )
        )

    def _create_account_combobox(
        self,
        *,
        parent: ttk.Frame,
        variable: tk.StringVar,
    ) -> ttk.Combobox:
        """Erzeugt eine schreibgeschützte Kontenauswahl."""

        return ttk.Combobox(
            parent,
            textvariable=variable,
            values=tuple(
                str(account)
                for account in self._accounts
            ),
            state="readonly",
        )

    def _create_role_listbox(
        self,
        *,
        parent: ttk.Frame,
        column: int,
        title: str,
        selected_account_numbers: frozenset[str],
    ) -> tk.Listbox:
        """Erzeugt eine Mehrfachauswahlliste für eine Kontenrolle."""

        frame = ttk.Frame(
            parent
        )
        frame.grid(
            row=1,
            column=column,
            sticky="nsew",
            padx=(
                0 if column == 0 else 6,
                0 if column == 2 else 6,
            ),
        )

        frame.rowconfigure(
            1,
            weight=1,
        )
        frame.columnconfigure(
            0,
            weight=1,
        )

        ttk.Label(
            frame,
            text=title,
            font=("TkDefaultFont", 10, "bold"),
        ).grid(
            row=0,
            column=0,
            sticky="w",
            pady=(0, 6),
        )

        listbox = tk.Listbox(
            frame,
            selectmode="extended",
            exportselection=False,
        )
        listbox.grid(
            row=1,
            column=0,
            sticky="nsew",
        )

        scrollbar = ttk.Scrollbar(
            frame,
            orient="vertical",
            command=listbox.yview,
        )
        scrollbar.grid(
            row=1,
            column=1,
            sticky="ns",
        )

        listbox.configure(
            yscrollcommand=scrollbar.set,
        )

        for index, account in enumerate(
            self._accounts
        ):
            listbox.insert(
                "end",
                str(account),
            )

            if account.number in selected_account_numbers:
                listbox.selection_set(
                    index
                )

        return listbox

    def _save(self) -> None:
        """Prüft die Eingaben und stellt das Dialogergebnis bereit."""

        try:
            control_accounts = AccountingControlAccounts(
                opening_balance_account=(
                    self._account_number_from_display(
                        self._opening_balance_var.get()
                    )
                ),
                income_summary_account=(
                    self._account_number_from_display(
                        self._income_summary_var.get()
                    )
                ),
                profit_account=(
                    self._account_number_from_display(
                        self._profit_var.get()
                    )
                ),
                loss_account=(
                    self._account_number_from_display(
                        self._loss_var.get()
                    )
                ),
                profit_loss_carryforward_account=(
                    self._account_number_from_display(
                        self._profit_loss_carryforward_var.get()
                    )
                ),
                depreciation_expense_account=(
                    self._account_number_from_display(
                        self._depreciation_expense_var.get()
                    )
                ),
            )

            vat_accounts = VatAccounts(
                input_tax_7=(
                    self._account_number_from_display(
                        self._input_tax_7_var.get()
                    )
                ),
                input_tax_19=(
                    self._account_number_from_display(
                        self._input_tax_19_var.get()
                    )
                ),
                output_tax_7=(
                    self._account_number_from_display(
                        self._output_tax_7_var.get()
                    )
                ),
                output_tax_19=(
                    self._account_number_from_display(
                        self._output_tax_19_var.get()
                    )
                ),
            )

            account_roles = AccountingAccountRoles(
                cash_accounts=self._selected_account_numbers(
                    self._cash_listbox
                ),
                bank_accounts=self._selected_account_numbers(
                    self._bank_listbox
                ),
                general_rate_sales_accounts=(
                    self._selected_account_numbers(
                        self._general_rate_sales_listbox
                    )
                ),
            )

        except (
            TypeError,
            ValueError,
        ) as exc:
            messagebox.showerror(
                "Kontenkonfiguration",
                str(exc),
                parent=self,
            )
            return

        self.result = (
            control_accounts,
            vat_accounts,
            account_roles,
        )

        self.destroy()

    def _display_for_account_number(
        self,
        account_number: str,
    ) -> str:
        """Liefert die Darstellungsform eines vorhandenen Kontos."""

        for account in self._accounts:
            if account.number == account_number:
                return str(account)

        return ""

    def _account_number_from_display(
        self,
        display_value: str,
    ) -> str:
        """Liefert die Kontonummer zu einer Combobox-Auswahl."""

        account = self._accounts_by_display.get(
            display_value
        )

        if account is None:
            raise ValueError(
                "Bitte für jedes Feld ein vorhandenes Konto auswählen."
            )

        return account.number

    def _selected_account_numbers(
        self,
        listbox: tk.Listbox,
    ) -> frozenset[str]:
        """Liefert die Kontonummern der markierten Listbox-Einträge."""

        return frozenset(
            self._accounts[index].number
            for index in listbox.curselection()
        )

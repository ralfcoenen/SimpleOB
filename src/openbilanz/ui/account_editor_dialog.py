"""Dialog zum Anlegen eines Kontos."""

import tkinter as tk
from dataclasses import dataclass
from tkinter import messagebox, ttk

from openbilanz.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
from openbilanz.accounting.statement_category import StatementCategory
from openbilanz.domain.account import Account
from openbilanz.domain.account_mapping_rule import (
    AccountMappingRule,
)
from openbilanz.domain.account_type import AccountType
from openbilanz.domain.template_account import TemplateAccount


@dataclass(frozen=True, slots=True)
class AccountEditorResult:
    """Ergebnis des Konteneditors."""

    account: Account
    mapping_rule: AccountMappingRule


class AccountEditorDialog(tk.Toplevel):
    """Erfasst ein neues Konto."""

    _ACCOUNT_TYPE_LABELS = {
        "Aktivkonto": AccountType.ASSET,
        "Passivkonto": AccountType.LIABILITY,
        "Eigenkapital": AccountType.EQUITY,
        "Ertragskonto": AccountType.REVENUE,
        "Aufwandskonto": AccountType.EXPENSE,
    }

    def __init__(
        self,
        parent: tk.Misc,
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

        self.title(
            "OpenBilanz – Konto bearbeiten"
            if self._is_edit_mode
            else "OpenBilanz – Neues Konto"
        )
        self.geometry("720x430")
        self.resizable(False, False)

        self.transient(parent)
        self.grab_set()

        self._create_ui()
        self._update_mapping_choices()
        if self._is_edit_mode:
            self._load_account()

        if self._is_edit_mode:
            self.after_idle(
                self._name_entry.focus_set
            )
        else:
            self.after_idle(
                self._account_number_entry.focus_set
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
            text=(
                "Konto bearbeiten"
                if self._is_edit_mode
                else "Neues Konto"
            ),
            font=("TkDefaultFont", 18, "bold"),
        ).pack(
            anchor="w",
            pady=(0, 18),
        )

        form = ttk.Frame(
            container
        )
        form.pack(
            fill="x"
        )

        form.columnconfigure(
            1,
            weight=1,
        )

        self._account_number_var = tk.StringVar()
        self._name_var = tk.StringVar()

        self._account_type_var = tk.StringVar(
            value="Aktivkonto"
        )

        self._debit_position_var = tk.StringVar()
        self._credit_position_var = tk.StringVar()

        self._is_active_var = tk.BooleanVar(
            value=True
        )

        ttk.Label(
            form,
            text="Kontonummer",
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=(0, 12),
            pady=7,
        )

        self._account_number_entry = ttk.Entry(
            form,
            textvariable=self._account_number_var,
        )
        self._account_number_entry.grid(
            row=0,
            column=1,
            sticky="ew",
            pady=7,
        )
        if self._is_edit_mode:
            self._account_number_entry.configure(
                state="disabled"
            )
        

        ttk.Label(
            form,
            text="Bezeichnung",
        ).grid(
            row=1,
            column=0,
            sticky="w",
            padx=(0, 12),
            pady=7,
        )

        self._name_entry = ttk.Entry(
            form,
            textvariable=self._name_var,
        )
        self._name_entry.grid(
            row=1,
            column=1,
            sticky="ew",
            pady=7,
        )

        ttk.Label(
            form,
            text="Kontotyp",
        ).grid(
            row=2,
            column=0,
            sticky="w",
            padx=(0, 12),
            pady=7,
        )

        self._account_type_box = ttk.Combobox(
            form,
            textvariable=self._account_type_var,
            values=tuple(
                self._ACCOUNT_TYPE_LABELS
            ),
            state="readonly",
        )
        self._account_type_box.grid(
            row=2,
            column=1,
            sticky="ew",
            pady=7,
        )

        self._account_type_box.bind(
            "<<ComboboxSelected>>",
            self._on_account_type_changed,
        )

        ttk.Label(
            form,
            text="HGB-Zuordnung Soll",
        ).grid(
            row=3,
            column=0,
            sticky="w",
            padx=(0, 12),
            pady=7,
        )

        self._debit_position_box = ttk.Combobox(
            form,
            textvariable=self._debit_position_var,
            state="readonly",
        )
        self._debit_position_box.grid(
            row=3,
            column=1,
            sticky="ew",
            pady=7,
        )

        ttk.Label(
            form,
            text="HGB-Zuordnung Haben",
        ).grid(
            row=4,
            column=0,
            sticky="w",
            padx=(0, 12),
            pady=7,
        )

        self._credit_position_box = ttk.Combobox(
            form,
            textvariable=self._credit_position_var,
            state="readonly",
        )
        self._credit_position_box.grid(
            row=4,
            column=1,
            sticky="ew",
            pady=7,
        )

        ttk.Checkbutton(
            form,
            text="Konto ist aktiv",
            variable=self._is_active_var,
        ).grid(
            row=5,
            column=1,
            sticky="w",
            pady=(12, 7),
        )

        ttk.Label(
            container,
            text=(
                "Die HGB-Struktur ist fest vorgegeben. "
                "Hier wird nur die Zuordnung des Kontos "
                "zu einer vorhandenen HGB-Position festgelegt."
            ),
            wraplength=660,
        ).pack(
            anchor="w",
            pady=(16, 0),
        )

        button_frame = ttk.Frame(
            container
        )
        button_frame.pack(
            fill="x",
            pady=(24, 0),
        )

        ttk.Button(
            button_frame,
            text="Abbrechen",
            command=self.destroy,
        ).pack(
            side="right",
        )

        ttk.Button(
            button_frame,
            text="Speichern",
            command=self._save,
        ).pack(
            side="right",
            padx=(0, 10),
        )

    def _on_account_type_changed(
        self,
        _event: object | None = None,
    ) -> None:
        """Aktualisiert die möglichen HGB-Zuordnungen."""

        self._update_mapping_choices()

    def _update_mapping_choices(self) -> None:
        """Stellt passende HGB-Positionen zum Kontotyp bereit."""

        account_type = self._selected_account_type()

        self._debit_position_var.set("")
        self._credit_position_var.set("")

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

            self._debit_position_box.configure(
                state="readonly"
            )
            self._credit_position_box.configure(
                state="readonly"
            )

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

            self._debit_position_box.configure(
                state="readonly"
            )
            self._credit_position_box.configure(
                state="readonly"
            )

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

            self._debit_position_box.configure(
                state="disabled"
            )
            self._credit_position_box.configure(
                state="readonly"
            )

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

            self._debit_position_box.configure(
                state="readonly"
            )
            self._credit_position_box.configure(
                state="disabled"
            )

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

        self._debit_position_box.configure(
            values=tuple(
                self._debit_positions
            )
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

        self._credit_position_box.configure(
            values=tuple(
                self._credit_positions
            )
        )

    def _save(self) -> None:
        """Validiert die Eingaben und erzeugt das Konto."""

        try:
            account_number = (
                self._account_number_var
                .get()
                .strip()
            )

            name = (
                self._name_var
                .get()
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
                is_active=self._is_active_var.get(),
            )

            debit_position = (
                self._debit_positions.get(
                    self._debit_position_var.get()
                )
            )

            credit_position = (
                self._credit_positions.get(
                    self._credit_position_var.get()
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
            messagebox.showerror(
                (
                    "Konto kann nicht geändert werden"
                    if self._is_edit_mode
                    else "Konto kann nicht angelegt werden"
                ),
                str(exc),
                parent=self,
            )
            return

        self.result = AccountEditorResult(
            account=account,
            mapping_rule=mapping_rule,
        )

        self.destroy()

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
                self._account_type_var.get()
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

        self._account_number_var.set(
            self._account.number
        )
        self._name_var.set(
            self._account.name
        )
        self._is_active_var.set(
            self._account.is_active
        )

        account_type_label = next(
            label
            for label, account_type
            in self._ACCOUNT_TYPE_LABELS.items()
            if account_type is self._account.account_type
        )

        self._account_type_var.set(
            account_type_label
        )

        self._update_mapping_choices()

        if self._mapping_rule is None:
            return

        if self._mapping_rule.debit_position is not None:
            self._debit_position_var.set(
                self._position_display_name(
                    self._mapping_rule.debit_position
                )
            )

        if self._mapping_rule.credit_position is not None:
            self._credit_position_var.set(
                self._position_display_name(
                    self._mapping_rule.credit_position
                )
            )
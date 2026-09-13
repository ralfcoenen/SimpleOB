"""Hauptfenster der SimpleOB-Anwendung."""

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk
from urllib.error import URLError
from zipfile import BadZipFile
from decimal import Decimal

from openbilanz.accounting.balance_sheet import BalanceSheet
from openbilanz.accounting.financial_statement_context import (
    FinancialStatementContext,
)
from openbilanz.accounting.income_statement import IncomeStatement
from openbilanz.accounting.ledger import Ledger
from openbilanz.domain.account_type import AccountType
from openbilanz.domain.booking import Booking
from openbilanz.domain.entry_side import EntrySide
from openbilanz.domain.fixed_asset_status import FixedAssetStatus
from openbilanz.domain.journal import Journal
from openbilanz.domain.money import ZERO
from openbilanz.domain.vat_accounts import VatAccounts
from openbilanz.domain.bvv_annual_data import (
    BvvAnnualData,
)
from openbilanz.eric.elster_bilanz_transmission_service import (
    ElsterBilanzTransmissionService,
)
from openbilanz.services.closing_accounts import ClosingAccounts
from openbilanz.services.closing_result import ClosingResult
from openbilanz.services.closing_service import ClosingService
from openbilanz.services.e_bilanz_preparation_service import (
    EBilanzPreparationResult,
)
from openbilanz.services.fiscal_year_workspace import (
    FiscalYearWorkspace,
)
from openbilanz.services.opening_balance_service import (
    OpeningBalanceService,
)
from openbilanz.services.pdf_reporting_service import PdfReportingService
from openbilanz.taxonomy.e_bilanz_builder import (
    EBilanzDocument,
)
from openbilanz.ui.account_configuration_dialog import (
    AccountConfigurationDialog,
)
from openbilanz.ui.account_editor_dialog import (
    AccountEditorDialog,
)
from openbilanz.ui.balance_sheet_frame import BalanceSheetFrame
from openbilanz.ui.booking_frame import BookingFrame
from openbilanz.ui.closing_frame import ClosingFrame
from openbilanz.ui.company_master_data_dialog import (
    CompanyMasterDataDialog,
)
from openbilanz.ui.date_input import (
    normalize_german_date,
    parse_german_date,
)
from openbilanz.ui.fixed_asset_acquisition_link_dialog import (
    AcquisitionBookingCandidate,
    FixedAssetAcquisitionLinkDialog,
)
from openbilanz.ui.fixed_asset_disposal_link_dialog import (
    DisposalBookingCandidate,
    FixedAssetDisposalLinkDialog,
)
from openbilanz.ui.income_statement_frame import (
    IncomeStatementFrame,
)
from openbilanz.ui.new_fixed_asset_dialog import (
    NewFixedAssetDialog,
)
from openbilanz.ui.opening_balance_dialog import (
    OpeningBalanceDialog,
)
from openbilanz.ui.shareholder_dialog import (
    ShareholdersDialog,
)
from openbilanz.ui.tax_depreciation_adjustment_dialog import (
    TaxDepreciationAdjustmentDialog,
)
from openbilanz.ui.vat_booking_frame import VatBookingFrame


class MainWindow(tk.Tk):
    """Hauptfenster von SimpleOB."""

    def __init__(
        self,
        *,
        workspace: FiscalYearWorkspace,
        financial_statement_context: FinancialStatementContext,
        closing_accounts: ClosingAccounts,
        opening_balance_account_number: str,
        depreciation_expense_account_number: str,
        vat_accounts: VatAccounts,
        pdf_reporting_service: PdfReportingService,
        elster_bilanz_transmission_service: (
            ElsterBilanzTransmissionService | None
        ) = None,
    ) -> None:

        super().__init__()

        self._workspace = workspace
        self._context = workspace.context
        self._return_to_start_requested = False
        self._financial_statement_context = financial_statement_context
        self._closing_accounts = closing_accounts
        self._opening_balance_account_number = (
            opening_balance_account_number
        )
        self._depreciation_expense_account_number = (
            depreciation_expense_account_number
        )
        self._vat_accounts = vat_accounts
        self._pdf_reporting_service = pdf_reporting_service
        self._elster_bilanz_transmission_service = (
            elster_bilanz_transmission_service
        )
        self._current_trial_balance_report = None
        self._current_account_activity_reports = ()
        self._current_account_activity_start_date = None
        self._current_account_activity_end_date = None
        self._current_journal_report = None

        self.title("SimpleOB")
        self.geometry("1300x800")
        self.minsize(1100, 700)

        self._opening_balance_service = OpeningBalanceService(
            opening_balance_account_number=(
                self._opening_balance_account_number
            ),
        )

        self._closing_service = ClosingService()

        self._assets = financial_statement_context.assets
        self._liabilities = financial_statement_context.liabilities
        self._income_statement = financial_statement_context.income_statement

        self._chart_of_accounts = financial_statement_context.chart_of_accounts
        self._accounts = financial_statement_context.accounts
        self._account_mapper = financial_statement_context.account_mapper
        self._financial_statement_builder = (
            financial_statement_context.statement_builder
        )
        self._account_types = financial_statement_context.account_types
        self._current_income_statement: IncomeStatement | None = None
        self._current_closing_result: ClosingResult | None = None
        self._current_balance_sheet: BalanceSheet | None = None
        self._current_closing_balances = ()
        self._current_e_bilanz_preparation: EBilanzPreparationResult | None = None
        self._current_e_bilanz_document: EBilanzDocument | None = None
        self._current_e_bilanz_arelle_valid = False

        self._create_ui()

        self._refresh_all()

    @property
    def _journal(self) -> Journal:
        """Liefert das Journal des aktuellen Workspace."""

        return self._workspace.journal

    @property
    def _ledger(self) -> Ledger:
        """Liefert das Hauptbuch des aktuellen Workspace."""

        return self._workspace.ledger

    @property
    def return_to_start_requested(self) -> bool:
        """Zeigt an, ob zur Buchhaltungsauswahl zurückgekehrt werden soll."""

        return self._return_to_start_requested

    def _create_ui(self) -> None:
        """Erzeugt die Benutzeroberfläche."""

        container = ttk.Frame(
            self,
            padding=16,
        )
        container.pack(
            fill="both",
            expand=True,
        )

        ttk.Label(
            container,
            text="SimpleOB",
            font=("TkDefaultFont", 24, "bold"),
        ).pack(
            anchor="w",
        )

        ttk.Label(
            container,
            text="Buchhaltung und Jahresabschluss",
        ).pack(
            anchor="w",
            pady=(4, 16),
        )

        context_frame = ttk.Frame(
            container,
        )
        context_frame.pack(
            fill="x",
            pady=(0, 16),
        )

        ttk.Label(
            context_frame,
            text=self._context.company.name,
            font=("TkDefaultFont", 13, "bold"),
        ).pack(
            anchor="w",
        )

        ttk.Label(
            context_frame,
            text=(f"Geschäftsjahr: {self._context.fiscal_year.display_name}"),
        ).pack(
            anchor="w",
            pady=(2, 0),
        )

        context_buttons = ttk.Frame(context_frame)
        context_buttons.pack(
            anchor="w",
            pady=(8, 0),
        )

        ttk.Button(
            context_buttons,
            text="Unternehmensstammdaten",
            command=self._open_company_master_data,
        ).pack(
            side="left",
        )

        ttk.Button(
            context_buttons,
            text="Gesellschafter",
            command=self._open_shareholders,
        ).pack(
            side="left",
            padx=(8, 0),
        )

        ttk.Button(
            context_buttons,
            text="Kontenkonfiguration",
            command=self._open_account_configuration,
        ).pack(
            side="left",
            padx=(8, 0),
        )

        ttk.Button(
            context_buttons,
            text="Buchhaltung wechseln",
            command=self._return_to_start,
        ).pack(
            side="left",
            padx=(8, 0),
        )

        self._opening_balance_button = ttk.Button(
            container,
            text="Eröffnungsbilanz erfassen",
            command=self._open_opening_balance,
        )
        self._opening_balance_button.pack(
            anchor="w",
            pady=(0, 16),
        )

        self._notebook = ttk.Notebook(container)

        self._notebook.pack(
            fill="both",
            expand=True,
        )

        self._accounts_tab = ttk.Frame(
            self._notebook,
            padding=16,
        )

        self._journal_tab = ttk.Frame(
            self._notebook,
            padding=16,
        )

        self._booking_tab = ttk.Frame(
            self._notebook,
            padding=16,
        )

        self._balance_sheet_tab = ttk.Frame(
            self._notebook,
            padding=16,
        )
        self._fixed_assets_tab = ttk.Frame(
            self._notebook,
            padding=16,
        )
        self._income_statement_tab = ttk.Frame(
            self._notebook,
            padding=16,
        )
        self._reports_tab = ttk.Frame(
            self._notebook,
            padding=16,
        )

        self._closing_tab = ttk.Frame(
            self._notebook,
            padding=16,
        )

        self._e_bilanz_tab = ttk.Frame(
            self._notebook,
            padding=16,
        )

        self._notebook.add(
            self._accounts_tab,
            text="Konten",
        )

        self._notebook.add(
            self._journal_tab,
            text="Journal",
        )

        self._notebook.add(
            self._booking_tab,
            text="Buchen",
        )

        self._notebook.add(
            self._fixed_assets_tab,
            text="Anlagen",
        )

        self._notebook.add(
            self._balance_sheet_tab,
            text="Bilanz",
        )

        self._notebook.add(
            self._income_statement_tab,
            text="GuV",
        )

        self._notebook.add(
            self._reports_tab,
            text="Auswertungen",
        )

        self._notebook.add(
            self._closing_tab,
            text="Jahresabschluss",
        )

        self._notebook.add(
            self._e_bilanz_tab,
            text="E-Bilanz",
        )

        self._create_accounts_tab()
        self._create_journal_tab()
        self._create_booking_tab()
        self._create_fixed_assets_tab()
        self._create_balance_sheet_tab()
        self._create_income_statement_tab()
        self._create_closing_tab()
        self._create_e_bilanz_tab()
        self._create_reports_tab()

    def _create_accounts_tab(self) -> None:
        """Erzeugt den Arbeitsbereich Konten."""

        ttk.Label(
            self._accounts_tab,
            text="Kontenübersicht",
            font=("TkDefaultFont", 16, "bold"),
        ).pack(
            anchor="w",
        )

        button_frame = ttk.Frame(
            self._accounts_tab
        )
        button_frame.pack(
            fill="x",
            pady=(8, 12),
        )

        self._new_account_button = ttk.Button(
            button_frame,
            text="Neues Konto",
            command=self._open_new_account,
        )
        self._new_account_button.pack(
            side="left",
        )

        self._edit_account_button = ttk.Button(
            button_frame,
            text="Konto bearbeiten",
            command=self._open_edit_account,
        )
        self._edit_account_button.pack(
            side="left",
            padx=(8, 0),
        )

        self._journal_status = ttk.Label(
            self._accounts_tab,
            text="Journal: noch keine Buchungen",
        )
        self._journal_status.pack(
            anchor="w",
            pady=(0, 12),
        )

        columns = (
            "account_number",
            "name",
            "debit",
            "credit",
            "balance",
        )

        self._account_table = ttk.Treeview(
            self._accounts_tab,
            columns=columns,
            show="headings",
            height=12,
        )

        self._account_table.bind(
            "<Double-1>",
            lambda _event: self._open_edit_account(),
        )

        self._account_table.heading(
            "account_number",
            text="Konto",
        )

        self._account_table.heading(
            "name",
            text="Bezeichnung",
        )

        self._account_table.heading(
            "debit",
            text="Soll",
        )

        self._account_table.heading(
            "credit",
            text="Haben",
        )

        self._account_table.heading(
            "balance",
            text="Saldo",
        )

        self._account_table.column(
            "account_number",
            width=90,
            anchor="w",
        )

        self._account_table.column(
            "name",
            width=330,
            anchor="w",
        )

        self._account_table.column(
            "debit",
            width=120,
            anchor="e",
        )

        self._account_table.column(
            "credit",
            width=120,
            anchor="e",
        )

        self._account_table.column(
            "balance",
            width=140,
            anchor="e",
        )

        self._account_table.pack(
            fill="both",
            expand=True,
        )

    def _open_new_account(self) -> None:
        """Öffnet den Dialog zum Anlegen eines Kontos."""

        if self._workspace.is_closed:
            return

        dialog = AccountEditorDialog(
            self,
            assets=self._assets,
            liabilities=self._liabilities,
            income_statement=self._income_statement,
        )

        self.wait_window(dialog)

        if dialog.result is None:
            return

        try:
            self._workspace.add_account(
                account=dialog.result.account,
                mapping_rule=dialog.result.mapping_rule,
            )
        except ValueError as exc:
            messagebox.showerror(
                "Konto kann nicht angelegt werden",
                str(exc),
                parent=self,
            )
            return

        messagebox.showinfo(
            "Konto angelegt",
            (
                "Das Konto wurde gespeichert.\n\n"
                "Die Buchhaltung wird neu geöffnet, "
                "damit der geänderte Kontenrahmen "
                "vollständig wirksam wird."
            ),
            parent=self,
        )

        self._return_to_start_requested = True
        self.destroy()

    def _open_edit_account(self) -> None:
        """Öffnet den Dialog zum Bearbeiten des ausgewählten Kontos."""

        if self._workspace.is_closed:
            return

        selection = self._account_table.selection()

        if not selection:
            messagebox.showinfo(
                "Konto bearbeiten",
                "Bitte wählen Sie zuerst ein Konto aus.",
                parent=self,
            )
            return

        values = self._account_table.item(
            selection[0],
            "values",
        )

        if not values:
            return

        account_number = str(
            values[0]
        )

        technical_account_numbers = {
            self._opening_balance_account_number,
            self._closing_accounts.income_summary_account,
            self._closing_accounts.profit_account,
            self._closing_accounts.loss_account,
            *self._vat_accounts.account_numbers,
        }

        if account_number in technical_account_numbers:
            messagebox.showinfo(
                "Konto bearbeiten",
                (
                    "Dieses Konto ist als technisches "
                    "Steuerungskonto konfiguriert und kann "
                    "hier nicht bearbeitet werden."
                ),
                parent=self,
            )
            return

        account = next(
            (
                item
                for item in self._accounts
                if item.number == account_number
            ),
            None,
        )

        if account is None:
            messagebox.showerror(
                "Konto bearbeiten",
                "Das ausgewählte Konto wurde nicht gefunden.",
                parent=self,
            )
            return

        mapping_rule = next(
            (
                rule
                for rule
                in self._chart_of_accounts.account_mapping_rules
                if rule.account_number == account_number
            ),
            None,
        )

        dialog = AccountEditorDialog(
            self,
            assets=self._assets,
            liabilities=self._liabilities,
            income_statement=self._income_statement,
            account=account,
            mapping_rule=mapping_rule,
        )

        self.wait_window(dialog)

        if dialog.result is None:
            return

        try:
            self._workspace.update_account(
                account=dialog.result.account,
                mapping_rule=dialog.result.mapping_rule,
            )
        except ValueError as exc:
            messagebox.showerror(
                "Konto kann nicht geändert werden",
                str(exc),
                parent=self,
            )
            return

        messagebox.showinfo(
            "Konto geändert",
            (
                "Das Konto wurde gespeichert.\n\n"
                "Die Buchhaltung wird neu geöffnet, "
                "damit der geänderte Kontenrahmen "
                "vollständig wirksam wird."
            ),
            parent=self,
        )

        self._return_to_start_requested = True
        self.destroy()

    def _create_journal_tab(self) -> None:
        """Erzeugt den Arbeitsbereich Journal."""

        ttk.Label(
            self._journal_tab,
            text="Journal",
            font=("TkDefaultFont", 16, "bold"),
        ).pack(
            anchor="w",
        )

        columns = (
            "date",
            "voucher",
            "description",
            "account",
            "side",
            "amount",
        )

        self._journal_table = ttk.Treeview(
            self._journal_tab,
            columns=columns,
            show="headings",
            height=14,
        )

        self._journal_table.heading(
            "date",
            text="Datum",
        )

        self._journal_table.heading(
            "voucher",
            text="Beleg",
        )

        self._journal_table.heading(
            "description",
            text="Buchungstext",
        )

        self._journal_table.heading(
            "account",
            text="Konto",
        )

        self._journal_table.heading(
            "side",
            text="S/H",
        )

        self._journal_table.heading(
            "amount",
            text="Betrag",
        )

        self._journal_table.column(
            "date",
            width=100,
            anchor="w",
        )

        self._journal_table.column(
            "voucher",
            width=100,
            anchor="w",
        )

        self._journal_table.column(
            "description",
            width=230,
            anchor="w",
        )

        self._journal_table.column(
            "account",
            width=330,
            anchor="w",
        )

        self._journal_table.column(
            "side",
            width=60,
            anchor="center",
        )

        self._journal_table.column(
            "amount",
            width=130,
            anchor="e",
        )

        self._journal_table.pack(
            fill="both",
            expand=True,
            pady=(12, 0),
        )

    def _create_booking_tab(self) -> None:
        """Erzeugt den Arbeitsbereich Buchen."""

        ttk.Label(
            self._booking_tab,
            text="Neue Buchung",
            font=("TkDefaultFont", 16, "bold"),
        ).pack(
            anchor="w",
            pady=(0, 16),
        )

        mode_frame = ttk.Frame(
            self._booking_tab
        )
        mode_frame.pack(
            fill="x",
            pady=(0, 16),
        )

        ttk.Label(
            mode_frame,
            text="Buchungsart",
        ).pack(
            side="left",
            padx=(0, 12),
        )

        self._booking_mode_var = tk.StringVar(
            value="Einfache Buchung"
        )

        self._booking_mode_box = ttk.Combobox(
            mode_frame,
            textvariable=self._booking_mode_var,
            values=(
                "Einfache Buchung",
                "Rechnung mit Umsatzsteuer",
            ),
            state="readonly",
            width=28,
        )
        self._booking_mode_box.pack(
            side="left",
        )

        technical_account_numbers = {
            self._opening_balance_account_number,
            self._closing_accounts.income_summary_account,
            self._closing_accounts.profit_account,
            self._closing_accounts.loss_account,
            *self._vat_accounts.account_numbers,
        }

        bookable_accounts = tuple(
            account
            for account in self._accounts
            if (
                account.is_active
                and account.number not in technical_account_numbers
            )
        )

        self._booking_frame_container = ttk.Frame(
            self._booking_tab
        )
        self._booking_frame_container.pack(
            fill="x",
            expand=False,
        )

        self._booking_frame = BookingFrame(
            self._booking_frame_container,
            accounts=bookable_accounts,
            on_booking_created=self._post_booking,
        )

        self._vat_booking_frame = VatBookingFrame(
            self._booking_frame_container,
            accounts=bookable_accounts,
            vat_accounts=self._vat_accounts,
            on_booking_created=self._post_booking,
        )

        self._booking_frame.pack(
            fill="x",
            expand=False,
        )

        self._booking_mode_var.trace_add(
            "write",
            self._update_booking_mode,
        )

    def _update_booking_mode(
        self,
        *_args: object,
    ) -> None:
        """Schaltet zwischen einfacher und Umsatzsteuerbuchung um."""

        self._booking_frame.pack_forget()
        self._vat_booking_frame.pack_forget()

        if (
            self._booking_mode_var.get()
            == "Rechnung mit Umsatzsteuer"
        ):
            self._vat_booking_frame.pack(
                fill="x",
                expand=False,
            )
        else:
            self._booking_frame.pack(
                fill="x",
                expand=False,
            )

    def _create_fixed_assets_tab(self) -> None:
        """Erzeugt den Arbeitsbereich Anlagen."""

        header = ttk.Frame(self._fixed_assets_tab)
        header.pack(
            fill="x",
            pady=(0, 12),
        )

        ttk.Label(
            header,
            text="Anlagegüter",
            font=("TkDefaultFont", 16, "bold"),
        ).pack(
            side="left",
        )
        self._link_fixed_asset_disposal_button = ttk.Button(
            header,
            text="Abgangsbuchung zuordnen",
            command=self._open_link_fixed_asset_disposal,
        )
        self._link_fixed_asset_disposal_button.pack(
            side="right",
            padx=(0, 8),
        )
        self._link_fixed_asset_acquisition_button = ttk.Button(
            header,
            text="Anschaffungsbuchung zuordnen",
            command=self._open_link_fixed_asset_acquisition,
        )
        self._link_fixed_asset_acquisition_button.pack(
            side="right",
            padx=(0, 8),
        )
        self._tax_depreciation_adjustments_button = ttk.Button(
            header,
            text="Steuerliche AfA-Abweichungen",
            command=self._manage_tax_depreciation_adjustments,
        )
        self._tax_depreciation_adjustments_button.pack(
            side="right",
            padx=(0, 8),
        )
        self._process_depreciations_button = ttk.Button(
            header,
            text="Abschreibungen prüfen/buchen",
            command=self._process_depreciations,
        )
        self._process_depreciations_button.pack(
            side="right",
            padx=(0, 8),
        )

        self._delete_fixed_asset_button = ttk.Button(
            header,
            text="Anlagegut löschen",
            command=self._delete_fixed_asset,
        )
        self._delete_fixed_asset_button.pack(
            side="right",
            padx=(0, 8),
        )

        self._edit_fixed_asset_button = ttk.Button(
            header,
            text="Anlagegut bearbeiten",
            command=self._open_edit_fixed_asset,
        )
        self._edit_fixed_asset_button.pack(
            side="right",
            padx=(0, 8),
        )

        self._add_fixed_asset_button = ttk.Button(
            header,
            text="Anlagegut hinzufügen",
            command=self._open_new_fixed_asset,
        )
        self._add_fixed_asset_button.pack(
            side="right",
        )

        columns = (
            "asset_code",
            "description",
            "acquisition_date",
            "acquisition_cost",
            "useful_life",
            "asset_account",
            "depreciation_account",
            "acquisition_booking",
            "status",
        )

        self._fixed_asset_table = ttk.Treeview(
            self._fixed_assets_tab,
            columns=columns,
            show="headings",
            height=14,
        )

        headings = {
            "asset_code": "Anlagen-ID",
            "description": "Bezeichnung",
            "acquisition_date": "Anschaffung",
            "acquisition_cost": "AK/HK",
            "useful_life": "ND Monate",
            "asset_account": "Anlagekonto",
            "depreciation_account": "AfA-Konto",
            "acquisition_booking": "Anschaffungsbuchung",
            "status": "Status",
        }

        for column, text in headings.items():
            self._fixed_asset_table.heading(
                column,
                text=text,
            )

        self._fixed_asset_table.column(
            "asset_code",
            width=90,
            anchor="w",
        )
        self._fixed_asset_table.column(
            "description",
            width=220,
            anchor="w",
        )
        self._fixed_asset_table.column(
            "acquisition_date",
            width=100,
            anchor="w",
        )
        self._fixed_asset_table.column(
            "acquisition_cost",
            width=110,
            anchor="e",
        )
        self._fixed_asset_table.column(
            "useful_life",
            width=85,
            anchor="e",
        )
        self._fixed_asset_table.column(
            "asset_account",
            width=90,
            anchor="w",
        )
        self._fixed_asset_table.column(
            "depreciation_account",
            width=90,
            anchor="w",
        )
        self._fixed_asset_table.column(
            "acquisition_booking",
            width=150,
            anchor="w",
        )
        self._fixed_asset_table.column(
            "status",
            width=90,
            anchor="w",
        )

        self._fixed_asset_table.pack(
            fill="both",
            expand=True,
        )

    def _create_balance_sheet_tab(
        self,
    ) -> None:
        """Erzeugt den Arbeitsbereich Bilanz."""

        ttk.Label(
            self._balance_sheet_tab,
            text="Bilanz nach § 266 HGB",
            font=("TkDefaultFont", 16, "bold"),
        ).pack(
            anchor="w",
            pady=(0, 12),
        )

        ttk.Button(
            self._balance_sheet_tab,
            text="PDF exportieren",
            command=self._export_balance_sheet_pdf,
        ).pack(
            anchor="w",
            pady=(0, 12),
        )

        self._balance_sheet_frame = BalanceSheetFrame(self._balance_sheet_tab)

        self._balance_sheet_frame.pack(
            fill="both",
            expand=True,
        )

    def _create_income_statement_tab(
        self,
    ) -> None:
        """Erzeugt den Arbeitsbereich GuV."""

        ttk.Label(
            self._income_statement_tab,
            text="Gewinn- und Verlustrechnung nach § 275 HGB",
            font=("TkDefaultFont", 16, "bold"),
        ).pack(
            anchor="w",
            pady=(0, 12),
        )

        ttk.Button(
            self._income_statement_tab,
            text="PDF exportieren",
            command=self._export_income_statement_pdf,
        ).pack(
            anchor="w",
            pady=(0, 12),
        )

        self._income_statement_frame = IncomeStatementFrame(self._income_statement_tab)

        self._income_statement_frame.pack(
            fill="both",
            expand=True,
        )

    def _create_closing_tab(
        self,
    ) -> None:
        """Erzeugt den Arbeitsbereich Jahresabschluss."""

        self._closing_frame = ClosingFrame(
            self._closing_tab,
            on_validate=self._validate_closing,
            on_close=self._close_fiscal_year,
        )

        self._closing_frame.pack(
            fill="both",
            expand=True,
        )

    def _create_e_bilanz_tab(self) -> None:
        """Erzeugt den Arbeitsbereich E-Bilanz."""

        ttk.Label(
            self._e_bilanz_tab,
            text="E-Bilanz",
            font=("TkDefaultFont", 16, "bold"),
        ).pack(
            anchor="w",
        )

        ttk.Label(
            self._e_bilanz_tab,
            text=(
                "Vorbereitung und Erzeugung der E-Bilanz "
                "für das aktuelle Geschäftsjahr."
            ),
        ).pack(
            anchor="w",
            pady=(4, 16),
        )

        self._taxonomy_status = ttk.Label(
            self._e_bilanz_tab,
            text="",
        )
        self._taxonomy_status.pack(
            anchor="w",
            pady=(0, 16),
        )

        self._install_taxonomy_button = ttk.Button(
            self._e_bilanz_tab,
            text="Taxonomie installieren",
            command=self._install_required_taxonomy,
            state="disabled",
        )
        self._install_taxonomy_button.pack(
            anchor="w",
            pady=(0, 16),
        )

        self._e_bilanz_status = ttk.Label(
            self._e_bilanz_tab,
            text="",
        )
        self._e_bilanz_status.pack(
            anchor="w",
            pady=(0, 16),
        )
        bvv_frame = ttk.LabelFrame(
            self._e_bilanz_tab,
            text="BVV-Jahresdaten",
            padding=12,
        )
        bvv_frame.pack(
            fill="x",
            pady=(0, 16),
        )

        self._bvv_effective_previous_hgb_equity_var = (
            tk.StringVar(value="–")
        )
        self._bvv_previous_hgb_equity_source_var = (
            tk.StringVar(value="")
        )
        self._bvv_previous_hgb_equity_override_var = (
            tk.StringVar()
        )
        self._bvv_contribution_var = (
            tk.StringVar(value="0,00")
        )
        self._bvv_withdrawal_distribution_var = (
            tk.StringVar(value="0,00")
        )

        ttk.Label(
            bvv_frame,
            text="HGB-Vorjahreseigenkapital",
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=(0, 12),
            pady=(0, 4),
        )

        ttk.Label(
            bvv_frame,
            textvariable=(
                self._bvv_effective_previous_hgb_equity_var
            ),
        ).grid(
            row=0,
            column=1,
            sticky="w",
            pady=(0, 4),
        )

        ttk.Label(
            bvv_frame,
            text="Herkunft",
        ).grid(
            row=1,
            column=0,
            sticky="w",
            padx=(0, 12),
            pady=(0, 12),
        )

        ttk.Label(
            bvv_frame,
            textvariable=(
                self._bvv_previous_hgb_equity_source_var
            ),
        ).grid(
            row=1,
            column=1,
            sticky="w",
            pady=(0, 12),
        )

        ttk.Label(
            bvv_frame,
            text="Manueller Korrekturwert",
        ).grid(
            row=2,
            column=0,
            sticky="w",
            padx=(0, 12),
            pady=(0, 4),
        )

        ttk.Entry(
            bvv_frame,
            textvariable=(
                self._bvv_previous_hgb_equity_override_var
            ),
            width=18,
        ).grid(
            row=2,
            column=1,
            sticky="w",
            pady=(0, 4),
        )

        ttk.Label(
            bvv_frame,
            text=(
                "Leer lassen, um den automatisch "
                "ermittelten Wert zu verwenden."
            ),
        ).grid(
            row=3,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(0, 12),
        )

        ttk.Label(
            bvv_frame,
            text="Einlagen",
        ).grid(
            row=4,
            column=0,
            sticky="w",
            padx=(0, 12),
            pady=(0, 8),
        )

        ttk.Entry(
            bvv_frame,
            textvariable=self._bvv_contribution_var,
            width=18,
        ).grid(
            row=4,
            column=1,
            sticky="w",
            pady=(0, 8),
        )

        ttk.Label(
            bvv_frame,
            text="Entnahmen / Ausschüttungen",
        ).grid(
            row=5,
            column=0,
            sticky="w",
            padx=(0, 12),
            pady=(0, 8),
        )

        ttk.Entry(
            bvv_frame,
            textvariable=(
                self._bvv_withdrawal_distribution_var
            ),
            width=18,
        ).grid(
            row=5,
            column=1,
            sticky="w",
            pady=(0, 8),
        )

        ttk.Button(
            bvv_frame,
            text="BVV-Daten speichern",
            command=self._save_bvv_annual_data,
        ).grid(
            row=6,
            column=0,
            columnspan=2,
            sticky="w",
        )
        self._prepare_e_bilanz_button = ttk.Button(
            self._e_bilanz_tab,
            text="E-Bilanz vorbereiten",
            command=self._prepare_e_bilanz,
            state="disabled",
        )
        self._prepare_e_bilanz_button.pack(
            anchor="w",
        )
        self._build_e_bilanz_button = ttk.Button(
            self._e_bilanz_tab,
            text="E-Bilanz erzeugen",
            command=self._build_e_bilanz,
            state="disabled",
        )
        self._build_e_bilanz_button.pack(
            anchor="w",
            pady=(8, 0),
        )
        self._validate_e_bilanz_button = ttk.Button(
            self._e_bilanz_tab,
            text="E-Bilanz validieren",
            command=self._validate_e_bilanz,
            state="disabled",
        )
        self._validate_e_bilanz_button.pack(
            anchor="w",
            pady=(8, 0),
        )
        self._export_e_bilanz_button = ttk.Button(
            self._e_bilanz_tab,
            text="E-Bilanz exportieren",
            command=self._export_e_bilanz,
            state="disabled",
        )
        self._export_e_bilanz_button.pack(
            anchor="w",
            pady=(8, 0),
        )
        self._send_e_bilanz_test_button = ttk.Button(
            self._e_bilanz_tab,
            text="ELSTER-Testübermittlung",
            command=self._send_e_bilanz_test,
            state="disabled",
        )
        self._send_e_bilanz_test_button.pack(
            anchor="w",
            pady=(8, 0),
        )
        self._send_e_bilanz_production_button = ttk.Button(
            self._e_bilanz_tab,
            text="ELSTER-Produktivübermittlung",
            command=self._send_e_bilanz_production,
            state="disabled",
        )
        self._send_e_bilanz_production_button.pack(
            anchor="w",
            pady=(8, 0),
        )

    def _save_bvv_annual_data(self) -> None:
        """Speichert die BVV-Jahresdaten des aktuellen Geschäftsjahres."""

        def parse_decimal(
            value: str,
            *,
            allow_empty: bool = False,
        ) -> Decimal | None:
            normalized = (
                value.strip()
                .replace(".", "")
                .replace(",", ".")
            )

            if not normalized:
                if allow_empty:
                    return None
                return Decimal("0.00")

            return Decimal(normalized)

        try:
            previous_hgb_equity = parse_decimal(
                self._bvv_previous_hgb_equity_override_var.get(),
                allow_empty=True,
            )

            contribution = parse_decimal(
                self._bvv_contribution_var.get(),
            )

            withdrawal_distribution = parse_decimal(
                self._bvv_withdrawal_distribution_var.get(),
            )

            assert contribution is not None
            assert withdrawal_distribution is not None

            data = BvvAnnualData(
                previous_hgb_equity=previous_hgb_equity,
                contribution=contribution,
                withdrawal_distribution=(
                    withdrawal_distribution
                ),
            )

            self._workspace.save_bvv_annual_data(
                data
            )

            self._refresh_bvv_annual_data()

        except (
            ValueError,
            ArithmeticError,
        ) as exc:
            messagebox.showerror(
                "BVV-Daten",
                (
                    "Die BVV-Jahresdaten konnten nicht "
                    "gespeichert werden.\n\n"
                    f"{exc}"
                ),
                parent=self,
            )
            return

        messagebox.showinfo(
            "BVV-Daten",
            "Die BVV-Jahresdaten wurden gespeichert.",
            parent=self,
        )

    def _post_booking(
        self,
        booking: Booking,
    ) -> None:
        """Verbucht und speichert eine Buchung."""

        if self._workspace.is_closed:
            return

        self._workspace.post_booking(booking)

        self._refresh_all()

    def _open_opening_balance(self) -> None:
        """Erfasst, verbucht und speichert die Eröffnungsbilanz."""

        if self._workspace.is_closed:
            return

        dialog = OpeningBalanceDialog(
            self,
            accounts=self._accounts,
            excluded_account_numbers={
                self._opening_balance_account_number,
                self._closing_accounts.income_summary_account,
                self._closing_accounts.profit_account,
                self._closing_accounts.loss_account,
            },
        )

        self.wait_window(dialog)

        if dialog.result is None:
            return

        bookings = self._opening_balance_service.create_bookings(
            opening_balance=dialog.result,
            booking_date=self._context.fiscal_year.start_date,
        )

        for booking in bookings:
            self._workspace.post_booking(booking)

        self._refresh_all()

    def _validate_closing(self) -> None:
        """Prüft den Jahresabschluss."""

        if (
            self._current_income_statement is None
            or self._current_closing_result is None
            or self._current_balance_sheet is None
        ):
            return

        try:
            depreciation_proposals = self._workspace.build_depreciation_proposals()
        except (ValueError, RuntimeError) as exc:
            messagebox.showerror(
                "Abschreibungen konnten nicht geprüft werden",
                str(exc),
                parent=self,
            )
            return

        if depreciation_proposals:
            messagebox.showwarning(
                "Offene Abschreibungen",
                (
                    "Für dieses Geschäftsjahr sind noch "
                    "Abschreibungen zu bearbeiten.\n\n"
                    "Bitte führen Sie zuerst im Bereich "
                    '"Anlagen" die Aktion '
                    '"Abschreibungen prüfen/buchen" aus.'
                ),
                parent=self,
            )
            return

        result = self._workspace.validate_closing(
            balance_sheet=self._current_balance_sheet,
            income_statement=self._current_income_statement,
            closing_result=self._current_closing_result,
            balances=self._current_closing_balances,
            mapper=self._account_mapper,
        )

        self._closing_frame.update_consistency(result)

    def _process_depreciations(self) -> None:
        """Prüft und bucht offene Abschreibungen."""

        try:
            proposals = self._workspace.build_depreciation_proposals()
        except (ValueError, RuntimeError) as exc:
            messagebox.showerror(
                "Abschreibungen konnten nicht vorbereitet werden",
                str(exc),
                parent=self,
            )
            return

        if not proposals:
            messagebox.showinfo(
                "Abschreibungen",
                (
                    "Für dieses Geschäftsjahr sind keine "
                    "offenen Abschreibungen vorhanden."
                ),
                parent=self,
            )
            return

        for proposal in proposals:
            confirmed = messagebox.askyesno(
                "Abschreibung bestätigen",
                (
                    "Für ein Anlagegut wurde folgende lineare "
                    "Abschreibung ermittelt:\n\n"
                    f"Betrag: {proposal.amount:.2f} €\n"
                    f"Aufwandskonto: "
                    f"{proposal.expense_account_number}\n"
                    f"Anlagenkonto: "
                    f"{proposal.asset_account_number}\n"
                    f"Datum: "
                    f"{proposal.depreciation_date:%d.%m.%Y}\n\n"
                    "Soll diese Abschreibung gebucht werden?"
                ),
                parent=self,
            )

            if not confirmed:
                break

            try:
                self._workspace.confirm_depreciation(proposal)
            except (ValueError, RuntimeError) as exc:
                messagebox.showerror(
                    "Abschreibung konnte nicht gebucht werden",
                    str(exc),
                    parent=self,
                )
                break

        # Gebuchte AfA verändert Journal, GuV und Bilanz.
        self._refresh_all()

    def _manage_tax_depreciation_adjustments(self) -> None:
        """Bearbeitet steuerliche AfA-Abweichungen."""

        try:
            depreciations = (
                self._workspace.list_confirmed_depreciations()
            )
            fixed_assets = (
                self._workspace.list_fixed_assets()
            )
        except (ValueError, RuntimeError) as exc:
            messagebox.showerror(
                "Steuerliche AfA-Abweichungen",
                str(exc),
                parent=self,
            )
            return

        if not depreciations:
            messagebox.showinfo(
                "Steuerliche AfA-Abweichungen",
                (
                    "Für dieses Geschäftsjahr sind noch keine "
                    "bestätigten Abschreibungen vorhanden."
                ),
                parent=self,
            )
            return

        fixed_assets_by_id = {
            fixed_asset.fixed_asset_id: fixed_asset
            for fixed_asset in fixed_assets
        }

        for depreciation in depreciations:
            fixed_asset = fixed_assets_by_id.get(
                depreciation.fixed_asset_id
            )

            if fixed_asset is None:
                messagebox.showerror(
                    "Steuerliche AfA-Abweichungen",
                    (
                        "Das Anlagegut zu einer bestätigten "
                        "Abschreibung konnte nicht gefunden werden."
                    ),
                    parent=self,
                )
                return

            try:
                adjustment = (
                    self._workspace
                    .get_tax_depreciation_adjustment(
                        depreciation.depreciation_id
                    )
                )
            except (ValueError, RuntimeError) as exc:
                messagebox.showerror(
                    "Steuerliche AfA-Abweichungen",
                    str(exc),
                    parent=self,
                )
                return

            initial_tax_amount = (
                adjustment.tax_amount
                if adjustment is not None
                else depreciation.amount
            )

            dialog = TaxDepreciationAdjustmentDialog(
                self,
                fixed_asset=fixed_asset,
                depreciation=depreciation,
                initial_tax_amount=initial_tax_amount,
            )
            self.wait_window(
                dialog
            )

            if dialog.result is None:
                break

            try:
                self._workspace.save_tax_depreciation_adjustment(
                    depreciation_id=(
                        depreciation.depreciation_id
                    ),
                    tax_amount=dialog.result,
                )
            except (ValueError, RuntimeError) as exc:
                messagebox.showerror(
                    "Steuerliche AfA-Abweichung konnte "
                    "nicht gespeichert werden",
                    str(exc),
                    parent=self,
                )
                break


    def _close_fiscal_year(self) -> None:
        """Schließt das Geschäftsjahr persistent ab."""

        if self._workspace.is_closed:
            return

        if self._current_income_statement is None:
            return

        confirmed = messagebox.askyesno(
            "Geschäftsjahr abschließen",
            (
                "Das Geschäftsjahr wird nun endgültig "
                "abgeschlossen.\n\n"
                "Dabei werden die Erfolgskonten abgeschlossen "
                "und weitere Buchungen in diesem Geschäftsjahr "
                "gesperrt.\n\n"
                "Möchten Sie fortfahren?"
            ),
            parent=self,
        )

        if not confirmed:
            return

        try:
            result = self._workspace.close_fiscal_year(
                income_statement=self._current_income_statement,
                chart_of_accounts=self._chart_of_accounts,
            )
        except ValueError as exc:
            messagebox.showerror(
                "Jahresabschluss fehlgeschlagen",
                str(exc),
                parent=self,
            )
            return

        self._refresh_all()

        self._closing_frame.update_net_income(result.net_income)

        self._closing_frame.mark_closed()

        messagebox.showinfo(
            "Jahresabschluss",
            "Das Geschäftsjahr wurde erfolgreich abgeschlossen.",
            parent=self,
        )

    def _refresh_all(self) -> None:
        """Aktualisiert alle sichtbaren Buchhaltungsdaten."""

        self._refresh_overview()
        self._refresh_journal()
        self._refresh_fixed_assets()
        self._refresh_balance_sheet()
        self._refresh_trial_balance_report()
        self._refresh_closing()
        self._refresh_taxonomy_status()
        self._refresh_bvv_annual_data()
        self._refresh_e_bilanz()
        self._update_editing_state()
        self.update_idletasks()

    def _refresh_taxonomy_status(self) -> None:
        """Aktualisiert den Taxonomiestatus des Geschäftsjahres."""

        status = self._workspace.taxonomy_status

        if status.complete:
            status_text = "installiert und vollständig"
        elif status.installed:
            status_text = "installiert, aber unvollständig"
        else:
            status_text = "nicht installiert"

        if status.usable:
            self._install_taxonomy_button.config(state="disabled")
        else:
            self._install_taxonomy_button.config(state="normal")

        self._taxonomy_status.config(
            text=(
                "Benötigte Taxonomie: "
                f"{status.required_version.value}\n"
                f"Status: {status_text}"
            ),
        )

    def _install_required_taxonomy(self) -> None:
        """Installiert die benötigte Taxonomie."""

        try:
            self._workspace.install_required_taxonomy()
        except (
            URLError,
            BadZipFile,
            ValueError,
            RuntimeError,
            OSError,
        ) as exc:
            messagebox.showerror(
                "Taxonomie konnte nicht installiert werden",
                str(exc),
                parent=self,
            )
            return

        self._refresh_taxonomy_status()
        self._refresh_e_bilanz()

        messagebox.showinfo(
            "Taxonomie",
            "Die benötigte Taxonomie wurde erfolgreich installiert.",
            parent=self,
        )

    def _refresh_bvv_annual_data(self) -> None:
        """Aktualisiert die BVV-Jahresdaten des Geschäftsjahres."""

        data = self._workspace.load_bvv_annual_data()

        effective_previous_hgb_equity = (
            self._workspace.effective_previous_hgb_equity(
                chart_of_accounts=self._chart_of_accounts,
            )
        )

        if effective_previous_hgb_equity is None:
            self._bvv_effective_previous_hgb_equity_var.set(
                "nicht ermittelbar"
            )
        else:
            self._bvv_effective_previous_hgb_equity_var.set(
                (
                    str(effective_previous_hgb_equity)
                    .replace(".", ",")
                    + " €"
                )
            )

        if data is None:
            self._bvv_previous_hgb_equity_source_var.set(
                "automatisch ermittelt"
                if effective_previous_hgb_equity is not None
                else "keine Angabe vorhanden"
            )
            self._bvv_previous_hgb_equity_override_var.set("")
            self._bvv_contribution_var.set("0,00")
            self._bvv_withdrawal_distribution_var.set("0,00")
            return

        if data.previous_hgb_equity is None:
            self._bvv_previous_hgb_equity_source_var.set(
                "automatisch ermittelt"
                if effective_previous_hgb_equity is not None
                else "keine Angabe vorhanden"
            )
            self._bvv_previous_hgb_equity_override_var.set("")
        else:
            self._bvv_previous_hgb_equity_source_var.set(
                "manuell gespeichert"
            )
            self._bvv_previous_hgb_equity_override_var.set(
                str(data.previous_hgb_equity).replace(".", ",")
            )

        self._bvv_contribution_var.set(
            str(data.contribution).replace(".", ",")
        )

        self._bvv_withdrawal_distribution_var.set(
            str(
                data.withdrawal_distribution
            ).replace(".", ",")
        )

    def _refresh_e_bilanz(self) -> None:
        """Aktualisiert den Zustand des E-Bilanz-Arbeitsbereichs."""

        self._export_e_bilanz_button.config(
            state="disabled",
        )
        self._send_e_bilanz_test_button.config(
            state="disabled",
        )
        self._send_e_bilanz_production_button.config(
            state="disabled",
        )

        if not self._workspace.is_closed:
            self._e_bilanz_status.config(
                text=(
                    "Die E-Bilanz kann erst nach dem "
                    "Jahresabschluss vorbereitet werden."
                ),
            )
            self._prepare_e_bilanz_button.config(
                state="disabled",
            )
            self._build_e_bilanz_button.config(
                state="disabled",
            )
            self._build_e_bilanz_button.config(
                state="disabled",
            )
            self._validate_e_bilanz_button.config(
                state="disabled",
            )
            return

        self._prepare_e_bilanz_button.config(
            state="normal",
        )

        if self._current_e_bilanz_preparation is None:
            self._e_bilanz_status.config(
                text=(
                    "Das Geschäftsjahr ist abgeschlossen. "
                    "Die E-Bilanz kann vorbereitet werden."
                ),
            )
            self._build_e_bilanz_button.config(
                state="disabled",
            )
            self._build_e_bilanz_button.config(
                state="disabled",
            )
            self._validate_e_bilanz_button.config(
                state="disabled",
            )
            return

        preparation = self._current_e_bilanz_preparation

        taxonomy_status = self._workspace.taxonomy_status

        if taxonomy_status.usable:
            self._build_e_bilanz_button.config(
                state="normal",
            )
        else:
            self._build_e_bilanz_button.config(
                state="disabled",
            )

        if self._current_e_bilanz_document is None:
            self._validate_e_bilanz_button.config(
                state="disabled",
            )
        else:
            self._validate_e_bilanz_button.config(
                state="normal",
            )

            if self._current_e_bilanz_arelle_valid:
                self._export_e_bilanz_button.config(
                    state="normal",
                )

                if (
                    self._elster_bilanz_transmission_service
                    is not None
                ):
                    self._send_e_bilanz_test_button.config(
                        state="normal",
                    )
                    self._send_e_bilanz_production_button.config(
                        state="normal",
                    )

        status_text = (
            "Die E-Bilanz wurde vorbereitet.\n"
            f"Bilanzpositionen: "
            f"{len(preparation.balance_sheet_amounts)}\n"
            f"GuV-Positionen: "
            f"{len(preparation.income_statement_amounts)}"
        )

        if not taxonomy_status.usable:
            status_text += (
                "\n\nDie benötigte Taxonomie ist nicht vollständig installiert."
            )

        self._e_bilanz_status.config(
            text=status_text,
        )

    def _prepare_e_bilanz(self) -> None:
        """Bereitet die Abschlusswerte für die E-Bilanz auf."""

        if not self._workspace.is_closed:
            messagebox.showwarning(
                "E-Bilanz",
                "Das Geschäftsjahr ist noch nicht abgeschlossen.",
                parent=self,
            )
            return

        if self._current_income_statement is None:
            messagebox.showwarning(
                "E-Bilanz",
                "Es steht keine GuV für die E-Bilanz-Vorbereitung zur Verfügung.",
                parent=self,
            )
            return

        try:
            preparation = self._workspace.prepare_e_bilanz(
                income_statement=self._current_income_statement,
            )
        except ValueError as exc:
            messagebox.showerror(
                "E-Bilanz konnte nicht vorbereitet werden",
                str(exc),
                parent=self,
            )
            return

        self._current_e_bilanz_preparation = preparation
        self._current_e_bilanz_document = None
        self._current_e_bilanz_arelle_valid = False

        self._refresh_e_bilanz()


    def _build_e_bilanz(self) -> None:
        """Erzeugt die E-Bilanz aus den vorbereiteten Abschlusswerten."""

        if self._current_e_bilanz_preparation is None:
            messagebox.showwarning(
                "E-Bilanz",
                "Die E-Bilanz wurde noch nicht vorbereitet.",
                parent=self,
            )
            return

        try:
            document = self._workspace.build_e_bilanz(
                preparation=self._current_e_bilanz_preparation,
                chart_of_accounts=self._chart_of_accounts,
            )
        except (ValueError, FileNotFoundError, RuntimeError) as exc:
            messagebox.showerror(
                "E-Bilanz konnte nicht erzeugt werden",
                str(exc),
                parent=self,
            )
            return

        self._current_e_bilanz_document = document
        self._current_e_bilanz_arelle_valid = False

        self._refresh_e_bilanz()

        messagebox.showinfo(
            "E-Bilanz",
            "Die E-Bilanz wurde erfolgreich erzeugt.",
            parent=self,
        )

    def _validate_e_bilanz(self) -> None:
        """Validiert die erzeugte E-Bilanz mit Arelle."""

        if self._current_e_bilanz_document is None:
            messagebox.showwarning(
                "E-Bilanz",
                "Die E-Bilanz wurde noch nicht erzeugt.",
                parent=self,
            )
            return

        try:
            result = self._workspace.validate_e_bilanz(self._current_e_bilanz_document)
        except (ValueError, RuntimeError) as exc:
            messagebox.showerror(
                "E-Bilanz konnte nicht validiert werden",
                str(exc),
                parent=self,
            )
            return

        if result.is_valid:
            self._current_e_bilanz_arelle_valid = True
            self._refresh_e_bilanz()

            messagebox.showinfo(
                "E-Bilanz",
                "Die E-Bilanz wurde von Arelle erfolgreich validiert.",
                parent=self,
            )
            return

        self._current_e_bilanz_arelle_valid = False
        self._refresh_e_bilanz()

        errors = "\n".join(result.errors)

        messagebox.showerror(
            "E-Bilanz-Validierung fehlgeschlagen",
            (f"Arelle hat Fehler in der E-Bilanz festgestellt.\n\n{errors}"),
            parent=self,
        )

    def _send_e_bilanz_test(self) -> None:
        """Übermittelt die E-Bilanz als echte ELSTER-Testsendung."""

        if self._elster_bilanz_transmission_service is None:
            messagebox.showerror(
                "ELSTER-Testübermittlung",
                (
                    "Die ERiC-/ELSTER-Konfiguration ist "
                    "nicht vollständig."
                ),
                parent=self,
            )
            return

        if self._current_e_bilanz_document is None:
            messagebox.showwarning(
                "ELSTER-Testübermittlung",
                "Die E-Bilanz wurde noch nicht erzeugt.",
                parent=self,
            )
            return

        if not self._current_e_bilanz_arelle_valid:
            messagebox.showwarning(
                "ELSTER-Testübermittlung",
                (
                    "Die E-Bilanz muss zuerst erfolgreich "
                    "mit Arelle validiert werden."
                ),
                parent=self,
            )
            return

        confirmation = simpledialog.askstring(
            "ELSTER-Testübermittlung",
            (
                "ACHTUNG: Diese Funktion stellt eine echte "
                "Verbindung zum ELSTER-Server her.\n\n"
                "Der Datensatz wird ausschließlich als "
                "Testsendung mit dem ELSTER-Testmerker "
                "700000004 übertragen.\n\n"
                "Zum Start bitte exakt TESTSENDUNG eingeben:"
            ),
            parent=self,
        )

        if confirmation != "TESTSENDUNG":
            return

        try:
            master_data = (
                self._workspace.load_company_master_data()
            )

            validated = (
                self._elster_bilanz_transmission_service
                .validate_test_transmission(
                    xbrl_xml=(
                        self._current_e_bilanz_document.xml
                    ),
                    master_data=master_data,
                    balance_sheet_date=(
                        self._context.fiscal_year.end_date
                    ),
                )
            )

            self._elster_bilanz_transmission_service\
                .send_test_transmission(
                    validated=validated,
                )

        except (
            ValueError,
            FileNotFoundError,
            RuntimeError,
        ) as exc:
            messagebox.showerror(
                "ELSTER-Testübermittlung fehlgeschlagen",
                str(exc),
                parent=self,
            )
            return

        messagebox.showinfo(
            "ELSTER-Testübermittlung",
            (
                "Die ELSTER-Testübermittlung wurde "
                "ohne Fehler abgeschlossen.\n\n"
                "Testmerker: 700000004\n\n"
                "Es wurde keine produktive "
                "Steuerübermittlung durchgeführt."
            ),
            parent=self,
        )

    def _send_e_bilanz_production(self) -> None:
        """Übermittelt die E-Bilanz produktiv an ELSTER."""

        if self._elster_bilanz_transmission_service is None:
            messagebox.showerror(
                "ELSTER-Produktivübermittlung",
                (
                    "Die ERiC-/ELSTER-Konfiguration ist "
                    "nicht vollständig."
                ),
                parent=self,
            )
            return

        if self._current_e_bilanz_document is None:
            messagebox.showwarning(
                "ELSTER-Produktivübermittlung",
                "Die E-Bilanz wurde noch nicht erzeugt.",
                parent=self,
            )
            return

        if not self._current_e_bilanz_arelle_valid:
            messagebox.showwarning(
                "ELSTER-Produktivübermittlung",
                (
                    "Die E-Bilanz muss zuerst erfolgreich "
                    "mit Arelle validiert werden."
                ),
                parent=self,
            )
            return

        confirmation = simpledialog.askstring(
            "ELSTER-Produktivübermittlung",
            (
                "ACHTUNG: Dies ist eine PRODUKTIVE "
                "ELSTER-Übermittlung.\n\n"
                "Der Datensatz wird ohne Testmerker an ELSTER "
                "übertragen und ist keine Testsendung.\n\n"
                "Bitte prüfen Sie vor dem Versand nochmals "
                "Mandant, Geschäftsjahr und E-Bilanz.\n\n"
                "Zum endgültigen Start bitte exakt "
                "PRODUKTIV SENDEN eingeben:"
            ),
            parent=self,
        )

        if confirmation != "PRODUKTIV SENDEN":
            return

        try:
            master_data = self._workspace.load_company_master_data()

            validated = (
                self._elster_bilanz_transmission_service
                .validate_production_transmission(
                    xbrl_xml=self._current_e_bilanz_document.xml,
                    master_data=master_data,
                    balance_sheet_date=self._context.fiscal_year.end_date,
                )
            )

            self._elster_bilanz_transmission_service.send_production_transmission(
                validated=validated,
            )
        except (ValueError, FileNotFoundError, RuntimeError) as exc:
            messagebox.showerror(
                "ELSTER-Produktivübermittlung fehlgeschlagen",
                str(exc),
                parent=self,
            )
            return

        messagebox.showinfo(
            "ELSTER-Produktivübermittlung",
            (
                "Die E-Bilanz wurde ohne Fehler produktiv "
                "an ELSTER übermittelt."
            ),
            parent=self,
        )

    def _export_e_bilanz(self) -> None:
        """Exportiert die erfolgreich validierte E-Bilanz."""

        if self._current_e_bilanz_document is None:
            messagebox.showwarning(
                "E-Bilanz",
                "Die E-Bilanz wurde noch nicht erzeugt.",
                parent=self,
            )
            return

        filename = filedialog.asksaveasfilename(
            parent=self,
            title="E-Bilanz exportieren",
            defaultextension=".xbrl",
            filetypes=(
                ("XBRL-Dateien", "*.xbrl"),
                ("Alle Dateien", "*.*"),
            ),
        )

        if not filename:
            return

        target = Path(filename)

        try:
            exported_path = self._workspace.export_e_bilanz(
                document=self._current_e_bilanz_document,
                target=target,
            )
        except (ValueError, OSError) as exc:
            messagebox.showerror(
                "E-Bilanz konnte nicht exportiert werden",
                str(exc),
                parent=self,
            )
            return

        messagebox.showinfo(
            "E-Bilanz",
            (f"Die E-Bilanz wurde erfolgreich exportiert.\n\n{exported_path}"),
            parent=self,
        )

    def _refresh_overview(self) -> None:
        """Aktualisiert die Kontenübersicht."""

        self._journal_status.config(text=(f"Journal: {len(self._journal)} Buchungen"))

        for item in self._account_table.get_children():
            self._account_table.delete(item)

        for account in self._accounts:
            debit = ZERO
            credit = ZERO
            debit_balance = ZERO
            credit_balance = ZERO

            try:
                ledger_account = self._ledger.get_account(account.number)
            except KeyError:
                pass
            else:
                debit = ledger_account.debit
                credit = ledger_account.credit
                debit_balance = ledger_account.debit_balance
                credit_balance = ledger_account.credit_balance

            balance = self._display_account_balance(
                account_type=account.account_type,
                debit_balance=debit_balance,
                credit_balance=credit_balance,
            )

            self._account_table.insert(
                "",
                "end",
                values=(
                    account.number,
                    account.name,
                    self._format_amount(debit),
                    self._format_amount(credit),
                    balance,
                ),
            )


    def _refresh_journal(self) -> None:
        """Aktualisiert die Journalanzeige."""

        for item in self._journal_table.get_children():
            self._journal_table.delete(item)

        account_names = {account.number: account.name for account in self._accounts}

        for booking in self._journal:
            first_line = True

            for line in booking.lines:
                account_name = account_names.get(
                    line.account_number,
                    "Unbekanntes Konto",
                )

                account_display = f"{line.account_number} – {account_name}"

                if line.is_debit:
                    side = "Soll"
                else:
                    side = "Haben"

                self._journal_table.insert(
                    "",
                    "end",
                    values=(
                        (
                            booking.booking_date.strftime("%d.%m.%Y")
                            if first_line
                            else ""
                        ),
                        (booking.voucher_no or "" if first_line else ""),
                        (booking.description or "" if first_line else ""),
                        account_display,
                        side,
                        self._format_amount(line.amount),
                    ),
                )

                first_line = False

    def _refresh_balance_sheet(self) -> None:
        """Erzeugt und aktualisiert die laufende Bilanz."""

        self._current_balance_sheet = None

        balance_sheet_account_types = (
            AccountType.ASSET,
            AccountType.LIABILITY,
            AccountType.EQUITY,
        )

        income_statement_account_types = (
            AccountType.REVENUE,
            AccountType.EXPENSE,
        )

        balance_sheet_balances = tuple(
            balance
            for balance in self._ledger.balances()
            if self._account_types.get(balance.account_number)
            in balance_sheet_account_types
            and (balance.debit_balance > ZERO or balance.credit_balance > ZERO)
        )

        income_statement_ledger = (
            self._workspace.pre_closing_ledger
            if self._workspace.is_closed
            else self._ledger
        )

        income_statement_balances = tuple(
            balance
            for balance in income_statement_ledger.balances()
            if self._account_types.get(balance.account_number)
            in income_statement_account_types
            and (balance.debit_balance > ZERO or balance.credit_balance > ZERO)
        )

        self._current_closing_balances = (
            balance_sheet_balances + income_statement_balances
        )

        income_statement_amounts = self._financial_statement_builder.build(
            balances=income_statement_balances,
            root_positions=(self._income_statement,),
        )

        income_statement = IncomeStatement(
            income_statement=self._income_statement,
            amounts=income_statement_amounts,
        )

        self._current_income_statement = income_statement

        net_income = self._closing_service.calculate_net_income(
            income_statement=income_statement,
        )

        self._income_statement_frame.update_income_statement(
            income_statement=income_statement,
            net_income=net_income,
        )

        closing_result = ClosingResult(
            net_income=net_income,
        )

        self._current_closing_result = closing_result

        equity = next(
            position
            for position in self._liabilities.children
            if position.code == "HGB.266.PASSIVA.A"
        )

        result_position = next(
            position
            for position in equity.children
            if position.code == "HGB.266.PASSIVA.A.V"
        )

        try:
            amounts = self._financial_statement_builder.build(
                balances=balance_sheet_balances,
                root_positions=(
                    self._assets,
                    self._liabilities,
                ),
                closing_result=closing_result,
                result_position=result_position,
            )
        except ValueError as exc:
            message = str(exc)

            if (
                "no debit position defined for account" not in message
                and "no credit position defined for account" not in message
            ):
                raise

            self._balance_sheet_frame.show_mapping_error(
                self._format_mapping_error(message)
            )

            return

        balance_sheet = BalanceSheet(
            assets=self._assets,
            liabilities=self._liabilities,
            amounts=amounts,
        )

        self._current_balance_sheet = balance_sheet

        self._balance_sheet_frame.update_balance_sheet(balance_sheet)

    def _refresh_closing(self) -> None:
        """Aktualisiert den sichtbaren Abschlussstatus."""

        managed_fiscal_year = self._workspace.managed_fiscal_year

        self._closing_frame.update_fiscal_year_status(managed_fiscal_year.status)

        if self._current_closing_result is None:
            return

        self._closing_frame.update_net_income(self._current_closing_result.net_income)

    @staticmethod
    def _format_amount(
        amount: object,
    ) -> str:
        """Formatiert einen Geldbetrag."""

        formatted = f"{amount:,.2f}"

        return formatted.replace(",", "X").replace(".", ",").replace("X", ".")

    @staticmethod
    def _format_mapping_error(
        message: str,
    ) -> str:
        """Formatiert einen Mappingfehler für die GUI."""

        if "no credit position defined for account" in message:
            account_number = message.rsplit(" ", 1)[-1]

            return (
                f"Konto {account_number} weist einen Habensaldo auf. "
                "Für diesen Fall ist keine Bilanzzuordnung hinterlegt."
            )

        if "no debit position defined for account" in message:
            account_number = message.rsplit(" ", 1)[-1]

            return (
                f"Konto {account_number} weist einen Sollsaldo auf. "
                "Für diesen Fall ist keine Bilanzzuordnung hinterlegt."
            )

        return message

    @classmethod
    def _display_account_balance(
        cls,
        *,
        account_type: AccountType,
        debit_balance: object,
        credit_balance: object,
    ) -> str:
        """Formatiert den fachlichen Kontosaldo."""

        if account_type in (
            AccountType.ASSET,
            AccountType.EXPENSE,
        ):
            if debit_balance > ZERO:
                return cls._format_amount(debit_balance)

            if credit_balance > ZERO:
                return "-" + cls._format_amount(credit_balance)

        if account_type in (
            AccountType.LIABILITY,
            AccountType.EQUITY,
            AccountType.REVENUE,
        ):
            if credit_balance > ZERO:
                return cls._format_amount(credit_balance)

            if debit_balance > ZERO:
                return "-" + cls._format_amount(debit_balance)

        return cls._format_amount(ZERO)

    def _update_editing_state(self) -> None:
        """Passt die Eingabemöglichkeiten an den Geschäftsjahresstatus an."""

        enabled = self._workspace.is_open

        if enabled:
            self._opening_balance_button.state(["!disabled"])
            self._new_account_button.state(["!disabled"])
            self._edit_account_button.state(["!disabled"])
        else:
            self._opening_balance_button.state(["disabled"])
            self._new_account_button.state(["disabled"])
            self._edit_account_button.state(["disabled"])

        self._booking_frame.set_enabled(enabled)
        self._vat_booking_frame.set_enabled(enabled)

        self._booking_mode_box.configure(
            state=(
                "readonly"
                if enabled
                else "disabled"
            )
        )

        if enabled:
            self._add_fixed_asset_button.state(
                ["!disabled"]
            )
            self._edit_fixed_asset_button.state(
                ["!disabled"]
            )
            self._delete_fixed_asset_button.state(
                ["!disabled"]
            )
            self._link_fixed_asset_acquisition_button.state(
                ["!disabled"]
            )
            self._link_fixed_asset_disposal_button.state(
                ["!disabled"]
            )
            self._process_depreciations_button.state(
                ["!disabled"]
            )
            self._tax_depreciation_adjustments_button.state(
                ["!disabled"]
            )
        else:
            self._add_fixed_asset_button.state(
                ["disabled"]
            )
            self._edit_fixed_asset_button.state(
                ["disabled"]
            )
            self._delete_fixed_asset_button.state(
                ["disabled"]
            )
            self._link_fixed_asset_acquisition_button.state(
                ["disabled"]
            )
            self._link_fixed_asset_disposal_button.state(
                ["disabled"]
            )
            self._process_depreciations_button.state(
                ["disabled"]
            )
            self._tax_depreciation_adjustments_button.state(
                ["disabled"]
            )

    def _open_company_master_data(
        self,
    ) -> None:
        """Öffnet die Unternehmensstammdaten."""

        try:
            master_data = self._workspace.load_company_master_data()
        except ValueError as exc:
            messagebox.showerror(
                "Unternehmensstammdaten",
                str(exc),
                parent=self,
            )
            return

        dialog = CompanyMasterDataDialog(
            self,
            master_data=master_data,
        )

        self.wait_window(dialog)

        if dialog.result is None:
            return

        try:
            self._workspace.save_company_master_data(dialog.result)
        except ValueError as exc:
            messagebox.showerror(
                "Unternehmensstammdaten",
                str(exc),
                parent=self,
            )
            return

        messagebox.showinfo(
            "Unternehmensstammdaten",
            "Die Unternehmensstammdaten wurden gespeichert.",
            parent=self,
        )


    def _open_account_configuration(
        self,
    ) -> None:
        """Öffnet die mandantenspezifische Kontenkonfiguration."""

        try:
            (
                control_accounts,
                vat_accounts,
                account_roles,
            ) = self._workspace.load_account_configuration()

        except (
            RuntimeError,
            ValueError,
        ) as exc:
            messagebox.showerror(
                "Kontenkonfiguration",
                str(exc),
                parent=self,
            )
            return

        dialog = AccountConfigurationDialog(
            self,
            accounts=self._accounts,
            control_accounts=control_accounts,
            vat_accounts=vat_accounts,
            account_roles=account_roles,
        )

        self.wait_window(dialog)

        if dialog.result is None:
            return

        (
            new_control_accounts,
            new_vat_accounts,
            new_account_roles,
        ) = dialog.result

        try:
            self._workspace.update_account_configuration(
                control_accounts=new_control_accounts,
                vat_accounts=new_vat_accounts,
                account_roles=new_account_roles,
            )

        except (
            RuntimeError,
            ValueError,
        ) as exc:
            messagebox.showerror(
                "Kontenkonfiguration",
                str(exc),
                parent=self,
            )
            return

        self._closing_accounts = ClosingAccounts(
            income_summary_account=(
                new_control_accounts.income_summary_account
            ),
            profit_account=(
                new_control_accounts.profit_account
            ),
            loss_account=(
                new_control_accounts.loss_account
            ),
        )

        self._opening_balance_account_number = (
            new_control_accounts.opening_balance_account
        )

        self._depreciation_expense_account_number = (
            new_control_accounts.depreciation_expense_account
        )

        self._vat_accounts = new_vat_accounts

        self._opening_balance_service = OpeningBalanceService(
            opening_balance_account_number=(
                self._opening_balance_account_number
            ),
        )

        messagebox.showinfo(
            "Kontenkonfiguration",
            "Die Kontenkonfiguration wurde gespeichert.",
            parent=self,
        )


    def _open_shareholders(
        self,
    ) -> None:
        """Öffnet die Gesellschafterverwaltung."""

        dialog = ShareholdersDialog(
            self,
            workspace=self._workspace,
        )

        self.wait_window(dialog)

    def _refresh_fixed_assets(self) -> None:
        """Aktualisiert die Liste der Anlagegüter."""

        for item in self._fixed_asset_table.get_children():
            self._fixed_asset_table.delete(item)

        try:
            assets = self._workspace.list_fixed_assets()
        except RuntimeError:
            return

        self._fixed_assets_by_id = {
            str(asset.fixed_asset_id): asset
            for asset in assets
        }

        for asset in assets:
            status = (
                "Aktiv"
                if asset.status.value == "ACTIVE"
                else "Abgegangen"
            )

            try:
                acquisition_linked = (
                    self._workspace.has_fixed_asset_acquisition(
                        asset.fixed_asset_id
                    )
                )
            except RuntimeError:
                acquisition_linked = False

            acquisition_booking = (
                "zugeordnet"
                if acquisition_linked
                else "nicht zugeordnet"
            )

            self._fixed_asset_table.insert(
                "",
                "end",
                iid=str(asset.fixed_asset_id),
                values=(
                    asset.asset_code,
                    asset.description,
                    (
                        f"{asset.acquisition_date:%d.%m.%Y}"
                    ),
                    self._format_amount(
                        asset.acquisition_cost
                    ),
                    asset.useful_life_months,
                    asset.asset_account_number,
                    (
                        asset.depreciation_expense_account_number
                    ),
                    acquisition_booking,
                    status,
                ),
            )
    def _selected_fixed_asset(self):
        """Gibt das aktuell ausgewählte Anlagegut zurück."""

        selection = self._fixed_asset_table.selection()

        if not selection:
            return None

        fixed_asset_id = selection[0]

        return self._fixed_assets_by_id.get(
            fixed_asset_id
        )

    def _open_edit_fixed_asset(self) -> None:
        """Öffnet ein Anlagegut zur Bearbeitung."""

        if not self._workspace.is_open:
            return

        fixed_asset = self._selected_fixed_asset()

        if fixed_asset is None:
            messagebox.showinfo(
                "Anlagegut bearbeiten",
                "Bitte zuerst ein Anlagegut auswählen.",
                parent=self,
            )
            return

        try:
            acquisition_linked = (
                self._workspace.has_fixed_asset_acquisition(
                    fixed_asset.fixed_asset_id
                )
            )
        except RuntimeError as exc:
            messagebox.showerror(
                "Anlagegut kann nicht bearbeitet werden",
                str(exc),
                parent=self,
            )
            return

        dialog = NewFixedAssetDialog(
            self,
            company_id=(
                self._context.company.company_id
            ),
            depreciation_expense_account_number=(
                self._depreciation_expense_account_number
            ),
            fixed_asset=fixed_asset,
            acquisition_linked=acquisition_linked,
        )
        self.wait_window(dialog)

        if dialog.result is None:
            return

        try:
            self._workspace.update_fixed_asset(
                dialog.result
            )
        except (
            ValueError,
            RuntimeError,
        ) as exc:
            messagebox.showerror(
                "Anlagegut kann nicht bearbeitet werden",
                str(exc),
                parent=self,
            )
            return

        self._refresh_fixed_assets()

        messagebox.showinfo(
            "Anlagegut",
            "Das Anlagegut wurde geändert.",
            parent=self,
        )

    def _delete_fixed_asset(self) -> None:
        """Löscht ein noch nicht buchungswirksames Anlagegut."""

        if not self._workspace.is_open:
            return

        fixed_asset = self._selected_fixed_asset()

        if fixed_asset is None:
            messagebox.showinfo(
                "Anlagegut löschen",
                "Bitte zuerst ein Anlagegut auswählen.",
                parent=self,
            )
            return

        confirmed = messagebox.askyesno(
            "Anlagegut löschen",
            (
                f"Soll das Anlagegut "
                f"„{fixed_asset.asset_code} – "
                f"{fixed_asset.description}“ "
                "wirklich gelöscht werden?\n\n"
                "Dieser Vorgang kann nicht rückgängig "
                "gemacht werden."
            ),
            parent=self,
        )

        if not confirmed:
            return

        try:
            self._workspace.delete_fixed_asset(
                fixed_asset.fixed_asset_id
            )
        except (
            ValueError,
            RuntimeError,
        ) as exc:
            messagebox.showerror(
                "Anlagegut kann nicht gelöscht werden",
                str(exc),
                parent=self,
            )
            return

        self._refresh_fixed_assets()

        messagebox.showinfo(
            "Anlagegut",
            "Das Anlagegut wurde gelöscht.",
            parent=self,
        )

    def _open_new_fixed_asset(self) -> None:
        """Öffnet den Dialog für ein neues Anlagegut."""

        if not self._workspace.is_open:
            return

        dialog = NewFixedAssetDialog(
            self,
            company_id=(self._context.company.company_id),
            depreciation_expense_account_number=(
                self._depreciation_expense_account_number
            ),
        )
        self.wait_window(dialog)

        if dialog.result is None:
            return

        try:
            self._workspace.add_fixed_asset(dialog.result)
        except (
            ValueError,
            RuntimeError,
        ) as exc:
            messagebox.showerror(
                "Anlagegut kann nicht angelegt werden",
                str(exc),
                parent=self,
            )
            return

        self._refresh_fixed_assets()

        messagebox.showinfo(
            "Anlagegut",
            "Das Anlagegut wurde angelegt.",
            parent=self,
        )

    def _open_link_fixed_asset_acquisition(
        self,
    ) -> None:
        """Ordnet eine vorhandene Buchung einem Anlagegut zu."""

        if not self._workspace.is_open:
            return

        fixed_asset = self._selected_fixed_asset()

        if fixed_asset is None:
            messagebox.showinfo(
                "Anschaffungsbuchung zuordnen",
                "Bitte zuerst ein Anlagegut auswählen.",
                parent=self,
            )
            return

        try:
            if self._workspace.has_fixed_asset_acquisition(
                fixed_asset.fixed_asset_id
            ):
                messagebox.showinfo(
                    "Anschaffungsbuchung zuordnen",
                    (
                        "Dem ausgewählten Anlagegut ist bereits "
                        "eine Anschaffungsbuchung zugeordnet."
                    ),
                    parent=self,
                )
                return
        except RuntimeError as exc:
            messagebox.showerror(
                "Anschaffungsbuchung kann nicht zugeordnet werden",
                str(exc),
                parent=self,
            )
            return

        candidates: list[
            AcquisitionBookingCandidate
        ] = []

        for booking in self._workspace.journal.bookings:
            for position, line in enumerate(
                booking.lines
            ):
                if (
                    line.account_number
                    != fixed_asset.asset_account_number
                ):
                    continue

                if line.side is not EntrySide.DEBIT:
                    continue

                if (
                    line.amount
                    != fixed_asset.acquisition_cost
                ):
                    continue

                candidates.append(
                    AcquisitionBookingCandidate(
                        booking_id=booking.booking_id,
                        booking_line_position=position,
                        booking_date_text=(
                            booking.booking_date.strftime(
                                "%d.%m.%Y"
                            )
                        ),
                        voucher_no=(
                            booking.voucher_no or ""
                        ),
                        description=(
                            booking.description or ""
                        ),
                        account_number=(
                            line.account_number
                        ),
                        amount=line.amount,
                    )
                )

        if not candidates:
            messagebox.showinfo(
                "Anschaffungsbuchung zuordnen",
                (
                    "Es wurde keine passende "
                    "Anschaffungsbuchung gefunden."
                ),
                parent=self,
            )
            return

        dialog = FixedAssetAcquisitionLinkDialog(
            self,
            candidates=tuple(candidates),
        )

        self.wait_window(dialog)

        candidate = dialog.selected_candidate

        if candidate is None:
            return

        try:
            self._workspace.link_fixed_asset_acquisition(
                fixed_asset_id=(
                    fixed_asset.fixed_asset_id
                ),
                booking_id=(
                    candidate.booking_id
                ),
                booking_line_position=(
                    candidate.booking_line_position
                ),
            )
        except (
            ValueError,
            RuntimeError,
        ) as exc:
            messagebox.showerror(
                (
                    "Anschaffungsbuchung konnte "
                    "nicht zugeordnet werden"
                ),
                str(exc),
                parent=self,
            )
            return

        messagebox.showinfo(
            "Anschaffungsbuchung",
            (
                "Die Anschaffungsbuchung wurde "
                "dem Anlagegut zugeordnet."
            ),
            parent=self,
        )

        self._refresh_fixed_assets()

    def _open_link_fixed_asset_disposal(
        self,
    ) -> None:
        """Ordnet eine vorhandene Abgangsbuchung einem Anlagegut zu."""

        if not self._workspace.is_open:
            return

        fixed_asset = self._selected_fixed_asset()

        if fixed_asset is None:
            messagebox.showinfo(
                "Abgangsbuchung zuordnen",
                "Bitte zuerst ein Anlagegut auswählen.",
                parent=self,
            )
            return

        if fixed_asset.status is not FixedAssetStatus.ACTIVE:
            messagebox.showinfo(
                "Abgangsbuchung zuordnen",
                "Das ausgewählte Anlagegut ist bereits abgegangen.",
                parent=self,
            )
            return

        try:
            acquisition_linked = (
                self._workspace.has_fixed_asset_acquisition(
                    fixed_asset.fixed_asset_id
                )
            )
        except RuntimeError as exc:
            messagebox.showerror(
                "Abgangsbuchung kann nicht zugeordnet werden",
                str(exc),
                parent=self,
            )
            return

        if not acquisition_linked:
            messagebox.showinfo(
                "Abgangsbuchung zuordnen",
                (
                    "Dem ausgewählten Anlagegut ist noch keine "
                    "Anschaffungsbuchung zugeordnet."
                ),
                parent=self,
            )
            return

        candidates: list[
            DisposalBookingCandidate
        ] = []

        for booking in self._workspace.journal.bookings:
            if (
                booking.booking_date
                < fixed_asset.acquisition_date
            ):
                continue

            for position, line in enumerate(
                booking.lines
            ):
                if (
                    line.account_number
                    != fixed_asset.asset_account_number
                ):
                    continue

                if line.side is not EntrySide.CREDIT:
                    continue

                candidates.append(
                    DisposalBookingCandidate(
                        booking_id=booking.booking_id,
                        booking_line_position=position,
                        booking_date_text=(
                            booking.booking_date.strftime(
                                "%d.%m.%Y"
                            )
                        ),
                        voucher_no=(
                            booking.voucher_no or ""
                        ),
                        description=(
                            booking.description or ""
                        ),
                        account_number=(
                            line.account_number
                        ),
                        amount=line.amount,
                    )
                )

        if not candidates:
            messagebox.showinfo(
                "Abgangsbuchung zuordnen",
                (
                    "Es wurde keine passende "
                    "Abgangsbuchung gefunden."
                ),
                parent=self,
            )
            return

        dialog = FixedAssetDisposalLinkDialog(
            self,
            candidates=tuple(candidates),
        )

        self.wait_window(dialog)

        candidate = dialog.selected_candidate

        if candidate is None:
            return

        try:
            self._workspace.link_fixed_asset_disposal(
                fixed_asset_id=(
                    fixed_asset.fixed_asset_id
                ),
                booking_id=(
                    candidate.booking_id
                ),
                booking_line_position=(
                    candidate.booking_line_position
                ),
            )
        except (
            ValueError,
            RuntimeError,
        ) as exc:
            messagebox.showerror(
                (
                    "Abgangsbuchung konnte "
                    "nicht zugeordnet werden"
                ),
                str(exc),
                parent=self,
            )
            return

        messagebox.showinfo(
            "Abgangsbuchung",
            (
                "Die Abgangsbuchung wurde "
                "dem Anlagegut zugeordnet."
            ),
            parent=self,
        )

        self._refresh_fixed_assets()

    def _return_to_start(self) -> None:
        """Schließt die aktuelle Buchhaltung und kehrt zur Auswahl zurück."""

        confirmed = messagebox.askyesno(
            "Buchhaltung wechseln",
            (
                "Möchten Sie die aktuelle Buchhaltung schließen "
                "und zur Buchhaltungsauswahl zurückkehren?"
            ),
            parent=self,
        )

        if not confirmed:
            return

        self._return_to_start_requested = True
        self.destroy()

    def _create_reports_tab(self) -> None:
        """Erzeugt den Arbeitsbereich Auswertungen."""

        self._reports_notebook = ttk.Notebook(self._reports_tab)
        self._reports_notebook.pack(
            fill="both",
            expand=True,
        )

        self._trial_balance_report_tab = ttk.Frame(
            self._reports_notebook,
            padding=12,
        )

        self._account_statement_report_tab = ttk.Frame(
            self._reports_notebook,
            padding=12,
        )

        self._journal_report_tab = ttk.Frame(
            self._reports_notebook,
            padding=12,
        )

        self._reports_notebook.add(
            self._trial_balance_report_tab,
            text="Summen- und Saldenliste",
        )

        self._reports_notebook.add(
            self._account_statement_report_tab,
            text="Kontenauswertung",
        )

        self._reports_notebook.add(
            self._journal_report_tab,
            text="Journal",
        )

        self._create_trial_balance_report()
        self._create_account_statement_report()
        self._create_journal_report()

    def _normalize_report_date(
        self,
        variable: tk.StringVar,
    ) -> None:
        """Normalisiert ein Datum im Auswertungsfilter."""

        value = variable.get().strip()

        if not value:
            return

        try:
            normalized = normalize_german_date(value)
        except ValueError:
            return

        variable.set(normalized)

    def _refresh_trial_balance_report(self) -> None:
        """Aktualisiert die Summen- und Saldenliste."""

        try:
            start_date = parse_german_date(self._trial_balance_start_date_var.get())
            end_date = parse_german_date(self._trial_balance_end_date_var.get())

            report = self._workspace.build_trial_balance_report(
                start_date=start_date,
                end_date=end_date,
                opening_balance_account_number=(
                    self._opening_balance_account_number
                ),
            )

        except ValueError as exc:
            messagebox.showerror(
                "Summen- und Saldenliste",
                str(exc),
                parent=self,
            )
            return

        self._current_trial_balance_report = report

        self._trial_balance_start_date_var.set(start_date.strftime("%d.%m.%Y"))
        self._trial_balance_end_date_var.set(end_date.strftime("%d.%m.%Y"))

        for item in self._trial_balance_table.get_children():
            self._trial_balance_table.delete(item)

        account_names = {account.number: account.name for account in self._accounts}

        for row in report.rows:
            self._trial_balance_table.insert(
                "",
                "end",
                values=(
                    row.account_number,
                    account_names.get(
                        row.account_number,
                        "Unbekanntes Konto",
                    ),
                    f"{row.opening_debit:.2f}",
                    f"{row.opening_credit:.2f}",
                    f"{row.debit_turnover:.2f}",
                    f"{row.credit_turnover:.2f}",
                    f"{row.closing_debit:.2f}",
                    f"{row.closing_credit:.2f}",
                ),
            )

        self._trial_balance_totals_var.set(
            (
                "Summen: "
                f"Anfang Soll {report.opening_debit_total:.2f} · "
                f"Anfang Haben {report.opening_credit_total:.2f} · "
                f"Soll-Umsatz {report.debit_turnover_total:.2f} · "
                f"Haben-Umsatz {report.credit_turnover_total:.2f} · "
                f"Endsaldo Soll {report.closing_debit_total:.2f} · "
                f"Endsaldo Haben {report.closing_credit_total:.2f}"
            )
        )

    def _create_trial_balance_report(self) -> None:
        """Erzeugt die Summen- und Saldenliste."""

        ttk.Label(
            self._trial_balance_report_tab,
            text="Summen- und Saldenliste",
            font=("TkDefaultFont", 16, "bold"),
        ).pack(
            anchor="w",
        )

        ttk.Label(
            self._trial_balance_report_tab,
            text=("Auswertung der Kontenbewegungen vor Jahresabschlussbuchungen."),
        ).pack(
            anchor="w",
            pady=(4, 12),
        )

        filter_frame = ttk.Frame(self._trial_balance_report_tab)
        filter_frame.pack(
            fill="x",
            pady=(0, 12),
        )

        self._trial_balance_start_date_var = tk.StringVar(
            value=self._context.fiscal_year.start_date.strftime("%d.%m.%Y")
        )

        self._trial_balance_end_date_var = tk.StringVar(
            value=self._context.fiscal_year.end_date.strftime("%d.%m.%Y")
        )

        ttk.Label(
            filter_frame,
            text="Von",
        ).pack(
            side="left",
        )

        self._trial_balance_start_date_entry = ttk.Entry(
            filter_frame,
            textvariable=self._trial_balance_start_date_var,
            width=12,
        )
        self._trial_balance_start_date_entry.pack(
            side="left",
            padx=(6, 16),
        )

        self._trial_balance_start_date_entry.bind(
            "<FocusOut>",
            lambda _event: self._normalize_report_date(
                self._trial_balance_start_date_var
            ),
        )

        ttk.Label(
            filter_frame,
            text="Bis",
        ).pack(
            side="left",
        )

        self._trial_balance_end_date_entry = ttk.Entry(
            filter_frame,
            textvariable=self._trial_balance_end_date_var,
            width=12,
        )
        self._trial_balance_end_date_entry.pack(
            side="left",
            padx=(6, 16),
        )

        self._trial_balance_end_date_entry.bind(
            "<FocusOut>",
            lambda _event: self._normalize_report_date(
                self._trial_balance_end_date_var
            ),
        )

        ttk.Button(
            filter_frame,
            text="Aktualisieren",
            command=self._refresh_trial_balance_report,
        ).pack(
            side="left",
        )

        ttk.Button(
            filter_frame,
            text="PDF exportieren",
            command=self._export_trial_balance_pdf,
        ).pack(
            side="left",
            padx=(8, 0),
        )

        columns = (
            "account_number",
            "account_name",
            "opening_debit",
            "opening_credit",
            "debit_turnover",
            "credit_turnover",
            "closing_debit",
            "closing_credit",
        )

        table_frame = ttk.Frame(self._trial_balance_report_tab)
        table_frame.pack(
            fill="both",
            expand=True,
        )

        self._trial_balance_table = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            height=15,
        )

        headings = {
            "account_number": "Konto",
            "account_name": "Bezeichnung",
            "opening_debit": "Anfang Soll",
            "opening_credit": "Anfang Haben",
            "debit_turnover": "Soll-Umsatz",
            "credit_turnover": "Haben-Umsatz",
            "closing_debit": "Endsaldo Soll",
            "closing_credit": "Endsaldo Haben",
        }

        for column, heading in headings.items():
            self._trial_balance_table.heading(
                column,
                text=heading,
            )

        self._trial_balance_table.column(
            "account_number",
            width=80,
            anchor="w",
        )
        self._trial_balance_table.column(
            "account_name",
            width=240,
            anchor="w",
        )

        for column in (
            "opening_debit",
            "opening_credit",
            "debit_turnover",
            "credit_turnover",
            "closing_debit",
            "closing_credit",
        ):
            self._trial_balance_table.column(
                column,
                width=105,
                anchor="e",
            )

        scrollbar = ttk.Scrollbar(
            table_frame,
            orient="vertical",
            command=self._trial_balance_table.yview,
        )

        self._trial_balance_table.configure(yscrollcommand=scrollbar.set)

        self._trial_balance_table.pack(
            side="left",
            fill="both",
            expand=True,
        )

        scrollbar.pack(
            side="right",
            fill="y",
        )

        self._trial_balance_totals_var = tk.StringVar()

        ttk.Label(
            self._trial_balance_report_tab,
            textvariable=self._trial_balance_totals_var,
        ).pack(
            anchor="e",
            pady=(8, 0),
        )

    def _create_account_statement_report(self) -> None:
        """Erzeugt die gefilterte Kontenauswertung."""

        ttk.Label(
            self._account_statement_report_tab,
            text="Kontenauswertung",
            font=("TkDefaultFont", 16, "bold"),
        ).pack(
            anchor="w",
        )

        ttk.Label(
            self._account_statement_report_tab,
            text=("Kontenbewegungen mit Zeitraum- und Kontennummernfilter."),
        ).pack(
            anchor="w",
            pady=(4, 12),
        )

        filter_frame = ttk.Frame(self._account_statement_report_tab)
        filter_frame.pack(
            fill="x",
            pady=(0, 12),
        )

        self._account_statement_start_date_var = tk.StringVar(
            value=self._context.fiscal_year.start_date.strftime("%d.%m.%Y")
        )

        self._account_statement_end_date_var = tk.StringVar(
            value=self._context.fiscal_year.end_date.strftime("%d.%m.%Y")
        )

        self._account_statement_from_account_var = tk.StringVar()
        self._account_statement_to_account_var = tk.StringVar()

        ttk.Label(
            filter_frame,
            text="Von",
        ).pack(
            side="left",
        )

        start_entry = ttk.Entry(
            filter_frame,
            textvariable=self._account_statement_start_date_var,
            width=12,
        )
        start_entry.pack(
            side="left",
            padx=(6, 12),
        )

        start_entry.bind(
            "<FocusOut>",
            lambda _event: self._normalize_report_date(
                self._account_statement_start_date_var
            ),
        )

        ttk.Label(
            filter_frame,
            text="Bis",
        ).pack(
            side="left",
        )

        end_entry = ttk.Entry(
            filter_frame,
            textvariable=self._account_statement_end_date_var,
            width=12,
        )
        end_entry.pack(
            side="left",
            padx=(6, 12),
        )

        end_entry.bind(
            "<FocusOut>",
            lambda _event: self._normalize_report_date(
                self._account_statement_end_date_var
            ),
        )

        ttk.Label(
            filter_frame,
            text="Konto von",
        ).pack(
            side="left",
        )

        ttk.Entry(
            filter_frame,
            textvariable=self._account_statement_from_account_var,
            width=8,
        ).pack(
            side="left",
            padx=(6, 12),
        )

        ttk.Label(
            filter_frame,
            text="Konto bis",
        ).pack(
            side="left",
        )

        ttk.Entry(
            filter_frame,
            textvariable=self._account_statement_to_account_var,
            width=8,
        ).pack(
            side="left",
            padx=(6, 12),
        )

        ttk.Button(
            filter_frame,
            text="Aktualisieren",
            command=self._refresh_account_statement_report,
        ).pack(
            side="left",
        )

        ttk.Button(
            filter_frame,
            text="PDF exportieren",
            command=self._export_account_activity_pdf,
        ).pack(
            side="left",
            padx=(8, 0),
        )

        columns = (
            "booking_date",
            "voucher_no",
            "account_number",
            "account_name",
            "description",
            "debit",
            "credit",
            "balance",
        )

        table_frame = ttk.Frame(self._account_statement_report_tab)
        table_frame.pack(
            fill="both",
            expand=True,
        )

        self._account_statement_table = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            height=15,
        )

        headings = {
            "booking_date": "Datum",
            "voucher_no": "Beleg",
            "account_number": "Konto",
            "account_name": "Bezeichnung",
            "description": "Buchungstext",
            "debit": "Soll",
            "credit": "Haben",
            "balance": "Saldo",
        }

        for column, heading in headings.items():
            self._account_statement_table.heading(
                column,
                text=heading,
            )

        self._account_statement_table.column(
            "booking_date",
            width=95,
            anchor="w",
        )
        self._account_statement_table.column(
            "voucher_no",
            width=90,
            anchor="w",
        )
        self._account_statement_table.column(
            "account_number",
            width=75,
            anchor="w",
        )
        self._account_statement_table.column(
            "account_name",
            width=210,
            anchor="w",
        )
        self._account_statement_table.column(
            "description",
            width=280,
            anchor="w",
        )

        for column in (
            "debit",
            "credit",
            "balance",
        ):
            self._account_statement_table.column(
                column,
                width=110,
                anchor="e",
            )

        scrollbar = ttk.Scrollbar(
            table_frame,
            orient="vertical",
            command=self._account_statement_table.yview,
        )

        self._account_statement_table.configure(yscrollcommand=scrollbar.set)

        self._account_statement_table.pack(
            side="left",
            fill="both",
            expand=True,
        )

        scrollbar.pack(
            side="right",
            fill="y",
        )

    def _create_journal_report(self) -> None:
        """Erzeugt die gefilterte Journalauswertung."""

        ttk.Label(
            self._journal_report_tab,
            text="Journal",
            font=("TkDefaultFont", 16, "bold"),
        ).pack(
            anchor="w",
        )

        ttk.Label(
            self._journal_report_tab,
            text="Auswertung der Buchungen für einen gewählten Zeitraum.",
        ).pack(
            anchor="w",
            pady=(4, 12),
        )

        filter_frame = ttk.Frame(self._journal_report_tab)
        filter_frame.pack(
            fill="x",
            pady=(0, 12),
        )

        self._journal_report_start_date_var = tk.StringVar(
            value=self._context.fiscal_year.start_date.strftime("%d.%m.%Y")
        )

        self._journal_report_end_date_var = tk.StringVar(
            value=self._context.fiscal_year.end_date.strftime("%d.%m.%Y")
        )

        ttk.Label(
            filter_frame,
            text="Von",
        ).pack(
            side="left",
        )

        self._journal_report_start_date_entry = ttk.Entry(
            filter_frame,
            textvariable=self._journal_report_start_date_var,
            width=12,
        )
        self._journal_report_start_date_entry.pack(
            side="left",
            padx=(6, 16),
        )

        self._journal_report_start_date_entry.bind(
            "<FocusOut>",
            lambda _event: self._normalize_report_date(
                self._journal_report_start_date_var
            ),
        )

        ttk.Label(
            filter_frame,
            text="Bis",
        ).pack(
            side="left",
        )

        self._journal_report_end_date_entry = ttk.Entry(
            filter_frame,
            textvariable=self._journal_report_end_date_var,
            width=12,
        )
        self._journal_report_end_date_entry.pack(
            side="left",
            padx=(6, 16),
        )

        self._journal_report_end_date_entry.bind(
            "<FocusOut>",
            lambda _event: self._normalize_report_date(
                self._journal_report_end_date_var
            ),
        )

        ttk.Button(
            filter_frame,
            text="Aktualisieren",
            command=self._refresh_journal_report,
        ).pack(
            side="left",
        )

        ttk.Button(
            filter_frame,
            text="PDF exportieren",
            command=self._export_journal_pdf,
        ).pack(
            side="left",
            padx=(8, 0),
        )

        columns = (
            "booking_number",
            "booking_date",
            "voucher_no",
            "description",
            "account_number",
            "account_name",
            "side",
            "amount",
        )

        table_frame = ttk.Frame(self._journal_report_tab)
        table_frame.pack(
            fill="both",
            expand=True,
        )

        self._journal_report_table = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            height=15,
        )

        headings = {
            "booking_number": "Nr.",
            "booking_date": "Datum",
            "voucher_no": "Beleg",
            "description": "Buchungstext",
            "account_number": "Konto",
            "account_name": "Bezeichnung",
            "side": "S/H",
            "amount": "Betrag",
        }

        for column, heading in headings.items():
            self._journal_report_table.heading(
                column,
                text=heading,
            )

        self._journal_report_table.column(
            "booking_number",
            width=55,
            anchor="e",
        )

        self._journal_report_table.column(
            "booking_date",
            width=95,
            anchor="w",
        )
        self._journal_report_table.column(
            "voucher_no",
            width=90,
            anchor="w",
        )
        self._journal_report_table.column(
            "description",
            width=280,
            anchor="w",
        )
        self._journal_report_table.column(
            "account_number",
            width=75,
            anchor="w",
        )
        self._journal_report_table.column(
            "account_name",
            width=220,
            anchor="w",
        )
        self._journal_report_table.column(
            "side",
            width=55,
            anchor="center",
        )
        self._journal_report_table.column(
            "amount",
            width=110,
            anchor="e",
        )

        scrollbar = ttk.Scrollbar(
            table_frame,
            orient="vertical",
            command=self._journal_report_table.yview,
        )

        self._journal_report_table.configure(
            yscrollcommand=scrollbar.set
        )

        self._journal_report_table.pack(
            side="left",
            fill="both",
            expand=True,
        )

        scrollbar.pack(
            side="right",
            fill="y",
        )

    def _refresh_account_statement_report(self) -> None:
        """Aktualisiert die gefilterte Kontenauswertung."""

        try:
            start_date = parse_german_date(self._account_statement_start_date_var.get())
            end_date = parse_german_date(self._account_statement_end_date_var.get())

            from_account = self._account_statement_from_account_var.get().strip()
            to_account = self._account_statement_to_account_var.get().strip()

            if not from_account:
                raise ValueError("Bitte geben Sie mindestens 'Konto von' ein.")

            if not to_account:
                to_account = from_account
                self._account_statement_to_account_var.set(to_account)

            if not from_account.isdigit() or not to_account.isdigit():
                raise ValueError("Die Kontonummern müssen numerisch sein.")

            if int(to_account) < int(from_account):
                raise ValueError("'Konto bis' darf nicht kleiner als 'Konto von' sein.")

            account_numbers = tuple(
                account.number
                for account in self._accounts
                if (int(from_account) <= int(account.number) <= int(to_account))
            )

            statements = tuple(
                self._workspace.build_account_activity_report(
                    account_number=account_number,
                    start_date=start_date,
                    end_date=end_date,
                )
                for account_number in account_numbers
            )

        except ValueError as exc:
            messagebox.showerror(
                "Kontenauswertung",
                str(exc),
                parent=self,
            )
            return

        self._current_account_activity_reports = statements
        self._current_account_activity_start_date = start_date
        self._current_account_activity_end_date = end_date

        self._account_statement_start_date_var.set(start_date.strftime("%d.%m.%Y"))
        self._account_statement_end_date_var.set(end_date.strftime("%d.%m.%Y"))

        for item in self._account_statement_table.get_children():
            self._account_statement_table.delete(item)

        account_names = {account.number: account.name for account in self._accounts}

        for statement in statements:
            account_name = account_names.get(
                statement.account_number,
                "Unbekanntes Konto",
            )

            for line in statement.lines:
                self._account_statement_table.insert(
                    "",
                    "end",
                    values=(
                        line.booking_date.strftime("%d.%m.%Y"),
                        line.voucher_no,
                        statement.account_number,
                        account_name,
                        line.description,
                        f"{line.debit:.2f}",
                        f"{line.credit:.2f}",
                        f"{line.running_balance:.2f}",
                    ),
                )

    def _select_pdf_target(
        self,
        *,
        title: str,
        initialfile: str,
    ) -> Path | None:
        """Wählt eine Zieldatei für einen PDF-Bericht."""

        filename = filedialog.asksaveasfilename(
            parent=self,
            title=title,
            initialfile=initialfile,
            defaultextension=".pdf",
            filetypes=(
                ("PDF-Dateien", "*.pdf"),
                ("Alle Dateien", "*.*"),
            ),
        )

        if not filename:
            return None

        return Path(filename)

    def _export_balance_sheet_pdf(self) -> None:
        """Exportiert die aktuelle Bilanz als PDF."""

        if self._current_balance_sheet is None:
            messagebox.showwarning(
                "Bilanz",
                "Es steht keine Bilanz für den PDF-Export zur Verfügung.",
                parent=self,
            )
            return

        target = self._select_pdf_target(
            title="Bilanz als PDF exportieren",
            initialfile="Bilanz.pdf",
        )

        if target is None:
            return

        try:
            exported_path = self._pdf_reporting_service.export_balance_sheet(
                balance_sheet=self._current_balance_sheet,
                company_name=self._context.company.name,
                fiscal_year_name=self._context.fiscal_year.display_name,
                target=target,
            )
        except OSError as exc:
            messagebox.showerror(
                "Bilanz konnte nicht exportiert werden",
                str(exc),
                parent=self,
            )
            return

        messagebox.showinfo(
            "Bilanz",
            f"PDF erfolgreich exportiert.\n\n{exported_path}",
            parent=self,
        )

    def _export_income_statement_pdf(self) -> None:
        """Exportiert die aktuelle GuV als PDF."""

        if (
            self._current_income_statement is None
            or self._current_closing_result is None
        ):
            messagebox.showwarning(
                "Gewinn- und Verlustrechnung",
                "Es steht keine GuV für den PDF-Export zur Verfügung.",
                parent=self,
            )
            return

        target = self._select_pdf_target(
            title="GuV als PDF exportieren",
            initialfile="GuV.pdf",
        )

        if target is None:
            return

        try:
            exported_path = (
                self._pdf_reporting_service.export_income_statement(
                    income_statement=self._current_income_statement,
                    net_income=self._current_closing_result.net_income,
                    company_name=self._context.company.name,
                    fiscal_year_name=self._context.fiscal_year.display_name,
                    target=target,
                )
            )
        except OSError as exc:
            messagebox.showerror(
                "GuV konnte nicht exportiert werden",
                str(exc),
                parent=self,
            )
            return

        messagebox.showinfo(
            "Gewinn- und Verlustrechnung",
            f"PDF erfolgreich exportiert.\n\n{exported_path}",
            parent=self,
        )

    def _export_trial_balance_pdf(self) -> None:
        """Exportiert die aktuelle Summen- und Saldenliste als PDF."""

        report = self._current_trial_balance_report

        if report is None:
            messagebox.showwarning(
                "Summen- und Saldenliste",
                "Bitte aktualisieren Sie zuerst die Auswertung.",
                parent=self,
            )
            return

        target = self._select_pdf_target(
            title="Summen- und Saldenliste als PDF exportieren",
            initialfile="Summen-und-Saldenliste.pdf",
        )

        if target is None:
            return

        account_names = {
            account.number: account.name
            for account in self._accounts
        }

        try:
            exported_path = self._pdf_reporting_service.export_trial_balance(
                report=report,
                account_names=account_names,
                company_name=self._context.company.name,
                target=target,
            )
        except OSError as exc:
            messagebox.showerror(
                "Summen- und Saldenliste konnte nicht exportiert werden",
                str(exc),
                parent=self,
            )
            return

        messagebox.showinfo(
            "Summen- und Saldenliste",
            f"PDF erfolgreich exportiert.\n\n{exported_path}",
            parent=self,
        )

    def _export_account_activity_pdf(self) -> None:
        """Exportiert die aktuelle Kontenauswertung als PDF."""

        if (
            self._current_account_activity_start_date is None
            or self._current_account_activity_end_date is None
        ):
            messagebox.showwarning(
                "Kontenauswertung",
                "Bitte aktualisieren Sie zuerst die Auswertung.",
                parent=self,
            )
            return

        target = self._select_pdf_target(
            title="Kontenauswertung als PDF exportieren",
            initialfile="Kontenauswertung.pdf",
        )

        if target is None:
            return

        account_names = {
            account.number: account.name
            for account in self._accounts
        }

        try:
            exported_path = self._pdf_reporting_service.export_account_activity(
                reports=self._current_account_activity_reports,
                account_names=account_names,
                company_name=self._context.company.name,
                start_date=self._current_account_activity_start_date,
                end_date=self._current_account_activity_end_date,
                target=target,
            )
        except OSError as exc:
            messagebox.showerror(
                "Kontenauswertung konnte nicht exportiert werden",
                str(exc),
                parent=self,
            )
            return

        messagebox.showinfo(
            "Kontenauswertung",
            f"PDF erfolgreich exportiert.\n\n{exported_path}",
            parent=self,
        )

    def _refresh_journal_report(self) -> None:
        """Aktualisiert die gefilterte Journalauswertung."""

        try:
            start_date = parse_german_date(
                self._journal_report_start_date_var.get()
            )
            end_date = parse_german_date(
                self._journal_report_end_date_var.get()
            )

            report = self._workspace.build_journal_report(
                start_date=start_date,
                end_date=end_date,
            )

        except ValueError as exc:
            messagebox.showerror(
                "Journal",
                str(exc),
                parent=self,
            )
            return

        self._current_journal_report = report

        self._journal_report_start_date_var.set(
            start_date.strftime("%d.%m.%Y")
        )
        self._journal_report_end_date_var.set(
            end_date.strftime("%d.%m.%Y")
        )

        for item in self._journal_report_table.get_children():
            self._journal_report_table.delete(item)

        account_names = {
            account.number: account.name
            for account in self._accounts
        }

        for line in report.lines:
            self._journal_report_table.insert(
                "",
                "end",
                values=(
                    line.booking_number,
                    line.booking_date.strftime("%d.%m.%Y"),
                    line.voucher_no,
                    line.description,
                    line.account_number,
                    account_names.get(
                        line.account_number,
                        "Unbekanntes Konto",
                    ),
                    (
                        "S"
                        if line.side is EntrySide.DEBIT
                        else "H"
                    ),
                    f"{line.amount:.2f}",
                ),
            )

    def _export_journal_pdf(self) -> None:
        """Exportiert die aktuelle Journalauswertung als PDF."""

        report = self._current_journal_report

        if report is None:
            messagebox.showwarning(
                "Journal",
                "Bitte aktualisieren Sie zuerst die Auswertung.",
                parent=self,
            )
            return

        target = self._select_pdf_target(
            title="Journal als PDF exportieren",
            initialfile="Journal.pdf",
        )

        if target is None:
            return

        account_names = {
            account.number: account.name
            for account in self._accounts
        }

        try:
            exported_path = self._pdf_reporting_service.export_journal(
                report=report,
                account_names=account_names,
                company_name=self._context.company.name,
                target=target,
            )
        except OSError as exc:
            messagebox.showerror(
                "Journal konnte nicht exportiert werden",
                str(exc),
                parent=self,
            )
            return

        messagebox.showinfo(
            "Journal",
            f"PDF erfolgreich exportiert.\n\n{exported_path}",
            parent=self,
        )

"""Eingabemaske für Umsatzsteuerbuchungen."""

import tkinter as tk
from collections.abc import Callable
from datetime import date
from decimal import Decimal, InvalidOperation
from tkinter import ttk

from openbilanz.domain.account import Account
from openbilanz.domain.account_type import AccountType
from openbilanz.domain.booking import Booking
from openbilanz.domain.vat_accounts import VatAccounts
from openbilanz.domain.vat_booking_item import VatBookingItem
from openbilanz.domain.vat_configuration import (
    VatConfiguration,
)
from openbilanz.services.vat_booking_service import (
    VatBookingService,
)
from openbilanz.ui.date_input import (
    normalize_german_date,
    parse_german_date,
)

_INPUT_INVOICE = "Eingangsrechnung"
_OUTPUT_INVOICE = "Ausgangsrechnung"
_CUSTOMER_CREDIT_NOTE = "Kundengutschrift"
_SUPPLIER_CREDIT_NOTE = "Lieferantengutschrift"

_TAX_RATES = ("0 %", "7 %", "19 %")


class VatBookingFrame(ttk.Frame):
    """Erfasst Eingangs- und Ausgangsrechnungen mit Umsatzsteuer."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        accounts: tuple[Account, ...],
        vat_accounts: VatAccounts,
        vat_configuration: VatConfiguration,
        on_booking_created: Callable[[Booking], None],
    ) -> None:
        super().__init__(parent)

        self._accounts = accounts
        self._vat_accounts = vat_accounts
        self._vat_configuration = vat_configuration
        self._on_booking_created = on_booking_created
        self._vat_booking_service = VatBookingService()
        self._enabled = True

        self._accounts_by_display_name = {
            self._account_display_name(account): account
            for account in accounts
        }

        self._accounts_by_number = {
            account.number: account
            for account in accounts
        }

        self._account_display_names = tuple(
            self._accounts_by_display_name
        )

        self._position_rows: list[dict[str, object]] = []

        self._create_ui()

    def _create_ui(self) -> None:
        """Erzeugt die Rechnungserfassung."""

        self.columnconfigure(
            1,
            weight=1,
        )

        self._invoice_type_var = tk.StringVar(
            value=_INPUT_INVOICE
        )
        self._booking_date_var = tk.StringVar(
            value=date.today().strftime("%d.%m.%Y")
        )
        self._voucher_no_var = tk.StringVar()
        self._booking_description_var = tk.StringVar()
        self._counter_account_var = tk.StringVar()
        self._status_var = tk.StringVar()

        ttk.Label(
            self,
            text="Rechnungsart",
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=(0, 12),
            pady=6,
        )

        self._invoice_type_box = ttk.Combobox(
            self,
            textvariable=self._invoice_type_var,
            values=(
                _INPUT_INVOICE,
                _OUTPUT_INVOICE,
                _CUSTOMER_CREDIT_NOTE,
                _SUPPLIER_CREDIT_NOTE,
            ),
            state="readonly",
            width=24,
        )
        self._invoice_type_box.grid(
            row=0,
            column=1,
            sticky="w",
            pady=6,
        )

        ttk.Label(
            self,
            text="Datum",
        ).grid(
            row=1,
            column=0,
            sticky="w",
            padx=(0, 12),
            pady=6,
        )

        self._booking_date_entry = ttk.Entry(
            self,
            textvariable=self._booking_date_var,
            width=16,
        )
        self._booking_date_entry.grid(
            row=1,
            column=1,
            sticky="w",
            pady=6,
        )
        self._booking_date_entry.bind(
            "<FocusOut>",
            self._normalize_booking_date,
        )

        ttk.Label(
            self,
            text="Belegnummer",
        ).grid(
            row=2,
            column=0,
            sticky="w",
            padx=(0, 12),
            pady=6,
        )

        self._voucher_no_entry = ttk.Entry(
            self,
            textvariable=self._voucher_no_var,
            width=24,
        )
        self._voucher_no_entry.grid(
            row=2,
            column=1,
            sticky="w",
            pady=6,
        )

        ttk.Label(
            self,
            text="Buchungstext",
        ).grid(
            row=3,
            column=0,
            sticky="w",
            padx=(0, 12),
            pady=6,
        )

        self._description_entry = ttk.Entry(
            self,
            textvariable=self._booking_description_var,
        )
        self._description_entry.grid(
            row=3,
            column=1,
            sticky="ew",
            pady=6,
        )

        ttk.Label(
            self,
            text="Gegenkonto",
        ).grid(
            row=4,
            column=0,
            sticky="w",
            padx=(0, 12),
            pady=6,
        )

        self._counter_account_box = ttk.Combobox(
            self,
            textvariable=self._counter_account_var,
            values=self._account_display_names,
        )
        self._counter_account_box.grid(
            row=4,
            column=1,
            sticky="ew",
            pady=6,
        )

        ttk.Separator(
            self,
            orient="horizontal",
        ).grid(
            row=5,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=(14, 12),
        )

        ttk.Label(
            self,
            text="Rechnungspositionen",
            font=("TkDefaultFont", 11, "bold"),
        ).grid(
            row=6,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(0, 8),
        )

        self._positions_frame = ttk.Frame(
            self
        )
        self._positions_frame.grid(
            row=7,
            column=0,
            columnspan=2,
            sticky="ew",
        )

        self._positions_frame.columnconfigure(
            0,
            weight=1,
        )

        ttk.Label(
            self._positions_frame,
            text="Sachkonto",
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=(0, 8),
        )

        ttk.Label(
            self._positions_frame,
            text="Brutto",
        ).grid(
            row=0,
            column=1,
            sticky="e",
            padx=(0, 8),
        )

        ttk.Label(
            self._positions_frame,
            text="USt",
        ).grid(
            row=0,
            column=2,
            sticky="w",
        )

        self._add_position_row()

        button_frame = ttk.Frame(
            self
        )
        button_frame.grid(
            row=8,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=(10, 0),
        )

        self._add_position_button = ttk.Button(
            button_frame,
            text="Position hinzufügen",
            command=self._add_position_row,
        )
        self._add_position_button.pack(
            side="left",
        )

        self._remove_position_button = ttk.Button(
            button_frame,
            text="Letzte Position entfernen",
            command=self._remove_position_row,
        )
        self._remove_position_button.pack(
            side="left",
            padx=(8, 0),
        )

        self._booking_button = ttk.Button(
            button_frame,
            text="Buchung übernehmen",
            command=self._create_booking,
        )
        self._booking_button.pack(
            side="right",
        )
        self._booking_button.state(
            ["disabled"]
        )

        ttk.Label(
            self,
            textvariable=self._status_var,
        ).grid(
            row=9,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(10, 0),
        )

        for variable in (
            self._invoice_type_var,
            self._booking_date_var,
            self._booking_description_var,
            self._counter_account_var,
        ):
            variable.trace_add(
                "write",
                self._on_form_changed,
            )

        self._update_remove_button()

    def _add_position_row(self) -> None:
        """Fügt eine Rechnungsposition hinzu."""

        account_var = tk.StringVar()
        amount_var = tk.StringVar()
        tax_rate_var = tk.StringVar(
            value="19 %"
        )

        row_index = len(self._position_rows) + 1

        account_box = ttk.Combobox(
            self._positions_frame,
            textvariable=account_var,
            values=self._account_display_names,
        )
        account_box.grid(
            row=row_index,
            column=0,
            sticky="ew",
            padx=(0, 8),
            pady=4,
        )

        amount_entry = ttk.Entry(
            self._positions_frame,
            textvariable=amount_var,
            justify="right",
            width=14,
        )
        amount_entry.grid(
            row=row_index,
            column=1,
            sticky="e",
            padx=(0, 8),
            pady=4,
        )

        tax_rate_box = ttk.Combobox(
            self._positions_frame,
            textvariable=tax_rate_var,
            values=_TAX_RATES,
            state="readonly",
            width=8,
        )
        tax_rate_box.grid(
            row=row_index,
            column=2,
            sticky="w",
            pady=4,
        )

        self._position_rows.append(
            {
                "account_var": account_var,
                "amount_var": amount_var,
                "tax_rate_var": tax_rate_var,
                "account_box": account_box,
                "amount_entry": amount_entry,
                "tax_rate_box": tax_rate_box,
            }
        )

        for variable in (
            account_var,
            amount_var,
            tax_rate_var,
        ):
            variable.trace_add(
                "write",
                self._on_form_changed,
            )

        self._update_remove_button()

        if hasattr(
            self,
            "_booking_button",
        ):
            self._on_form_changed()

    def _remove_position_row(self) -> None:
        """Entfernt die letzte Rechnungsposition."""

        if len(self._position_rows) <= 1:
            return

        row = self._position_rows.pop()

        for widget_name in (
            "account_box",
            "amount_entry",
            "tax_rate_box",
        ):
            widget = row[widget_name]

            if isinstance(widget, tk.Widget):
                widget.destroy()

        self._update_remove_button()
        self._on_form_changed()

    def _update_remove_button(self) -> None:
        """Aktualisiert den Entfernen-Schalter."""

        if not hasattr(
            self,
            "_remove_position_button",
        ):
            return

        if (
            self._enabled
            and len(self._position_rows) > 1
        ):
            self._remove_position_button.state(
                ["!disabled"]
            )
        else:
            self._remove_position_button.state(
                ["disabled"]
            )

    def set_enabled(
        self,
        enabled: bool,
    ) -> None:
        """Aktiviert oder sperrt die Rechnungserfassung."""

        self._enabled = enabled

        entry_state = (
            "normal"
            if enabled
            else "disabled"
        )

        self._booking_date_entry.configure(
            state=entry_state
        )
        self._voucher_no_entry.configure(
            state=entry_state
        )
        self._description_entry.configure(
            state=entry_state
        )
        self._counter_account_box.configure(
            state=entry_state
        )

        if hasattr(
            self,
            "_invoice_type_box",
        ):
            self._invoice_type_box.configure(
                state=(
                    "readonly"
                    if enabled
                    else "disabled"
                )
            )

        for row in getattr(
            self,
            "_position_rows",
            (),
        ):
            row["account_box"].configure(
                state=entry_state
            )
            row["amount_entry"].configure(
                state=entry_state
            )
            row["tax_rate_box"].configure(
                state=(
                    "readonly"
                    if enabled
                    else "disabled"
                )
            )

        if hasattr(
            self,
            "_add_position_button",
        ):
            self._add_position_button.configure(
                state=entry_state
            )

        self._update_remove_button()

        if enabled:
            self._on_form_changed()
        else:
            self._booking_button.state(
                ["disabled"]
            )

            self._status_var.set(
                "Das Geschäftsjahr ist abgeschlossen. "
                "Buchungen sind nicht mehr möglich."
            )

    def _on_form_changed(
        self,
        *_args: object,
    ) -> None:
        """Prüft die Vollständigkeit der Rechnungserfassung."""

        if not self._enabled:
            self._booking_button.state(
                ["disabled"]
            )
            return

        valid = True

        try:
            self._parse_booking_date(
                self._booking_date_var.get()
            )
        except ValueError:
            valid = False

        if not self._booking_description_var.get().strip():
            valid = False

        counter_account = self._resolve_account(
            self._counter_account_var.get()
        )

        if counter_account is None:
            valid = False

        for row in self._position_rows:
            account = self._resolve_account(
                row["account_var"].get()
            )

            if account is None:
                valid = False

            invoice_type = self._invoice_type_var.get()

            if account is not None:
                if invoice_type in (
                    _OUTPUT_INVOICE,
                    _CUSTOMER_CREDIT_NOTE,
                ):
                    if account.account_type is not AccountType.REVENUE:
                        valid = False

                if invoice_type in (
                    _INPUT_INVOICE,
                    _SUPPLIER_CREDIT_NOTE,
                ):
                    if account.account_type is not AccountType.EXPENSE:
                        valid = False
            try:
                self._parse_amount(
                    row["amount_var"].get()
                )
            except ValueError:
                valid = False

            try:
                self._parse_tax_rate(
                    row["tax_rate_var"].get()
                )
            except ValueError:
                valid = False

            if (
                counter_account is not None
                and account is not None
                and counter_account.number
                == account.number
            ):
                valid = False

        if valid:
            self._booking_button.state(
                ["!disabled"]
            )
        else:
            self._booking_button.state(
                ["disabled"]
            )

        self._status_var.set("")

    def _create_booking(self) -> None:
        """Erzeugt die Buchung aus der Rechnung."""

        if not self._enabled:
            return

        counter_account = self._resolve_account(
            self._counter_account_var.get()
        )

        if counter_account is None:
            return

        try:
            booking_date = self._parse_booking_date(
                self._booking_date_var.get()
            )

            items = tuple(
                VatBookingItem(
                    account_number=account.number,
                    gross_amount=self._parse_amount(
                        row["amount_var"].get()
                    ),
                    tax_rate=self._parse_tax_rate(
                        row["tax_rate_var"].get()
                    ),
                )
                for row in self._position_rows
                if (
                    account := self._resolve_account(
                        row["account_var"].get()
                    )
                )
                is not None
            )
        except ValueError:
            return

        if len(items) != len(
            self._position_rows
        ):
            return

        voucher_no = (
            self._voucher_no_var.get().strip()
            or None
        )

        description = (
            self._booking_description_var.get().strip()
            or None
        )

        invoice_type = self._invoice_type_var.get()

        if invoice_type == _INPUT_INVOICE:
            booking = (
                self._vat_booking_service
                .build_input_booking(
                    booking_date=booking_date,
                    counter_account_number=(
                        counter_account.number
                    ),
                    items=items,
                    vat_accounts=self._vat_accounts,
                    vat_configuration=self._vat_configuration,
                    voucher_no=voucher_no,
                    description=description,
                )
            )

        elif invoice_type == _OUTPUT_INVOICE:
            booking = (
                self._vat_booking_service
                .build_output_booking(
                    booking_date=booking_date,
                    counter_account_number=(
                        counter_account.number
                    ),
                    items=items,
                    vat_accounts=self._vat_accounts,
                    vat_configuration=self._vat_configuration,
                    voucher_no=voucher_no,
                    description=description,
                )
            )

        elif invoice_type == _CUSTOMER_CREDIT_NOTE:
            booking = (
                self._vat_booking_service
                .build_customer_credit_note(
                    booking_date=booking_date,
                    counter_account_number=(
                        counter_account.number
                    ),
                    items=items,
                    vat_accounts=self._vat_accounts,
                    vat_configuration=self._vat_configuration,
                    voucher_no=voucher_no,
                    description=description,
                )
            )

        elif invoice_type == _SUPPLIER_CREDIT_NOTE:
            booking = (
                self._vat_booking_service
                .build_supplier_credit_note(
                    booking_date=booking_date,
                    counter_account_number=(
                        counter_account.number
                    ),
                    items=items,
                    vat_accounts=self._vat_accounts,
                    vat_configuration=self._vat_configuration,
                    voucher_no=voucher_no,
                    description=description,
                )
            )

        else:
            return

        self._on_booking_created(
            booking
        )

        self._clear()

        self._status_var.set(
            "Buchung wurde übernommen."
        )

    def _clear(self) -> None:
        """Leert die Rechnungspositionen nach der Buchung."""

        self._voucher_no_var.set("")
        self._booking_description_var.set("")
        self._counter_account_var.set("")

        while len(self._position_rows) > 1:
            self._remove_position_row()

        row = self._position_rows[0]

        row["account_var"].set("")
        row["amount_var"].set("")
        row["tax_rate_var"].set("19 %")

    def _resolve_account(
        self,
        value: str,
    ) -> Account | None:
        """Ermittelt das ausgewählte Konto."""

        normalized = value.strip()

        if not normalized:
            return None

        direct_match = (
            self._accounts_by_display_name.get(
                normalized
            )
        )

        if direct_match is not None:
            return direct_match

        return self._accounts_by_number.get(
            normalized
        )

    @staticmethod
    def _account_display_name(
        account: Account,
    ) -> str:
        """Liefert die Anzeige eines Kontos."""

        return str(account)

    @staticmethod
    def _parse_booking_date(
        value: str,
    ) -> date:
        """Liest ein deutsches Buchungsdatum."""

        return parse_german_date(
            value
        )

    @staticmethod
    def _parse_amount(
        value: str,
    ) -> Decimal:
        """Liest einen positiven Bruttobetrag."""

        normalized = (
            value.strip()
            .replace(".", "")
            .replace(",", ".")
        )

        try:
            amount = Decimal(
                normalized
            )
        except InvalidOperation as exc:
            raise ValueError(
                "Ungültiger Betrag."
            ) from exc

        if amount <= Decimal("0"):
            raise ValueError(
                "Der Betrag muss größer als 0 sein."
            )

        return amount

    @staticmethod
    def _parse_tax_rate(
        value: str,
    ) -> int:
        """Liest einen unterstützten Umsatzsteuersatz."""

        normalized = (
            value.strip()
            .removesuffix("%")
            .strip()
        )

        try:
            tax_rate = int(
                normalized
            )
        except ValueError as exc:
            raise ValueError(
                "Ungültiger Umsatzsteuersatz."
            ) from exc

        if tax_rate not in (0, 7, 19):
            raise ValueError(
                "Der Umsatzsteuersatz muss "
                "0, 7 oder 19 Prozent betragen."
            )

        return tax_rate

    def _normalize_booking_date(
        self,
        _event: tk.Event | None = None,
    ) -> None:
        """Normalisiert das Buchungsdatum."""

        try:
            normalized = (
                normalize_german_date(
                    self._booking_date_var.get()
                )
            )
        except ValueError:
            return

        self._booking_date_var.set(
            normalized
        )

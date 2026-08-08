"""Eingabemaske für laufende Buchungen."""

import tkinter as tk
from collections.abc import Callable
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from tkinter import ttk

from openbilanz.domain.account import Account
from openbilanz.domain.booking import Booking
from openbilanz.domain.booking_line import BookingLine
from openbilanz.domain.entry_side import EntrySide
from openbilanz.domain.money import ZERO


class BookingFrame(ttk.Frame):
    """Erfasst eine einfache laufende Buchung."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        accounts: tuple[Account, ...],
        on_booking_created: Callable[[Booking], None],
    ) -> None:
        super().__init__(parent)

        self._accounts = accounts
        self._on_booking_created = on_booking_created

        self._accounts_by_display_name = {
            self._account_display_name(account): account
            for account in accounts
        }

        self._account_display_names = tuple(
            self._accounts_by_display_name
        )

        self._create_ui()

    def _create_ui(self) -> None:
        """Erzeugt die Buchungsmaske."""

        self.columnconfigure(
            1,
            weight=1,
        )

        self._booking_date_var = tk.StringVar(
            value=date.today().strftime("%d.%m.%Y")
        )
        self._voucher_no_var = tk.StringVar()
        self._booking_description_var = tk.StringVar()
        self._debit_account_var = tk.StringVar()
        self._credit_account_var = tk.StringVar()
        self._booking_amount_var = tk.StringVar()
        self._status_var = tk.StringVar()

        ttk.Label(
            self,
            text="Datum",
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=(0, 12),
            pady=6,
        )

        ttk.Entry(
            self,
            textvariable=self._booking_date_var,
            width=16,
        ).grid(
            row=0,
            column=1,
            sticky="w",
            pady=6,
        )

        ttk.Label(
            self,
            text="Belegnummer",
        ).grid(
            row=1,
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
            row=1,
            column=1,
            sticky="w",
            pady=6,
        )

        ttk.Label(
            self,
            text="Buchungstext",
        ).grid(
            row=2,
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
            row=2,
            column=1,
            sticky="ew",
            pady=6,
        )

        ttk.Label(
            self,
            text="Sollkonto",
        ).grid(
            row=3,
            column=0,
            sticky="w",
            padx=(0, 12),
            pady=6,
        )

        self._debit_account_box = ttk.Combobox(
            self,
            textvariable=self._debit_account_var,
            values=self._account_display_names,
        )
        self._debit_account_box.grid(
            row=3,
            column=1,
            sticky="ew",
            pady=6,
        )

        ttk.Label(
            self,
            text="Habenkonto",
        ).grid(
            row=4,
            column=0,
            sticky="w",
            padx=(0, 12),
            pady=6,
        )

        self._credit_account_box = ttk.Combobox(
            self,
            textvariable=self._credit_account_var,
            values=self._account_display_names,
        )
        self._credit_account_box.grid(
            row=4,
            column=1,
            sticky="ew",
            pady=6,
        )

        ttk.Label(
            self,
            text="Betrag",
        ).grid(
            row=5,
            column=0,
            sticky="w",
            padx=(0, 12),
            pady=6,
        )

        self._amount_entry = ttk.Entry(
            self,
            textvariable=self._booking_amount_var,
            justify="right",
            width=18,
        )
        self._amount_entry.grid(
            row=5,
            column=1,
            sticky="w",
            pady=6,
        )

        self._booking_button = ttk.Button(
            self,
            text="Buchung übernehmen",
            command=self._create_booking,
        )
        self._booking_button.grid(
            row=6,
            column=1,
            sticky="e",
            pady=(18, 6),
        )
        self._booking_button.state(
            ["disabled"]
        )

        ttk.Label(
            self,
            textvariable=self._status_var,
        ).grid(
            row=7,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(10, 0),
        )

        self._debit_account_box.bind(
            "<KeyRelease>",
            self._filter_debit_accounts,
        )
        self._credit_account_box.bind(
            "<KeyRelease>",
            self._filter_credit_accounts,
        )

        variables = (
            self._booking_date_var,
            self._voucher_no_var,
            self._booking_description_var,
            self._debit_account_var,
            self._credit_account_var,
            self._booking_amount_var,
        )

        for variable in variables:
            variable.trace_add(
                "write",
                self._on_form_changed,
            )

    def _filter_debit_accounts(
        self,
        _event: tk.Event,
    ) -> None:
        """Filtert die Sollkonten während der Eingabe."""

        self._filter_account_box(
            self._debit_account_box,
            self._debit_account_var.get(),
        )

    def _filter_credit_accounts(
        self,
        _event: tk.Event,
    ) -> None:
        """Filtert die Habenkonten während der Eingabe."""

        self._filter_account_box(
            self._credit_account_box,
            self._credit_account_var.get(),
        )

    def _filter_account_box(
        self,
        box: ttk.Combobox,
        search_text: str,
    ) -> None:
        """Filtert eine Konten-Combobox."""

        search_value = search_text.strip().casefold()

        if not search_value:
            matches = self._account_display_names
        else:
            matches = tuple(
                display_name
                for display_name in self._account_display_names
                if search_value in display_name.casefold()
            )

        box.configure(
            values=matches,
        )

    def _on_form_changed(
        self,
        *_args: object,
    ) -> None:
        """Prüft die Vollständigkeit der Buchungsmaske."""

        debit_account = self._resolve_account(
            self._debit_account_var.get()
        )
        credit_account = self._resolve_account(
            self._credit_account_var.get()
        )

        valid = True

        try:
            self._parse_booking_date(
                self._booking_date_var.get()
            )
            self._parse_amount(
                self._booking_amount_var.get()
            )
        except ValueError:
            valid = False

        if not self._booking_description_var.get().strip():
            valid = False

        if debit_account is None:
            valid = False

        if credit_account is None:
            valid = False

        if (
            debit_account is not None
            and credit_account is not None
            and debit_account.number == credit_account.number
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
        """Erzeugt die Buchung aus den Eingaben."""

        debit_account = self._resolve_account(
            self._debit_account_var.get()
        )
        credit_account = self._resolve_account(
            self._credit_account_var.get()
        )

        if (
            debit_account is None
            or credit_account is None
        ):
            return

        try:
            booking_date = self._parse_booking_date(
                self._booking_date_var.get()
            )
            amount = self._parse_amount(
                self._booking_amount_var.get()
            )
        except ValueError:
            return

        voucher_no = (
            self._voucher_no_var.get().strip()
            or None
        )

        description = (
            self._booking_description_var.get().strip()
        )

        booking = Booking(
            booking_date=booking_date,
            voucher_no=voucher_no,
            description=description,
            lines=(
                BookingLine(
                    account_number=debit_account.number,
                    side=EntrySide.DEBIT,
                    amount=amount,
                ),
                BookingLine(
                    account_number=credit_account.number,
                    side=EntrySide.CREDIT,
                    amount=amount,
                ),
            ),
        )

        self._on_booking_created(booking)

        self._clear()

        self._status_var.set(
            "Buchung wurde übernommen."
        )

    def _resolve_account(
        self,
        value: str,
    ) -> Account | None:
        """Ermittelt eindeutig das ausgewählte Konto."""

        normalized = value.strip()

        if not normalized:
            return None

        direct_match = self._accounts_by_display_name.get(
            normalized
        )

        if direct_match is not None:
            return direct_match

        number_matches = tuple(
            account
            for account in self._accounts
            if account.number == normalized
        )

        if len(number_matches) == 1:
            return number_matches[0]

        search_value = normalized.casefold()

        text_matches = tuple(
            account
            for account in self._accounts
            if search_value
            in self._account_display_name(account).casefold()
        )

        if len(text_matches) == 1:
            return text_matches[0]

        return None

    def _clear(self) -> None:
        """Leert die Buchungsfelder."""

        self._voucher_no_var.set("")
        self._booking_description_var.set("")
        self._debit_account_var.set("")
        self._credit_account_var.set("")
        self._booking_amount_var.set("")

        self._debit_account_box.configure(
            values=self._account_display_names
        )
        self._credit_account_box.configure(
            values=self._account_display_names
        )

        self._voucher_no_entry.focus_set()

    @staticmethod
    def _account_display_name(
        account: Account,
    ) -> str:
        """Liefert die lesbare Kontendarstellung."""

        return f"{account.number} – {account.name}"

    @staticmethod
    def _parse_booking_date(
        value: str,
    ) -> date:
        """Wandelt ein deutsches Datum in date um."""

        try:
            return datetime.strptime(
                value.strip(),
                "%d.%m.%Y",
            ).date()
        except ValueError as exc:
            raise ValueError(
                "Ungültiges Buchungsdatum."
            ) from exc

    @staticmethod
    def _parse_amount(
        value: str,
    ) -> Decimal:
        """Wandelt einen deutschen Geldbetrag in Decimal um."""

        normalized = value.strip()

        if not normalized:
            raise ValueError(
                "Der Buchungsbetrag fehlt."
            )

        normalized = normalized.replace(".", "")
        normalized = normalized.replace(",", ".")

        try:
            amount = Decimal(normalized)
        except InvalidOperation as exc:
            raise ValueError(
                "Ungültiger Geldbetrag."
            ) from exc

        if amount <= ZERO:
            raise ValueError(
                "Der Buchungsbetrag muss größer als 0,00 sein."
            )

        return amount.quantize(
            Decimal("0.01")
        )

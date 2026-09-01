"""Dialog zur Zuordnung einer Anschaffungsbuchung."""

import tkinter as tk
from dataclasses import dataclass
from decimal import Decimal
from tkinter import ttk
from uuid import UUID


@dataclass(frozen=True, slots=True)
class AcquisitionBookingCandidate:
    """Eine passende Buchungszeile für einen Anlagenzugang."""

    booking_id: UUID
    booking_line_position: int
    booking_date_text: str
    voucher_no: str
    description: str
    account_number: str
    amount: Decimal


class FixedAssetAcquisitionLinkDialog(tk.Toplevel):
    """Wählt eine Anschaffungsbuchung für ein Anlagegut aus."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        candidates: tuple[
            AcquisitionBookingCandidate,
            ...
        ],
    ) -> None:
        super().__init__(parent)

        self.title("Anschaffungsbuchung zuordnen")
        self.geometry("820x420")
        self.minsize(700, 320)

        self.transient(parent)
        self.grab_set()

        self._candidates = candidates

        self.selected_candidate: (
            AcquisitionBookingCandidate | None
        ) = None

        container = ttk.Frame(
            self,
            padding=12,
        )
        container.pack(
            fill="both",
            expand=True,
        )

        ttk.Label(
            container,
            text=(
                "Bitte wählen Sie die Buchungszeile aus, "
                "die zu diesem Anlagegut gehört."
            ),
        ).pack(
            anchor="w",
            pady=(0, 12),
        )

        columns = (
            "booking_date",
            "voucher_no",
            "description",
            "account_number",
            "amount",
        )

        self._table = ttk.Treeview(
            container,
            columns=columns,
            show="headings",
            selectmode="browse",
            height=12,
        )

        headings = {
            "booking_date": "Datum",
            "voucher_no": "Beleg",
            "description": "Buchungstext",
            "account_number": "Konto",
            "amount": "Betrag",
        }

        for column, text in headings.items():
            self._table.heading(
                column,
                text=text,
            )

        self._table.column(
            "booking_date",
            width=90,
            anchor="w",
        )
        self._table.column(
            "voucher_no",
            width=100,
            anchor="w",
        )
        self._table.column(
            "description",
            width=330,
            anchor="w",
        )
        self._table.column(
            "account_number",
            width=90,
            anchor="w",
        )
        self._table.column(
            "amount",
            width=110,
            anchor="e",
        )

        self._table.pack(
            fill="both",
            expand=True,
        )

        for index, candidate in enumerate(
            candidates
        ):
            self._table.insert(
                "",
                "end",
                iid=str(index),
                values=(
                    candidate.booking_date_text,
                    candidate.voucher_no,
                    candidate.description,
                    candidate.account_number,
                    f"{candidate.amount:.2f}",
                ),
            )

        button_frame = ttk.Frame(
            container,
        )
        button_frame.pack(
            fill="x",
            pady=(12, 0),
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
            text="Zuordnen",
            command=self._accept,
        ).pack(
            side="right",
            padx=(0, 8),
        )

        self._table.bind(
            "<Double-1>",
            self._on_double_click,
        )

        if candidates:
            self._table.selection_set("0")
            self._table.focus("0")

        self.protocol(
            "WM_DELETE_WINDOW",
            self.destroy,
        )

    def _on_double_click(
        self,
        _event: tk.Event,
    ) -> None:
        """Übernimmt die per Doppelklick ausgewählte Zeile."""

        self._accept()

    def _accept(self) -> None:
        """Übernimmt die ausgewählte Buchungszeile."""

        selection = self._table.selection()

        if not selection:
            return

        try:
            index = int(selection[0])
        except ValueError:
            return

        if index < 0:
            return

        if index >= len(
            self._candidates
        ):
            return

        self.selected_candidate = (
            self._candidates[index]
        )

        self.destroy()

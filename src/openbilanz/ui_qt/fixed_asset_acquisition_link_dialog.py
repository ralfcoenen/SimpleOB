"""Dialog zur Zuordnung einer Anschaffungsbuchung."""

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)


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


class FixedAssetAcquisitionLinkDialog(QDialog):
    """Wählt eine Anschaffungsbuchung für ein Anlagegut aus."""

    def __init__(
        self,
        *,
        candidates: tuple[
            AcquisitionBookingCandidate,
            ...
        ],
        parent=None,
    ) -> None:
        super().__init__(parent)

        self.setWindowTitle(
            "Anschaffungsbuchung zuordnen"
        )
        self.resize(
            820,
            420,
        )

        self._candidates = candidates

        layout = QVBoxLayout(self)

        layout.addWidget(
            QLabel(
                "Bitte wählen Sie die Buchungszeile aus, "
                "die zu diesem Anlagegut gehört."
            )
        )

        self._table = QTableWidget(
            len(candidates),
            5,
        )

        self._table.setHorizontalHeaderLabels(
            (
                "Datum",
                "Beleg",
                "Buchungstext",
                "Konto",
                "Betrag",
            )
        )

        self._table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        self._table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self._table.setSelectionMode(
            QTableWidget.SelectionMode.SingleSelection
        )
        self._table.setAlternatingRowColors(True)

        for row, candidate in enumerate(
            candidates
        ):
            values = (
                candidate.booking_date_text,
                candidate.voucher_no,
                candidate.description,
                candidate.account_number,
                f"{candidate.amount:.2f}",
            )

            for column, value in enumerate(
                values
            ):
                item = QTableWidgetItem(
                    value
                )

                if column == 4:
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignRight
                        | Qt.AlignmentFlag.AlignVCenter
                    )

                self._table.setItem(
                    row,
                    column,
                    item,
                )

        self._table.resizeColumnsToContents()

        layout.addWidget(
            self._table
        )

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )

        buttons.accepted.connect(
            self.accept
        )
        buttons.rejected.connect(
            self.reject
        )

        layout.addWidget(
            buttons
        )

        if candidates:
            self._table.selectRow(
                0
            )

    @property
    def selected_candidate(
        self,
    ) -> AcquisitionBookingCandidate | None:
        """Liefert die ausgewählte Buchungszeile."""

        row = self._table.currentRow()

        if row < 0:
            return None

        if row >= len(
            self._candidates
        ):
            return None

        return self._candidates[
            row
        ]

"""Qt-Tabellenmodell für das Journal."""

from dataclasses import dataclass
from decimal import Decimal

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt


@dataclass(frozen=True, slots=True)
class JournalTableRow:
    """Darstellungszeile des Journals."""

    booking_date: str
    voucher_no: str
    description: str
    account: str
    side: str
    amount: Decimal


class JournalTableModel(QAbstractTableModel):
    """Model für die Journalanzeige."""

    HEADERS = (
        "Datum",
        "Beleg",
        "Buchungstext",
        "Konto",
        "S/H",
        "Betrag",
    )

    def __init__(
        self,
        rows: tuple[JournalTableRow, ...] = (),
    ) -> None:
        super().__init__()
        self._rows = rows

    def rowCount(
        self,
        parent: QModelIndex = QModelIndex(),
    ) -> int:
        if parent.isValid():
            return 0

        return len(self._rows)

    def columnCount(
        self,
        parent: QModelIndex = QModelIndex(),
    ) -> int:
        if parent.isValid():
            return 0

        return len(self.HEADERS)

    def data(
        self,
        index: QModelIndex,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> object | None:
        if not index.isValid():
            return None

        if role == Qt.ItemDataRole.DisplayRole:
            row = self._rows[index.row()]

            values = (
                row.booking_date,
                row.voucher_no,
                row.description,
                row.account,
                row.side,
                self._format_amount(row.amount),
            )

            return values[index.column()]

        if role == Qt.ItemDataRole.TextAlignmentRole:
            if index.column() == 4:
                return (
                    Qt.AlignmentFlag.AlignCenter
                    | Qt.AlignmentFlag.AlignVCenter
                )

            if index.column() == 5:
                return (
                    Qt.AlignmentFlag.AlignRight
                    | Qt.AlignmentFlag.AlignVCenter
                )

        return None

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> object | None:
        if (
            role == Qt.ItemDataRole.DisplayRole
            and orientation == Qt.Orientation.Horizontal
        ):
            return self.HEADERS[section]

        return super().headerData(
            section,
            orientation,
            role,
        )

    def replace_rows(
        self,
        rows: tuple[JournalTableRow, ...],
    ) -> None:
        """Ersetzt den vollständigen Tabelleninhalt."""

        self.beginResetModel()
        self._rows = rows
        self.endResetModel()

    @staticmethod
    def _format_amount(amount: Decimal) -> str:
        return f"{amount:.2f}"

"""Qt-Tabellenmodell für die Kontenübersicht."""

from dataclasses import dataclass
from decimal import Decimal

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt

from openbilanz.domain.account import Account


@dataclass(frozen=True, slots=True)
class AccountTableRow:
    """Darstellungsdaten einer Kontenzeile."""

    account: Account
    debit: Decimal
    credit: Decimal
    balance: str


class AccountsTableModel(QAbstractTableModel):
    """Model für die Kontenübersicht."""

    HEADERS = (
        "Konto",
        "Bezeichnung",
        "Soll",
        "Haben",
        "Saldo",
    )

    def __init__(
        self,
        rows: tuple[AccountTableRow, ...] = (),
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

        if role != Qt.ItemDataRole.DisplayRole:
            return None

        row = self._rows[index.row()]

        values = (
            row.account.number,
            row.account.name,
            self._format_amount(row.debit),
            self._format_amount(row.credit),
            row.balance,
        )

        return values[index.column()]

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

    def account_at(self, row: int) -> Account:
        """Liefert das Domain-Konto einer Tabellenzeile."""

        return self._rows[row].account

    def replace_rows(
        self,
        rows: tuple[AccountTableRow, ...],
    ) -> None:
        """Ersetzt den vollständigen Tabelleninhalt."""

        self.beginResetModel()
        self._rows = rows
        self.endResetModel()

    @staticmethod
    def _format_amount(amount: Decimal) -> str:
        return f"{amount:.2f}"

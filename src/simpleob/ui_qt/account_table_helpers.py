"""Hilfsfunktionen für Kontonummern in Qt-Tabellen."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QAbstractItemView, QTableWidget, QTableWidgetItem


class AccountNumberTableWidgetItem(QTableWidgetItem):
    """Sortiert rein numerische Kontonummern nach ihrem Zahlenwert."""

    def __lt__(self, other: QTableWidgetItem) -> bool:
        own_text = self.text()
        other_text = other.text()
        if own_text.isdecimal() and other_text.isdecimal():
            return int(own_text) < int(other_text)
        return own_text.casefold() < other_text.casefold()


def select_account_row(
    table: QTableWidget,
    account_number: str,
) -> bool:
    """Wählt ein Konto anhand seiner Nummer aus und scrollt es sichtbar."""

    for row in range(table.rowCount()):
        item = table.item(row, 0)
        if item is None or item.text() != account_number:
            continue
        if table.isRowHidden(row):
            return False
        table.setCurrentCell(row, 0)
        table.selectRow(row)
        table.setFocus()
        table.scrollToItem(
            item,
            QAbstractItemView.ScrollHint.PositionAtCenter,
        )
        return True
    return False


def set_default_account_sort(table: QTableWidget) -> None:
    """Aktiviert Tabellensortierung und setzt Kontonummer aufsteigend."""

    table.setSortingEnabled(True)
    table.sortItems(0, Qt.SortOrder.AscendingOrder)

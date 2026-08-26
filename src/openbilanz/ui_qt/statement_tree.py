"""Gemeinsame Qt-Baumdarstellung für HGB-Abschlusspositionen."""

from collections.abc import Callable, Mapping
from decimal import Decimal

from PySide6.QtCore import Qt
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import QHeaderView, QTreeView

from openbilanz.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
from openbilanz.domain.money import ZERO


class StatementTree(QTreeView):
    """Zeigt belegte HGB-Positionen hierarchisch an."""

    def __init__(self) -> None:
        super().__init__()

        self._model = QStandardItemModel()
        self._model.setHorizontalHeaderLabels(
            ("Position", "Betrag")
        )

        self.setModel(self._model)
        self.setAlternatingRowColors(True)
        self.setRootIsDecorated(True)
        self.setItemsExpandable(True)
        self.setUniformRowHeights(True)

        header = self.header()

        header.setSectionResizeMode(
            0,
            QHeaderView.ResizeMode.Interactive,
        )
        header.setSectionResizeMode(
            1,
            QHeaderView.ResizeMode.Interactive,
        )

        header.resizeSection(
            0,
            420,
        )
        header.resizeSection(
            1,
            120,
        )

        header.setStretchLastSection(True)


    def replace_positions(
        self,
        *,
        positions: tuple[FinancialStatementPosition, ...],
        amount_for: Callable[
            [FinancialStatementPosition],
            Decimal,
        ],
        account_details: Mapping[
            str,
            tuple[tuple[str, Decimal], ...],
        ] | None = None,
    ) -> None:
        """Ersetzt den vollständigen Inhalt."""

        self._model.removeRows(
            0,
            self._model.rowCount(),
        )

        root = self._model.invisibleRootItem()

        details = (
            account_details
            if account_details is not None
            else {}
        )

        for position in positions:
            self._append_position(
                parent=root,
                position=position,
                amount_for=amount_for,
                account_details=details,
            )

        self.expandAll()

    def clear_positions(self) -> None:
        """Leert die Abschlussdarstellung."""

        self._model.removeRows(
            0,
            self._model.rowCount(),
        )

    def _append_position(
        self,
        *,
        parent: QStandardItem,
        position: FinancialStatementPosition,
        amount_for: Callable[
            [FinancialStatementPosition],
            Decimal,
        ],
        account_details: Mapping[
            str,
            tuple[tuple[str, Decimal], ...],
        ],
    ) -> None:
        amount = amount_for(position)

        if amount == ZERO:
            return

        position_item = QStandardItem(
            position.name
        )
        position_item.setEditable(False)

        amount_item = QStandardItem(
            self._format_amount(amount)
        )
        amount_item.setEditable(False)
        amount_item.setTextAlignment(
            Qt.AlignmentFlag.AlignRight
            | Qt.AlignmentFlag.AlignVCenter
        )

        parent.appendRow(
            (position_item, amount_item)
        )

        for child in position.children:
            self._append_position(
                parent=position_item,
                position=child,
                amount_for=amount_for,
                account_details=account_details,
            )

        for label, detail_amount in account_details.get(
            position.code,
            (),
        ):
            account_item = QStandardItem(
                label
            )
            account_item.setEditable(False)

            font = account_item.font()
            font.setItalic(True)
            account_item.setFont(font)

            account_amount_item = QStandardItem(
                self._format_amount(
                    detail_amount
                )
            )
            account_amount_item.setEditable(False)
            account_amount_item.setTextAlignment(
                Qt.AlignmentFlag.AlignRight
                | Qt.AlignmentFlag.AlignVCenter
            )

            position_item.appendRow(
                (
                    account_item,
                    account_amount_item,
                )
            )

    @staticmethod
    def _format_amount(
        amount: Decimal,
    ) -> str:
        formatted = f"{amount:,.2f}"

        return (
            formatted
            .replace(",", "X")
            .replace(".", ",")
            .replace("X", ".")
        )

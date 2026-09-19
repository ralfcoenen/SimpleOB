"""PySide6-Darstellung der Bilanz."""

from decimal import Decimal

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from openbilanz.accounting.balance_sheet import BalanceSheet
from openbilanz.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
from openbilanz.domain.money import ZERO


class BalanceSheetFrame(QWidget):
    """Stellt eine HGB-Bilanz dar."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._create_ui()

    def _create_ui(self) -> None:
        """Erzeugt die Bilanzdarstellung."""

        layout = QVBoxLayout(self)

        headings_layout = QHBoxLayout()

        assets_label = QLabel("Aktiva")
        assets_label.setStyleSheet(
            "font-size: 15px; font-weight: bold;"
        )
        headings_layout.addWidget(assets_label)

        liabilities_label = QLabel("Passiva")
        liabilities_label.setStyleSheet(
            "font-size: 15px; font-weight: bold;"
        )
        headings_layout.addWidget(liabilities_label)

        layout.addLayout(headings_layout)

        trees_layout = QHBoxLayout()

        self._assets_tree = self._create_tree()
        self._liabilities_tree = self._create_tree()

        trees_layout.addWidget(self._assets_tree)
        trees_layout.addWidget(self._liabilities_tree)

        layout.addLayout(trees_layout)

        self._totals_label = QLabel(
            "Aktiva: 0,00 €   Passiva: 0,00 €"
        )
        self._totals_label.setStyleSheet(
            "font-size: 12px; font-weight: bold;"
        )
        self._totals_label.setAlignment(
            self._totals_label.alignment()
        )
        layout.addWidget(self._totals_label)

        self._status_label = QLabel(
            "Bilanz ausgeglichen: Ja"
        )
        layout.addWidget(self._status_label)

    @staticmethod
    def _create_tree() -> QTreeWidget:
        """Erzeugt eine Baumansicht für eine Bilanzseite."""

        tree = QTreeWidget()
        tree.setColumnCount(2)
        tree.setHeaderLabels(
            (
                "Position",
                "Betrag",
            )
        )
        tree.setColumnWidth(0, 330)
        tree.setColumnWidth(1, 130)
        tree.setAlternatingRowColors(True)

        return tree

    def update_balance_sheet(
        self,
        balance_sheet: BalanceSheet,
    ) -> None:
        """Zeigt die übergebene Bilanz an."""

        self._assets_tree.clear()
        self._liabilities_tree.clear()

        self._insert_position(
            tree=self._assets_tree,
            parent=None,
            position=balance_sheet.assets,
            balance_sheet=balance_sheet,
        )

        self._insert_position(
            tree=self._liabilities_tree,
            parent=None,
            position=balance_sheet.liabilities,
            balance_sheet=balance_sheet,
        )

        self._assets_tree.expandAll()
        self._liabilities_tree.expandAll()

        assets_total = balance_sheet.amount_for(
            balance_sheet.assets
        )
        liabilities_total = balance_sheet.amount_for(
            balance_sheet.liabilities
        )

        self._totals_label.setText(
            "Aktiva: "
            f"{self._format_amount(assets_total)} €"
            "   "
            "Passiva: "
            f"{self._format_amount(liabilities_total)} €"
        )

        if balance_sheet.is_balanced():
            self._status_label.setText(
                "Bilanz ausgeglichen: Ja"
            )
        else:
            difference = (
                assets_total
                - liabilities_total
            )

            self._status_label.setText(
                "Bilanz ausgeglichen: Nein"
                "   Differenz: "
                f"{self._format_amount(difference)} €"
            )

    def _insert_position(
        self,
        *,
        tree: QTreeWidget,
        parent: QTreeWidgetItem | None,
        position: FinancialStatementPosition,
        balance_sheet: BalanceSheet,
    ) -> None:
        """Fügt eine HGB-Position rekursiv ein."""

        amount = balance_sheet.amount_for(
            position
        )

        if amount == ZERO:
            return

        item = QTreeWidgetItem(
            (
                position.name,
                self._format_amount(amount),
            )
        )

        if parent is None:
            tree.addTopLevelItem(item)
        else:
            parent.addChild(item)

        for child in position.children:
            self._insert_position(
                tree=tree,
                parent=item,
                position=child,
                balance_sheet=balance_sheet,
            )

    @staticmethod
    def _format_amount(
        amount: Decimal,
    ) -> str:
        """Formatiert einen Geldbetrag deutsch."""

        formatted = f"{amount:,.2f}"

        return (
            formatted
            .replace(",", "X")
            .replace(".", ",")
            .replace("X", ".")
        )

    def show_mapping_error(
        self,
        message: str,
    ) -> None:
        """Zeigt einen Fehler bei der Bilanzzuordnung an."""

        self._assets_tree.clear()
        self._liabilities_tree.clear()

        self._totals_label.setText(
            "Bilanz kann nicht vollständig ermittelt werden."
        )

        self._status_label.setText(message)

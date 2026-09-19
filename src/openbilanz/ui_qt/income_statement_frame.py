"""PySide6-Darstellung der Gewinn- und Verlustrechnung."""

from decimal import Decimal

from PySide6.QtWidgets import (
    QLabel,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from openbilanz.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
from openbilanz.accounting.income_statement import IncomeStatement
from openbilanz.domain.money import ZERO


class IncomeStatementFrame(QWidget):
    """Stellt die laufende GuV nach § 275 HGB dar."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._create_ui()

    def _create_ui(self) -> None:
        """Erzeugt die GuV-Darstellung."""

        layout = QVBoxLayout(self)

        self._tree = QTreeWidget()
        self._tree.setColumnCount(2)
        self._tree.setHeaderLabels(
            (
                "Position",
                "Betrag",
            )
        )
        self._tree.setColumnWidth(0, 620)
        self._tree.setColumnWidth(1, 150)
        self._tree.setAlternatingRowColors(True)

        layout.addWidget(self._tree)

        self._result_label = QLabel(
            "Laufendes Ergebnis: 0,00 €"
        )
        self._result_label.setStyleSheet(
            "font-size: 12px; font-weight: bold;"
        )
        layout.addWidget(self._result_label)

    def update_income_statement(
        self,
        *,
        income_statement: IncomeStatement,
        net_income: Decimal,
    ) -> None:
        """Aktualisiert die GuV."""

        self._tree.clear()

        for position in (
            income_statement.income_statement.children
        ):
            self._insert_position(
                parent=None,
                position=position,
                income_statement=income_statement,
            )

        self._tree.expandAll()

        if net_income > ZERO:
            description = "Jahresüberschuss"
        elif net_income < ZERO:
            description = "Jahresfehlbetrag"
        else:
            description = "Ergebnis"

        self._result_label.setText(
            f"{description}: "
            f"{self._format_amount(net_income)} €"
        )

    def _insert_position(
        self,
        *,
        parent: QTreeWidgetItem | None,
        position: FinancialStatementPosition,
        income_statement: IncomeStatement,
    ) -> None:
        """Fügt eine belegte GuV-Position ein."""

        amount = income_statement.amount_for(
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
            self._tree.addTopLevelItem(item)
        else:
            parent.addChild(item)

        for child in position.children:
            self._insert_position(
                parent=item,
                position=child,
                income_statement=income_statement,
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

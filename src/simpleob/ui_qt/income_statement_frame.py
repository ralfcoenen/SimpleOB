"""PySide6-Darstellung der Gewinn- und Verlustrechnung."""

from decimal import Decimal

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from simpleob.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
from simpleob.accounting.income_statement import IncomeStatement
from simpleob.accounting.statement_category import StatementCategory
from simpleob.domain.money import ZERO
from simpleob.domain.profit_appropriation_annual_data import (
    ProfitAppropriationAnnualData,
)
from simpleob.services.profit_appropriation_presentation_service import (
    ProfitAppropriationPresentationService,
)


class IncomeStatementFrame(QWidget):
    """Stellt die laufende GuV nach § 275 HGB dar."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._create_ui()

    def _create_ui(self) -> None:
        """Erzeugt die GuV-Darstellung."""

        layout = QVBoxLayout(self)

        headings_layout = QHBoxLayout()

        income_label = QLabel("Erträge")
        income_label.setStyleSheet(
            "font-size: 15px; font-weight: bold;"
        )
        headings_layout.addWidget(income_label)

        expenses_label = QLabel("Aufwendungen")
        expenses_label.setStyleSheet(
            "font-size: 15px; font-weight: bold;"
        )
        headings_layout.addWidget(expenses_label)

        layout.addLayout(headings_layout)

        trees_layout = QHBoxLayout()

        self._income_tree = self._create_tree()
        self._expenses_tree = self._create_tree()

        trees_layout.addWidget(self._income_tree)
        trees_layout.addWidget(self._expenses_tree)

        layout.addLayout(trees_layout)

        self._result_label = QLabel(
            "Laufendes Ergebnis: 0,00 €"
        )
        self._result_label.setStyleSheet(
            "font-size: 12px; font-weight: bold;"
        )
        layout.addWidget(self._result_label)

        self._appropriation_label = QLabel()
        self._appropriation_label.setWordWrap(True)
        self._appropriation_label.setStyleSheet(
            "font-size: 12px; margin-top: 6px;"
        )
        self._appropriation_label.hide()
        layout.addWidget(self._appropriation_label)

    @staticmethod
    def _create_tree() -> QTreeWidget:
        """Erzeugt eine Baumansicht für eine GuV-Seite."""

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

    def update_income_statement(
        self,
        *,
        income_statement: IncomeStatement,
        net_income: Decimal,
        appropriation_data: ProfitAppropriationAnnualData | None = None,
        previous_carryforward: Decimal = ZERO,
    ) -> None:
        """Aktualisiert die GuV."""

        self._income_tree.clear()
        self._expenses_tree.clear()

        for position in (
            income_statement.income_statement.children
        ):
            self._insert_position(
                income_parent=None,
                expenses_parent=None,
                position=position,
                income_statement=income_statement,
            )

        self._income_tree.expandAll()
        self._expenses_tree.expandAll()

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

        if appropriation_data is None:
            self._appropriation_label.clear()
            self._appropriation_label.hide()
            return

        balance_profit_loss = (
            ProfitAppropriationPresentationService
            .remaining_balance_profit_loss(
                net_income=net_income,
                previous_carryforward=previous_carryforward,
                data=appropriation_data,
            )
        )
        rows = [
            "Ergebnisverwendung",
            f"{description}: {self._format_amount(net_income)} €",
            f"Gewinn-/Verlustvortrag aus Vorjahr: "
            f"{self._format_amount(previous_carryforward)} €",
            f"Zuführung gesetzliche Rücklage: "
            f"−{self._format_amount(appropriation_data.statutory_reserve_addition)} €",
            f"Zuführung andere Gewinnrücklagen: "
            f"−{self._format_amount(appropriation_data.other_revenue_reserves_addition)} €",
            f"Auflösung gesetzliche Rücklage: "
            f"{self._format_amount(appropriation_data.statutory_reserve_release)} €",
            f"Auflösung anderer Gewinnrücklagen: "
            f"{self._format_amount(appropriation_data.other_revenue_reserves_release)} €",
            f"Ausschüttung: "
            f"−{self._format_amount(appropriation_data.distribution)} €",
            f"Neuer Gewinn-/Verlustvortrag: "
            f"{self._format_amount(appropriation_data.profit_loss_carryforward)} €",
            f"Bilanzgewinn/Bilanzverlust: "
            f"{self._format_amount(balance_profit_loss)} €",
        ]
        self._appropriation_label.setText("\n".join(rows))
        self._appropriation_label.show()

    def _insert_position(
        self,
        *,
        income_parent: QTreeWidgetItem | None,
        expenses_parent: QTreeWidgetItem | None,
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

        if position.category is StatementCategory.INCOME:
            if income_parent is None:
                self._income_tree.addTopLevelItem(item)
            else:
                income_parent.addChild(item)

            for child in position.children:
                self._insert_position(
                    income_parent=item,
                    expenses_parent=None,
                    position=child,
                    income_statement=income_statement,
                )

            return

        if position.category is StatementCategory.EXPENSE:
            if expenses_parent is None:
                self._expenses_tree.addTopLevelItem(item)
            else:
                expenses_parent.addChild(item)

            for child in position.children:
                self._insert_position(
                    income_parent=None,
                    expenses_parent=item,
                    position=child,
                    income_statement=income_statement,
                )

            return

        for child in position.children:
            self._insert_position(
                income_parent=income_parent,
                expenses_parent=expenses_parent,
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

"""GuV-Darstellung der PySide6-Oberfläche."""

from decimal import Decimal

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from openbilanz.accounting.income_statement import (
    IncomeStatement,
)
from openbilanz.domain.money import ZERO
from openbilanz.ui_qt.statement_tree import StatementTree


class IncomeStatementPage(QWidget):
    """Stellt die GuV nach § 275 HGB dar."""

    def __init__(
        self,
        *,
        on_export_pdf=None,
    ) -> None:
        super().__init__()

        layout = QVBoxLayout(self)

        header = QHBoxLayout()

        title = QLabel(
            "Gewinn- und Verlustrechnung nach § 275 HGB"
        )
        font = title.font()
        font.setPointSize(16)
        font.setBold(True)
        title.setFont(font)

        header.addWidget(title)
        header.addStretch()

        self._export_button = QPushButton(
            "PDF exportieren"
        )
        self._export_button.setEnabled(
            on_export_pdf is not None
        )

        if on_export_pdf is not None:
            self._export_button.clicked.connect(
                on_export_pdf
            )

        header.addWidget(self._export_button)

        layout.addLayout(header)

        self._tree = StatementTree()
        layout.addWidget(self._tree, 1)

        self._result_label = QLabel(
            "Laufendes Ergebnis: 0,00 €"
        )
        self._result_label.setAlignment(
            Qt.AlignmentFlag.AlignRight
        )

        font = self._result_label.font()
        font.setBold(True)
        self._result_label.setFont(font)

        layout.addWidget(self._result_label)

    def update_income_statement(
        self,
        *,
        income_statement: IncomeStatement,
        net_income: Decimal,
    ) -> None:
        """Aktualisiert die GuV."""

        self._tree.replace_positions(
            positions=tuple(
                income_statement
                .income_statement
                .children
            ),
            amount_for=income_statement.amount_for,
        )

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

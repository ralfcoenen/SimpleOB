"""Bilanzdarstellung der PySide6-Oberfläche."""

from collections.abc import Mapping
from decimal import Decimal

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from openbilanz.accounting.balance_sheet import BalanceSheet
from openbilanz.ui_qt.statement_tree import StatementTree


class BalanceSheetPage(QWidget):
    """Stellt die Bilanz nach § 266 HGB dar."""

    def __init__(
        self,
        *,
        on_export_pdf=None,
    ) -> None:
        super().__init__()

        layout = QVBoxLayout(self)

        header = QHBoxLayout()

        title = QLabel("Bilanz nach § 266 HGB")
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

        trees = QHBoxLayout()

        assets_layout = QVBoxLayout()
        liabilities_layout = QVBoxLayout()

        assets_title = QLabel("Aktiva")
        liabilities_title = QLabel("Passiva")

        for label in (
            assets_title,
            liabilities_title,
        ):
            font = label.font()
            font.setPointSize(14)
            font.setBold(True)
            label.setFont(font)

        self._assets_tree = StatementTree()
        self._liabilities_tree = StatementTree()

        assets_layout.addWidget(assets_title)
        assets_layout.addWidget(self._assets_tree)

        liabilities_layout.addWidget(
            liabilities_title
        )
        liabilities_layout.addWidget(
            self._liabilities_tree
        )

        trees.addLayout(assets_layout)
        trees.addLayout(liabilities_layout)

        layout.addLayout(trees, 1)

        self._totals_label = QLabel(
            "Aktiva: 0,00 €   Passiva: 0,00 €"
        )
        self._status_label = QLabel(
            "Bilanz ausgeglichen: Ja"
        )

        for label in (
            self._totals_label,
            self._status_label,
        ):
            label.setAlignment(
                Qt.AlignmentFlag.AlignRight
            )

        font = self._totals_label.font()
        font.setBold(True)
        self._totals_label.setFont(font)

        layout.addWidget(self._totals_label)
        layout.addWidget(self._status_label)

    def update_balance_sheet(
        self,
        balance_sheet: BalanceSheet,
        *,
        account_details: Mapping[
            str,
            tuple[tuple[str, Decimal], ...],
        ] | None = None,
    ) -> None:
        """Aktualisiert die sichtbare Bilanz."""

        self._assets_tree.replace_positions(
            positions=(balance_sheet.assets,),
            amount_for=balance_sheet.amount_for,
            account_details=account_details,
        )

        self._liabilities_tree.replace_positions(
            positions=(balance_sheet.liabilities,),
            amount_for=balance_sheet.amount_for,
            account_details=account_details,
        )

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
                assets_total - liabilities_total
            )

            self._status_label.setText(
                "Bilanz ausgeglichen: Nein"
                "   Differenz: "
                f"{self._format_amount(difference)} €"
            )

    def show_mapping_error(
        self,
        message: str,
    ) -> None:
        """Zeigt einen Fehler bei der Kontenzuordnung."""

        self._assets_tree.clear_positions()
        self._liabilities_tree.clear_positions()

        self._totals_label.setText(
            "Bilanz kann nicht vollständig "
            "ermittelt werden."
        )
        self._status_label.setText(message)

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

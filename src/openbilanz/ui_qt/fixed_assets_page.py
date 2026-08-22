"""Anlagegüterübersicht der PySide6-Oberfläche."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from openbilanz.domain.fixed_asset import FixedAsset


class FixedAssetsPage(QWidget):
    """Arbeitsbereich für die Anlagenbuchhaltung."""

    def __init__(
        self,
        *,
        on_add,
        on_process_depreciations,
    ) -> None:
        super().__init__()

        layout = QVBoxLayout(self)

        header = QHBoxLayout()

        title = QLabel("Anlagegüter")
        font = title.font()
        font.setPointSize(16)
        font.setBold(True)
        title.setFont(font)

        header.addWidget(title)
        header.addStretch()

        self._process_button = QPushButton(
            "Abschreibungen prüfen/buchen"
        )
        self._process_button.clicked.connect(
            on_process_depreciations
        )
        header.addWidget(self._process_button)

        self._add_button = QPushButton(
            "Anlagegut hinzufügen"
        )
        self._add_button.clicked.connect(on_add)
        header.addWidget(self._add_button)

        layout.addLayout(header)

        self._table = QTableWidget(0, 8)

        self._table.setHorizontalHeaderLabels(
            (
                "Anlagen-ID",
                "Bezeichnung",
                "Anschaffung",
                "AK/HK",
                "ND Monate",
                "Anlagekonto",
                "AfA-Konto",
                "Status",
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

        self._table.verticalHeader().setVisible(False)

        header_view = self._table.horizontalHeader()

        header_view.setSectionResizeMode(
            0,
            QHeaderView.ResizeMode.ResizeToContents,
        )
        header_view.setSectionResizeMode(
            1,
            QHeaderView.ResizeMode.Stretch,
        )

        for column in range(2, 8):
            header_view.setSectionResizeMode(
                column,
                QHeaderView.ResizeMode.ResizeToContents,
            )

        layout.addWidget(self._table)

    def set_assets(
        self,
        assets: tuple[FixedAsset, ...],
    ) -> None:
        """Zeigt die vorhandenen Anlagegüter."""

        self._table.setRowCount(
            len(assets)
        )

        for row, asset in enumerate(assets):
            status = (
                "Aktiv"
                if asset.status.value == "ACTIVE"
                else "Abgegangen"
            )

            values = (
                asset.asset_code,
                asset.description,
                f"{asset.acquisition_date:%d.%m.%Y}",
                f"{asset.acquisition_cost:.2f}",
                str(asset.useful_life_months),
                asset.asset_account_number,
                asset.depreciation_expense_account_number,
                status,
            )

            for column, value in enumerate(values):
                item = QTableWidgetItem(value)

                if column == 3:
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignRight
                        | Qt.AlignmentFlag.AlignVCenter
                    )

                self._table.setItem(
                    row,
                    column,
                    item,
                )

    def set_editing_enabled(
        self,
        enabled: bool,
    ) -> None:
        """Aktiviert Funktionen für offene Geschäftsjahre."""

        self._add_button.setEnabled(enabled)
        self._process_button.setEnabled(enabled)

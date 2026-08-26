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
        on_edit,
        on_delete,
        on_link_acquisition,
        on_loss,
        on_process_depreciations,
        on_dispose,
    ) -> None:
        super().__init__()
        self._assets: tuple[FixedAsset, ...] = ()

        layout = QVBoxLayout(self)

        header = QHBoxLayout()

        title = QLabel("Anlagegüter")
        font = title.font()
        font.setPointSize(16)
        font.setBold(True)
        title.setFont(font)

        header.addWidget(title)
        header.addStretch()

        self._link_acquisition_button = QPushButton(
            "Anschaffungsbuchung zuordnen"
        )
        self._loss_button = QPushButton(
            "Totalverlust ausbuchen"
        )
        self._loss_button.clicked.connect(
            on_loss
        )

        header.addWidget(
            self._loss_button
        )
        self._link_acquisition_button.clicked.connect(
            on_link_acquisition
        )

        header.addWidget(
            self._link_acquisition_button
        )

        self._process_button = QPushButton(
            "Abschreibungen prüfen/buchen"
        )
        self._process_button.clicked.connect(
            on_process_depreciations
        )
        header.addWidget(self._process_button)

        self._dispose_button = QPushButton(
            "Anlagegut verkaufen"
        )
        self._dispose_button.clicked.connect(
            on_dispose
        )
        header.addWidget(self._dispose_button)

        self._edit_button = QPushButton(
            "Anlagegut bearbeiten"
        )
        self._edit_button.clicked.connect(
            on_edit
        )
        header.addWidget(
            self._edit_button
        )
        self._delete_button = QPushButton(
            "Anlagegut löschen"
        )
        self._delete_button.clicked.connect(
            on_delete
        )
        header.addWidget(
            self._delete_button
        )

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
        self._table.setHorizontalScrollMode(
            QTableWidget.ScrollMode.ScrollPerPixel
        )

        self._table.verticalHeader().setVisible(False)

        header_view = self._table.horizontalHeader()

        header_view.setSectionResizeMode(
            0,
            QHeaderView.ResizeMode.ResizeToContents,
        )
        header_view.setSectionResizeMode(
            1,
            QHeaderView.ResizeMode.Interactive,
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

        self._assets = assets

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

    def selected_asset(
        self,
    ) -> FixedAsset | None:
        """Liefert das aktuell ausgewählte Anlagegut."""

        row = self._table.currentRow()

        if row < 0:
            return None

        if row >= len(self._assets):
            return None

        return self._assets[row]

    def set_editing_enabled(
        self,
        enabled: bool,
    ) -> None:
        """Aktiviert Funktionen für offene Geschäftsjahre."""

        self._add_button.setEnabled(enabled)
        self._link_acquisition_button.setEnabled(enabled)
        self._process_button.setEnabled(enabled)
        self._edit_button.setEnabled(enabled)
        self._delete_button.setEnabled(enabled)

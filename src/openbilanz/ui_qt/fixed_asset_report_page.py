"""Anlagenbericht der PySide6-Oberfläche."""

from collections.abc import Callable
from decimal import Decimal

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from openbilanz.reporting.fixed_asset_report import (
    FixedAssetReport,
)


class FixedAssetReportPage(QWidget):
    """Zeigt den Anlagenbericht des Geschäftsjahres."""

    def __init__(
        self,
        *,
        build_report: Callable[
            [],
            FixedAssetReport,
        ],
        on_export_pdf=None,
    ) -> None:
        super().__init__()

        self._build_report = build_report
        self._current_report: FixedAssetReport | None = None

        layout = QVBoxLayout(self)

        title = QLabel("Anlagenbericht")
        font = title.font()
        font.setPointSize(16)
        font.setBold(True)
        title.setFont(font)

        layout.addWidget(title)

        description = QLabel(
            "Übersicht der Anlagegüter mit gebuchten "
            "Abschreibungen und Buchwerten."
        )
        layout.addWidget(description)

        self._refresh_button = QPushButton(
            "Aktualisieren"
        )
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

        layout.addWidget(
            self._export_button
        )

        self._refresh_button.clicked.connect(
            self.refresh_report
        )

        layout.addWidget(
            self._refresh_button
        )

        self._table = QTableWidget(0, 10)

        self._table.setHorizontalHeaderLabels(
            (
                "Anlagen-ID",
                "Bezeichnung",
                "Anlagekonto",
                "Anschaffungsdatum",
                "AK/HK",
                "AfA Vorjahre",
                "AfA Geschäftsjahr",
                "Kumulierte AfA",
                "Buchwert",
                "Abgang",
            )
        )

        self._table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setHorizontalScrollMode(
            QTableWidget.ScrollMode.ScrollPerPixel
        )

        header = self._table.horizontalHeader()

        header.setSectionResizeMode(
            0,
            QHeaderView.ResizeMode.ResizeToContents,
        )
        header.setSectionResizeMode(
            1,
            QHeaderView.ResizeMode.Stretch,
        )

        for column in range(2, 10):
            header.setSectionResizeMode(
                column,
                QHeaderView.ResizeMode.ResizeToContents,
            )

        layout.addWidget(
            self._table,
            1,
        )

        self._totals = QLabel()
        self._totals.setAlignment(
            Qt.AlignmentFlag.AlignRight
        )

        layout.addWidget(
            self._totals
        )

    @property
    def current_report(
        self,
    ) -> FixedAssetReport | None:
        return self._current_report

    def refresh_report(self) -> None:
        """Erzeugt den Anlagenbericht neu."""

        try:
            report = self._build_report()
        except (
            ValueError,
            RuntimeError,
        ) as exc:
            QMessageBox.critical(
                self,
                "Anlagenbericht",
                str(exc),
            )
            return

        self._current_report = report

        self._table.setRowCount(
            len(report.rows)
        )

        for table_row, row in enumerate(
            report.rows
        ):
            disposal_date = (
                row.disposal_date.strftime(
                    "%d.%m.%Y"
                )
                if row.disposal_date is not None
                else ""
            )

            values = (
                row.asset_code,
                row.description,
                row.asset_account_number,
                row.acquisition_date.strftime(
                    "%d.%m.%Y"
                ),
                self._format_amount(
                    row.acquisition_cost
                ),
                self._format_amount(
                    row.opening_depreciation
                ),
                self._format_amount(
                    row.current_depreciation
                ),
                self._format_amount(
                    row.accumulated_depreciation
                ),
                self._format_amount(
                    row.closing_book_value
                ),
                disposal_date,
            )

            for column, value in enumerate(values):
                item = QTableWidgetItem(
                    value
                )

                if 4 <= column <= 8:
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignRight
                        | Qt.AlignmentFlag.AlignVCenter
                    )

                self._table.setItem(
                    table_row,
                    column,
                    item,
                )

        self._totals.setText(
            "Summen: "
            f"AK/HK "
            f"{self._format_amount(report.acquisition_cost_total)} · "
            f"AfA Vorjahre "
            f"{self._format_amount(report.opening_depreciation_total)} · "
            f"AfA Geschäftsjahr "
            f"{self._format_amount(report.current_depreciation_total)} · "
            f"Kumulierte AfA "
            f"{self._format_amount(report.accumulated_depreciation_total)} · "
            f"Buchwert "
            f"{self._format_amount(report.closing_book_value_total)}"
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

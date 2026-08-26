"""Journal-Auswertung der PySide6-Oberfläche."""

from collections.abc import Callable
from datetime import date
from decimal import Decimal

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from openbilanz.domain.entry_side import EntrySide
from openbilanz.reporting.journal_report import JournalReport
from openbilanz.ui.date_input import (
    normalize_german_date,
    parse_german_date,
)


class JournalReportPage(QWidget):
    """Zeigt das Journal für einen gewählten Zeitraum."""

    def __init__(
        self,
        *,
        fiscal_year_start: date,
        fiscal_year_end: date,
        account_names: dict[str, str],
        build_report: Callable[
            [date, date],
            JournalReport,
        ],
        on_export_pdf=None,
    ) -> None:
        super().__init__()

        self._account_names = account_names
        self._build_report = build_report
        self._current_report: JournalReport | None = None

        layout = QVBoxLayout(self)

        title = QLabel("Journal")
        font = title.font()
        font.setPointSize(16)
        font.setBold(True)
        title.setFont(font)

        layout.addWidget(title)

        layout.addWidget(
            QLabel(
                "Auswertung der Buchungen "
                "für einen gewählten Zeitraum."
            )
        )

        filters = QHBoxLayout()

        filters.addWidget(QLabel("Von"))

        self._start_date = QLineEdit(
            fiscal_year_start.strftime("%d.%m.%Y")
        )
        self._start_date.setMaximumWidth(120)
        self._start_date.editingFinished.connect(
            lambda: self._normalize_date(
                self._start_date
            )
        )
        filters.addWidget(self._start_date)

        filters.addWidget(QLabel("Bis"))

        self._end_date = QLineEdit(
            fiscal_year_end.strftime("%d.%m.%Y")
        )
        self._end_date.setMaximumWidth(120)
        self._end_date.editingFinished.connect(
            lambda: self._normalize_date(
                self._end_date
            )
        )
        filters.addWidget(self._end_date)

        self._refresh_button = QPushButton(
            "Aktualisieren"
        )
        self._refresh_button.clicked.connect(
            self.refresh_report
        )
        filters.addWidget(self._refresh_button)

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

        filters.addWidget(self._export_button)
        filters.addStretch()

        layout.addLayout(filters)

        self._table = QTableWidget(0, 8)

        self._table.setHorizontalHeaderLabels(
            (
                "Nr.",
                "Datum",
                "Beleg",
                "Buchungstext",
                "Konto",
                "Bezeichnung",
                "S/H",
                "Betrag",
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

        for column in (0, 1, 2, 4, 6, 7):
            header.setSectionResizeMode(
                column,
                QHeaderView.ResizeMode.ResizeToContents,
            )

        header.setSectionResizeMode(
            3,
            QHeaderView.ResizeMode.Interactive,
        )

        header.setSectionResizeMode(
            5,
            QHeaderView.ResizeMode.Interactive,
        )

        layout.addWidget(
            self._table,
            1,
        )

    @property
    def current_report(
        self,
    ) -> JournalReport | None:
        return self._current_report

    def refresh_report(self) -> None:
        """Aktualisiert die Journal-Auswertung."""

        try:
            start_date = parse_german_date(
                self._start_date.text()
            )

            end_date = parse_german_date(
                self._end_date.text()
            )

            report = self._build_report(
                start_date,
                end_date,
            )

        except ValueError as exc:
            QMessageBox.critical(
                self,
                "Journal",
                str(exc),
            )
            return

        self._current_report = report

        self._start_date.setText(
            start_date.strftime("%d.%m.%Y")
        )

        self._end_date.setText(
            end_date.strftime("%d.%m.%Y")
        )

        self._table.setRowCount(
            len(report.lines)
        )

        for table_row, line in enumerate(
            report.lines
        ):
            values = (
                str(line.booking_number),
                line.booking_date.strftime(
                    "%d.%m.%Y"
                ),
                line.voucher_no,
                line.description,
                line.account_number,
                self._account_names.get(
                    line.account_number,
                    "Unbekanntes Konto",
                ),
                (
                    "S"
                    if line.side is EntrySide.DEBIT
                    else "H"
                ),
                self._format_amount(
                    line.amount
                ),
            )

            for column, value in enumerate(values):
                item = QTableWidgetItem(
                    str(value)
                )

                if column in (0, 7):
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignRight
                        | Qt.AlignmentFlag.AlignVCenter
                    )

                elif column == 6:
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignCenter
                        | Qt.AlignmentFlag.AlignVCenter
                    )

                self._table.setItem(
                    table_row,
                    column,
                    item,
                )

    @staticmethod
    def _normalize_date(
        entry: QLineEdit,
    ) -> None:
        value = entry.text().strip()

        if not value:
            return

        try:
            normalized = normalize_german_date(
                value
            )
        except ValueError:
            return

        entry.setText(normalized)

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

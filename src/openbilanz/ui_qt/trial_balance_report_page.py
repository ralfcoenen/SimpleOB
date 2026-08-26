"""Summen- und Saldenliste der PySide6-Oberfläche."""

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

from openbilanz.reporting.trial_balance_report import (
    TrialBalanceReport,
)
from openbilanz.ui.date_input import (
    normalize_german_date,
    parse_german_date,
)


class TrialBalanceReportPage(QWidget):
    """Zeigt die Summen- und Saldenliste."""

    def __init__(
        self,
        *,
        fiscal_year_start: date,
        fiscal_year_end: date,
        account_names: dict[str, str],
        build_report: Callable[
            [date, date],
            TrialBalanceReport,
        ],
        on_export_pdf=None,
    ) -> None:
        super().__init__()

        self._build_report = build_report
        self._account_names = account_names
        self._current_report: TrialBalanceReport | None = None

        layout = QVBoxLayout(self)

        title = QLabel("Summen- und Saldenliste")
        font = title.font()
        font.setPointSize(16)
        font.setBold(True)
        title.setFont(font)

        layout.addWidget(title)

        description = QLabel(
            "Auswertung der Kontenbewegungen "
            "vor Jahresabschlussbuchungen."
        )
        layout.addWidget(description)

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
                "Konto",
                "Bezeichnung",
                "Anfang Soll",
                "Anfang Haben",
                "Soll-Umsatz",
                "Haben-Umsatz",
                "Endsaldo Soll",
                "Endsaldo Haben",
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

        for column in range(2, 8):
            header.setSectionResizeMode(
                column,
                QHeaderView.ResizeMode.ResizeToContents,
            )

        layout.addWidget(self._table, 1)

        self._totals = QLabel()
        self._totals.setAlignment(
            Qt.AlignmentFlag.AlignRight
        )

        layout.addWidget(self._totals)

    @property
    def current_report(
        self,
    ) -> TrialBalanceReport | None:
        return self._current_report

    def refresh_report(self) -> None:
        """Erzeugt die Auswertung für den gewählten Zeitraum."""

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
                "Summen- und Saldenliste",
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
            len(report.rows)
        )

        for table_row, row in enumerate(report.rows):
            values = (
                row.account_number,
                self._account_names.get(
                    row.account_number,
                    "Unbekanntes Konto",
                ),
                self._format_amount(row.opening_debit),
                self._format_amount(row.opening_credit),
                self._format_amount(row.debit_turnover),
                self._format_amount(row.credit_turnover),
                self._format_amount(row.closing_debit),
                self._format_amount(row.closing_credit),
            )

            for column, value in enumerate(values):
                item = QTableWidgetItem(value)

                if column >= 2:
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
            f"Anfang Soll "
            f"{self._format_amount(report.opening_debit_total)} · "
            f"Anfang Haben "
            f"{self._format_amount(report.opening_credit_total)} · "
            f"Soll-Umsatz "
            f"{self._format_amount(report.debit_turnover_total)} · "
            f"Haben-Umsatz "
            f"{self._format_amount(report.credit_turnover_total)} · "
            f"Endsaldo Soll "
            f"{self._format_amount(report.closing_debit_total)} · "
            f"Endsaldo Haben "
            f"{self._format_amount(report.closing_credit_total)}"
        )

    def set_account_names(
        self,
        account_names: dict[str, str],
    ) -> None:
        """Ergänzt die Kontobezeichnungen der aktuellen Tabelle."""

        if self._current_report is None:
            return

        for table_row, row in enumerate(
            self._current_report.rows
        ):
            item = QTableWidgetItem(
                account_names.get(
                    row.account_number,
                    "Unbekanntes Konto",
                )
            )

            self._table.setItem(
                table_row,
                1,
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

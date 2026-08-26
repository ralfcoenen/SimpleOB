"""Kontenauswertung der PySide6-Oberfläche."""

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

from openbilanz.reporting.account_activity_report import (
    AccountActivityReport,
)
from openbilanz.ui.date_input import (
    normalize_german_date,
    parse_german_date,
)


class AccountActivityReportPage(QWidget):
    """Zeigt gefilterte Kontenbewegungen."""

    def __init__(
        self,
        *,
        fiscal_year_start: date,
        fiscal_year_end: date,
        account_names: dict[str, str],
        build_report: Callable[
            [str, date, date],
            AccountActivityReport,
        ],
        on_export_pdf=None,
    ) -> None:
        super().__init__()

        self._account_names = account_names
        self._build_report = build_report

        self._current_reports: tuple[
            AccountActivityReport,
            ...,
        ] = ()
        self._current_start_date: date | None = None
        self._current_end_date: date | None = None

        layout = QVBoxLayout(self)

        title = QLabel("Kontenauswertung")
        font = title.font()
        font.setPointSize(16)
        font.setBold(True)
        title.setFont(font)

        layout.addWidget(title)

        layout.addWidget(
            QLabel(
                "Kontenbewegungen mit Zeitraum- "
                "und Kontennummernfilter."
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

        filters.addWidget(QLabel("Konto von"))

        self._from_account = QLineEdit()
        self._from_account.setMaximumWidth(90)
        filters.addWidget(self._from_account)

        filters.addWidget(QLabel("Konto bis"))

        self._to_account = QLineEdit()
        self._to_account.setMaximumWidth(90)
        filters.addWidget(self._to_account)

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
                "Datum",
                "Beleg",
                "Konto",
                "Bezeichnung",
                "Buchungstext",
                "Soll",
                "Haben",
                "Saldo",
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

        for column in (0, 1, 2):
            header.setSectionResizeMode(
                column,
                QHeaderView.ResizeMode.ResizeToContents,
            )

        header.setSectionResizeMode(
            3,
            QHeaderView.ResizeMode.Interactive,
        )
        header.setSectionResizeMode(
            4,
            QHeaderView.ResizeMode.Interactive,
        )

        for column in (5, 6, 7):
            header.setSectionResizeMode(
                column,
                QHeaderView.ResizeMode.ResizeToContents,
            )

        layout.addWidget(
            self._table,
            1,
        )

    @property
    def current_reports(
        self,
    ) -> tuple[AccountActivityReport, ...]:
        return self._current_reports

    @property
    def current_start_date(
        self,
    ) -> date | None:
        return self._current_start_date

    @property
    def current_end_date(
        self,
    ) -> date | None:
        return self._current_end_date

    def refresh_report(self) -> None:
        """Aktualisiert die gefilterte Kontenauswertung."""

        try:
            start_date = parse_german_date(
                self._start_date.text()
            )
            end_date = parse_german_date(
                self._end_date.text()
            )

            from_account = (
                self._from_account.text().strip()
            )
            to_account = (
                self._to_account.text().strip()
            )

            if not from_account:
                raise ValueError(
                    "Bitte geben Sie mindestens "
                    "'Konto von' ein."
                )

            if not to_account:
                to_account = from_account
                self._to_account.setText(
                    to_account
                )

            if (
                not from_account.isdigit()
                or not to_account.isdigit()
            ):
                raise ValueError(
                    "Die Kontonummern müssen numerisch sein."
                )

            if int(to_account) < int(from_account):
                raise ValueError(
                    "'Konto bis' darf nicht kleiner "
                    "als 'Konto von' sein."
                )

            account_numbers = tuple(
                account_number
                for account_number in self._account_names
                if (
                    int(from_account)
                    <= int(account_number)
                    <= int(to_account)
                )
            )

            reports = tuple(
                self._build_report(
                    account_number,
                    start_date,
                    end_date,
                )
                for account_number in account_numbers
            )

        except ValueError as exc:
            QMessageBox.critical(
                self,
                "Kontenauswertung",
                str(exc),
            )
            return

        self._current_reports = reports
        self._current_start_date = start_date
        self._current_end_date = end_date

        self._start_date.setText(
            start_date.strftime("%d.%m.%Y")
        )
        self._end_date.setText(
            end_date.strftime("%d.%m.%Y")
        )

        row_count = sum(
            len(report.lines)
            for report in reports
        )

        self._table.setRowCount(
            row_count
        )

        table_row = 0

        for report in reports:
            account_name = self._account_names.get(
                report.account_number,
                "Unbekanntes Konto",
            )

            for line in report.lines:
                values = (
                    line.booking_date.strftime(
                        "%d.%m.%Y"
                    ),
                    line.voucher_no,
                    report.account_number,
                    account_name,
                    line.description,
                    self._format_amount(line.debit),
                    self._format_amount(line.credit),
                    self._format_amount(
                        line.running_balance
                    ),
                )

                for column, value in enumerate(values):
                    item = QTableWidgetItem(
                        str(value)
                    )

                    if column >= 5:
                        item.setTextAlignment(
                            Qt.AlignmentFlag.AlignRight
                            | Qt.AlignmentFlag.AlignVCenter
                        )

                    self._table.setItem(
                        table_row,
                        column,
                        item,
                    )

                table_row += 1

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

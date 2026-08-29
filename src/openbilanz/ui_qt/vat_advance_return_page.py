"""Qt-Auswertung für die Umsatzsteuer-Voranmeldung."""

from datetime import date
from typing import Callable

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

from openbilanz.reporting.vat_advance_return import (
    VatAdvanceReturn,
)
from openbilanz.ui.date_input import (
    normalize_german_date,
    parse_german_date,
)


class VatAdvanceReturnPage(QWidget):
    """Zeigt die Umsatzsteuer-Voranmeldung eines Zeitraums."""

    def __init__(
        self,
        *,
        fiscal_year_start: date,
        fiscal_year_end: date,
        build_report: Callable[
            [date, date],
            VatAdvanceReturn,
        ],
    ) -> None:
        super().__init__()

        self._build_report = build_report
        layout = QVBoxLayout(self)



        title = QLabel("Umsatzsteuer-Voranmeldung")
        font = title.font()
        font.setPointSize(16)
        font.setBold(True)
        title.setFont(font)

        layout.addWidget(title)

        description = QLabel(
            "Auswertung der umsatzsteuerlichen Buchungen "
            "für den gewählten Berichtszeitraum."
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

        filters.addStretch()

        layout.addLayout(filters)
        self._table = QTableWidget(0, 3)

        self._table.setHorizontalHeaderLabels(
            (
                "Position",
                "Bemessungsgrundlage",
                "Steuerbetrag",
            )
        )

        self._table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)

        header = self._table.horizontalHeader()

        header.setSectionResizeMode(
            0,
            QHeaderView.ResizeMode.Stretch,
        )

        header.setSectionResizeMode(
            1,
            QHeaderView.ResizeMode.ResizeToContents,
        )

        header.setSectionResizeMode(
            2,
            QHeaderView.ResizeMode.ResizeToContents,
        )

        layout.addWidget(self._table)

        self._total_label = QLabel()
        self._total_label.setAlignment(
            Qt.AlignmentFlag.AlignRight
        )

        total_font = self._total_label.font()
        total_font.setBold(True)
        self._total_label.setFont(total_font)

        layout.addWidget(self._total_label)

        self.refresh_report()

    def refresh_report(self) -> None:
        """Erzeugt und zeigt die USt-VA-Auswertung."""

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
                "Umsatzsteuer-Voranmeldung",
                str(exc),
            )
            return

        self._start_date.setText(
            start_date.strftime("%d.%m.%Y")
        )
        self._end_date.setText(
            end_date.strftime("%d.%m.%Y")
        )
        rows = (
            (
                "Steuerpflichtige Umsätze 19 %",
                report.taxable_turnover_19,
                report.output_tax_19,
            ),
            (
                "Steuerpflichtige Umsätze 7 %",
                report.taxable_turnover_7,
                report.output_tax_7,
            ),
            (
                "Vorsteuer 19 %",
                None,
                report.input_tax_19,
            ),
            (
                "Vorsteuer 7 %",
                None,
                report.input_tax_7,
            ),
        )

        self._table.setRowCount(len(rows))

        for row_index, (
            description,
            taxable_amount,
            tax_amount,
        ) in enumerate(rows):
            description_item = QTableWidgetItem(
                description
            )

            taxable_item = QTableWidgetItem(
                ""
                if taxable_amount is None
                else self._format_amount(
                    taxable_amount
                )
            )

            tax_item = QTableWidgetItem(
                self._format_amount(
                    tax_amount
                )
            )

            taxable_item.setTextAlignment(
                Qt.AlignmentFlag.AlignRight
                | Qt.AlignmentFlag.AlignVCenter
            )

            tax_item.setTextAlignment(
                Qt.AlignmentFlag.AlignRight
                | Qt.AlignmentFlag.AlignVCenter
            )

            self._table.setItem(
                row_index,
                0,
                description_item,
            )
            self._table.setItem(
                row_index,
                1,
                taxable_item,
            )
            self._table.setItem(
                row_index,
                2,
                tax_item,
            )

        self._total_label.setText(
            "Zahllast: "
            f"{self._format_amount(report.vat_payable)}"
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
        amount,
    ) -> str:
        formatted = f"{amount:,.2f}"

        return (
            formatted
            .replace(",", "X")
            .replace(".", ",")
            .replace("X", ".")
            + " €"
        )

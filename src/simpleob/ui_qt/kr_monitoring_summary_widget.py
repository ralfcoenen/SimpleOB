"""Informative Kleinunternehmer-Umsatzanzeige."""

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGridLayout, QGroupBox, QLabel, QWidget

from simpleob.amount_input import format_german_amount
from simpleob.domain.kr_monitoring import KrMonitoringSummary


class KrMonitoringSummaryWidget(QGroupBox):
    """Zeigt die vorhandene, ausdrücklich informative KR-Umsatzüberwachung."""

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        summary_provider: Callable[[], KrMonitoringSummary] | None = None,
    ) -> None:
        super().__init__("Umsatzüberwachung – vereinnahmte Kundenzahlungen", parent)
        self._summary_provider = summary_provider
        grid = QGridLayout(self)
        grid.setContentsMargins(8, 6, 8, 6)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(2)
        grid.addWidget(QLabel("Position"), 0, 0)
        self._kr_previous_year_label = QLabel("Vorjahr")
        self._kr_current_year_label = QLabel("Laufendes Jahr")
        grid.addWidget(self._kr_previous_year_label, 0, 1)
        grid.addWidget(self._kr_current_year_label, 0, 2)
        self._kr_value_labels: dict[str, tuple[QLabel, QLabel]] = {}
        for row, (key, caption) in enumerate(
            (
                ("payments", "Kundenzahlungen"),
                ("refunds", "Kundenrückerstattungen"),
                ("external", "Externe Umsatzergänzung"),
                ("balance", "Saldo inkl. Ergänzung"),
                ("limit", "Umsatzgrenze"),
            ),
            start=1,
        ):
            grid.addWidget(QLabel(caption), row, 0)
            previous = QLabel("–")
            current = QLabel("–")
            previous.setAlignment(Qt.AlignmentFlag.AlignRight)
            current.setAlignment(Qt.AlignmentFlag.AlignRight)
            grid.addWidget(previous, row, 1)
            grid.addWidget(current, row, 2)
            self._kr_value_labels[key] = (previous, current)

        self._kr_direct_revenue_warning = QLabel(
            "Direkte Erlösbuchungen vorhanden. Die Umsatzüberwachung kann unvollständig sein."
        )
        self._kr_direct_revenue_warning.setWordWrap(True)
        self._kr_direct_revenue_warning.setStyleSheet("font-weight: bold;")
        self._kr_direct_revenue_warning.hide()
        grid.addWidget(self._kr_direct_revenue_warning, 6, 0, 1, 3)
        self._kr_activity_start_warning = QLabel(
            "Beginn der Tätigkeit fehlt. Das Gründungsjahr und die passende Umsatzgrenze sind nicht bestimmbar."
        )
        self._kr_activity_start_warning.setWordWrap(True)
        self._kr_activity_start_warning.hide()
        grid.addWidget(self._kr_activity_start_warning, 7, 0, 1, 3)
        self._kr_error_label = QLabel(
            "Die Umsatzüberwachung ist derzeit nicht verfügbar."
        )
        self._kr_error_label.setWordWrap(True)
        self._kr_error_label.hide()
        grid.addWidget(self._kr_error_label, 8, 0, 1, 3)
        self._kr_scope_note = QLabel(
            "Ausgewertet werden ausschließlich OP-zugeordnete Kundenzahlungen und "
            "eindeutig zuordenbare Kundenrückerstattungen. Ausgangsrechnungen müssen "
            "dafür grundsätzlich auf Ziel erfasst werden. Direktverkäufe, Anzahlungen "
            "ohne Rechnung und nicht eindeutig erkennbare Entgeltminderungen fehlen; "
            "die Anzeige ersetzt keine vollständige steuerrechtliche Prüfung."
        )
        self._kr_scope_note.setWordWrap(True)
        grid.addWidget(self._kr_scope_note, 9, 0, 1, 3)
        self.refresh(summary_provider)

    def refresh(
        self,
        summary_provider: Callable[[], KrMonitoringSummary] | None = None,
    ) -> None:
        """Lädt die informative Anzeige über den vorhandenen Provider."""
        if summary_provider is not None:
            self._summary_provider = summary_provider
        if self._summary_provider is None:
            self.hide()
            return
        try:
            summary = self._summary_provider()
        except Exception:
            for labels in self._kr_value_labels.values():
                for label in labels:
                    label.setText("–")
            self._kr_direct_revenue_warning.hide()
            self._kr_activity_start_warning.hide()
            self._kr_error_label.show()
            return
        if not summary.is_visible:
            self.hide()
            return
        self.show()
        self._kr_error_label.hide()
        years = (summary.previous_year, summary.current_year)
        self._kr_previous_year_label.setText(f"Vorjahr {years[0].calendar_year}")
        self._kr_current_year_label.setText(
            f"Laufendes Jahr {years[1].calendar_year}"
        )
        values = {
            "payments": tuple(year.customer_payments for year in years),
            "refunds": tuple(year.customer_refunds for year in years),
            "external": tuple(year.external_turnover for year in years),
            "balance": tuple(year.balance for year in years),
        }
        for key, amounts in values.items():
            for label, amount in zip(
                self._kr_value_labels[key], amounts, strict=True
            ):
                label.setText(f"{format_german_amount(amount)} €")
        for label, year in zip(
            self._kr_value_labels["limit"], years, strict=True
        ):
            label.setText(
                "–" if year.limit is None else f"{format_german_amount(year.limit)} €"
            )
        self._kr_direct_revenue_warning.setVisible(
            summary.has_direct_revenue_bookings
        )
        self._kr_activity_start_warning.setVisible(
            summary.activity_start_date is None
        )

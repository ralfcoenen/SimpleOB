"""Auswertungsbereich der PySide6-Oberfläche."""

from PySide6.QtWidgets import (
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from openbilanz.ui_qt.trial_balance_report_page import (
    TrialBalanceReportPage,
)


class ReportsPage(QWidget):
    """Container für die OpenBilanz-Auswertungen."""

    def __init__(
        self,
        *,
        trial_balance_page: TrialBalanceReportPage,
    ) -> None:
        super().__init__()

        layout = QVBoxLayout(self)

        self._tabs = QTabWidget()

        self._tabs.addTab(
            trial_balance_page,
            "Summen- und Saldenliste",
        )

        self._tabs.addTab(
            QWidget(),
            "Kontenauswertung",
        )

        self._tabs.addTab(
            QWidget(),
            "Journal",
        )

        layout.addWidget(self._tabs)

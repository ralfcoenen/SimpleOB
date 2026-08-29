"""Auswertungsbereich der PySide6-Oberfläche."""

from PySide6.QtWidgets import (
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from openbilanz.ui_qt.account_activity_report_page import (
    AccountActivityReportPage,
)
from openbilanz.ui_qt.fixed_asset_report_page import (
    FixedAssetReportPage,
)
from openbilanz.ui_qt.journal_report_page import (
    JournalReportPage,
)
from openbilanz.ui_qt.trial_balance_report_page import (
    TrialBalanceReportPage,
)
from openbilanz.ui_qt.vat_advance_return_page import (
    VatAdvanceReturnPage,
)


class ReportsPage(QWidget):
    """Container für die OpenBilanz-Auswertungen."""

    def __init__(
        self,
        *,
        trial_balance_page: TrialBalanceReportPage,
        account_activity_page: AccountActivityReportPage,
        journal_report_page: JournalReportPage,
        fixed_asset_report_page: FixedAssetReportPage,
        vat_advance_return_page: VatAdvanceReturnPage,
    ) -> None:
        super().__init__()

        layout = QVBoxLayout(self)

        self._tabs = QTabWidget()

        self._tabs.addTab(
            trial_balance_page,
            "Summen- und Saldenliste",
        )

        self._tabs.addTab(
            account_activity_page,
            "Kontenauswertung",
        )

        self._tabs.addTab(
            journal_report_page,
            "Journal",
        )

        self._tabs.addTab(
            fixed_asset_report_page,
            "Anlagen",
        )

        self._tabs.addTab(
            vat_advance_return_page,
            "USt-VA",
        )

        layout.addWidget(self._tabs)

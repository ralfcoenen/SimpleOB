from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

from PySide6.QtCore import QItemSelectionModel
from PySide6.QtWidgets import QApplication, QTableWidget

from simpleob.accounting.ledger import Ledger
from simpleob.domain.account import Account
from simpleob.domain.account_type import AccountType
from simpleob.domain.booking import Booking
from simpleob.domain.booking_line import BookingLine
from simpleob.domain.business_partner import BusinessPartner
from simpleob.domain.entry_side import EntrySide
from simpleob.domain.fiscal_year import FiscalYear
from simpleob.domain.journal import Journal
from simpleob.domain.person_account import PersonAccount
from simpleob.domain.person_account_role import PersonAccountRole
from simpleob.domain.template_account import TemplateAccount
from simpleob.services.reporting_service import ReportingService
from simpleob.ui_qt.main_window import MainWindow
from simpleob.ui_qt.person_account_reports_widget import (
    PersonAccountReportsWidget,
)

_APP = QApplication.instance() or QApplication([])


def _creditor(company_id):
    partner = BusinessPartner(
        company_id=company_id,
        name="Muster GmbH",
        is_customer=True,
        is_supplier=True,
    )
    account = Account(
        TemplateAccount("70000", "Diverse Kreditoren", AccountType.LIABILITY),
        person_account_role=PersonAccountRole.KREDITOR,
    )
    return PersonAccount(account, partner, PersonAccountRole.KREDITOR)


class _ReportingWorkspace:
    def __init__(self, *, journal, fiscal_year, company_id, person_account):
        self.journal = journal
        self.fiscal_year = fiscal_year
        self.company_id = company_id
        self.person_account = person_account
        self.service = ReportingService()
        self.managed_fiscal_year = SimpleNamespace(has_opening_source=False)

    def build_person_account_summary(self, **kwargs):
        return self.service.person_account_summary(
            ledger=Ledger(),
            journal=self.journal,
            fiscal_year=self.fiscal_year,
            company_id=self.company_id,
            **kwargs,
        )

    def build_person_account_statement(self, **kwargs):
        return self.service.person_account_statement(
            journal=self.journal,
            fiscal_year=self.fiscal_year,
            company_id=self.company_id,
            has_opening_source=False,
            **kwargs,
        )


def _booking(day, amount, description):
    return Booking(
        booking_date=day,
        description=description,
        lines=(
            BookingLine("70000", EntrySide.DEBIT, amount),
            BookingLine("9000", EntrySide.CREDIT, amount),
        ),
    )


def test_refresh_updates_both_person_account_views_and_preserves_selection_period():
    company_id = uuid4()
    fiscal_year = FiscalYear(date(2025, 1, 1), date(2025, 12, 31))
    creditor = _creditor(company_id)
    journal = Journal()
    workspace = _ReportingWorkspace(
        journal=journal,
        fiscal_year=fiscal_year,
        company_id=company_id,
        person_account=creditor,
    )
    widget = PersonAccountReportsWidget(
        context=SimpleNamespace(
            fiscal_year=fiscal_year,
            company=SimpleNamespace(name="EG Consulting UG"),
        ),
        workspace=workspace,
        person_accounts=(creditor,),
        opening_balance_account_number="9000",
    )
    assert widget._overview_table.rowCount() == 1, widget._totals_label.text()
    widget._start_date.setText("01.06.2025")
    assert widget._overview_table.rowCount() == 1
    widget._overview_table.selectionModel().select(
        widget._overview_table.model().index(0, 0),
        QItemSelectionModel.SelectionFlag.Select
        | QItemSelectionModel.SelectionFlag.Rows,
    )
    assert widget._overview_table.selectionModel().selectedRows()[0].row() == 0

    journal.add(_booking(date(2025, 6, 16), Decimal("210.78"), "Buchung 1"))
    journal.add(_booking(date(2025, 6, 16), Decimal("292.75"), "Buchung 2"))
    widget.refresh()

    assert widget._start_date.date_value() == date(2025, 6, 1)
    assert widget._end_date.date_value() == fiscal_year.end_date
    assert widget._overview_table.selectionModel().selectedRows()[0].row() == 0
    assert widget._overview_table.item(0, 4).text() == "503,53"
    assert widget._overview_table.item(0, 5).text() == "0,00"
    assert widget._overview_table.item(0, 6).text() == "503,53"
    assert widget._overview_table.item(0, 7).text() == "0,00"
    assert widget._overview_table.item(0, 8).text() == "Soll"
    assert widget._statement_table.rowCount() == 2
    assert widget._statement_table.item(1, 5).text() == "503,53"

    widget.close()


def test_journal_refresh_also_refreshes_person_account_reports():
    reports_widget = Mock()
    window = SimpleNamespace(
        _journal_table=QTableWidget(),
        _accounts=(),
        _workspace=SimpleNamespace(journal=()),
        _reports_widget=reports_widget,
    )

    MainWindow._refresh_journal(window)

    reports_widget.refresh_person_account_reports.assert_called_once_with()


def test_bookkeeping_reload_runs_through_the_shared_journal_refresh():
    master_data = SimpleNamespace(supports_e_bilanz=False)
    window = SimpleNamespace(
        _workspace=SimpleNamespace(
            load_company_master_data=Mock(return_value=master_data),
            reload=Mock(),
            journal=(),
        ),
        _company_master_data=master_data,
        _refresh_accounts=Mock(),
        _refresh_journal=Mock(),
        _refresh_balance_sheet=Mock(),
        _update_editing_state=Mock(),
        _refresh_closing=Mock(),
        _refresh_e_bilanz_availability=Mock(),
        _e_bilanz_frame=SimpleNamespace(clear_bvv_evaluation=Mock()),
        _journal_status=Mock(),
        statusBar=Mock(return_value=SimpleNamespace(showMessage=Mock())),
    )

    MainWindow._reload_bookkeeping_data(window)

    window._workspace.reload.assert_called_once_with()
    window._refresh_journal.assert_called_once_with()

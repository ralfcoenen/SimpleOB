from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

from PySide6.QtWidgets import QApplication, QDialog, QMainWindow

from simpleob.date_input import GermanDateEdit
from simpleob.domain.company import Company
from simpleob.domain.fiscal_year import FiscalYear
from simpleob.domain.fixed_asset import FixedAsset
from simpleob.domain.vat_accounts import VatAccounts
from simpleob.ui_qt.booking_frame import BookingFrame
from simpleob.ui_qt.fixed_asset_disposal_dialog import FixedAssetDisposalDialog
from simpleob.ui_qt.main_window import MainWindow
from simpleob.ui_qt.new_company_dialog import NewCompanyDialog
from simpleob.ui_qt.new_fiscal_year_dialog import NewFiscalYearDialog
from simpleob.ui_qt.new_fixed_asset_dialog import NewFixedAssetDialog
from simpleob.ui_qt.reports_widget import ReportsWidget
from simpleob.ui_qt.vat_booking_frame import VatBookingFrame


def _app():
    return QApplication.instance() or QApplication([])


def test_accounting_and_fixed_asset_forms_use_central_date_fields():
    app = _app()
    company_id = uuid4()
    company = Company(company_id=company_id, name="Test GmbH")
    fiscal_year = FiscalYear(date(2026, 1, 1), date(2026, 12, 31))

    class CompanyRepository:
        def get_fiscal_years(self, _company_id):
            return ()

    company_dialog = NewCompanyDialog(None, repository=CompanyRepository())
    year_dialog = NewFiscalYearDialog(
        None,
        repository=CompanyRepository(),
        company=company,
    )
    booking_frame = BookingFrame(
        accounts=(),
        equity_contribution_account_numbers=frozenset(),
        on_booking_created=lambda *_args: None,
    )
    vat_frame = VatBookingFrame(
        accounts=(),
        vat_accounts=VatAccounts("1576", "1571", "1776", "1771"),
        on_booking_created=lambda _booking: None,
    )
    reports = ReportsWidget(
        context=SimpleNamespace(fiscal_year=fiscal_year),
        workspace=object(),
        accounts=(),
        opening_balance_account_number="9000",
        pdf_reporting_service=object(),
    )
    asset_dialog = NewFixedAssetDialog(
        company_id=company_id,
        depreciation_expense_account_number="4830",
        asset_account_options=(),
    )
    asset = FixedAsset(
        company_id=company_id,
        asset_code="ANL-001",
        description="Büroausstattung",
        position_code="HGB.266.AKTIVA.A.I.1",
        asset_account_number="0670",
        depreciation_expense_account_number="4830",
        acquisition_date=date(2026, 1, 1),
        acquisition_cost=Decimal("100.00"),
        depreciation_start_date=date(2026, 1, 1),
        useful_life_months=36,
    )
    disposal_dialog = FixedAssetDisposalDialog(None, fixed_asset=asset, accounts=())

    fields = (
        company_dialog._start_date_entry,
        company_dialog._end_date_entry,
        year_dialog._start_date_entry,
        year_dialog._end_date_entry,
        booking_frame._booking_date_entry,
        vat_frame._booking_date_entry,
        vat_frame._due_date_entry,
        reports._trial_balance_start_date,
        reports._trial_balance_end_date,
        reports._account_activity_start_date,
        reports._account_activity_end_date,
        reports._journal_start_date,
        reports._journal_end_date,
        asset_dialog._acquisition_date_entry,
        asset_dialog._depreciation_start_date_entry,
        disposal_dialog._disposal_date_entry,
    )
    assert all(isinstance(field, GermanDateEdit) for field in fields)

    for field in fields:
        field.setText("1.2.2026")
        assert field.date_value() == date(2026, 2, 1)
        assert field.text() == "01.02.2026"

    for widget in (
        company_dialog,
        year_dialog,
        booking_frame,
        vat_frame,
        reports,
        asset_dialog,
        disposal_dialog,
    ):
        widget.close()
    app.processEvents()


def test_main_window_date_prompt_uses_central_field(monkeypatch):
    app = _app()
    owner = QMainWindow()

    def accept_date_dialog(dialog):
        field = dialog.findChild(GermanDateEdit)
        assert field is not None
        field.setText("1.2.2026")
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(QDialog, "exec", accept_date_dialog)
    result = MainWindow._request_german_date(
        owner,
        title="Datum",
        prompt="Buchungsdatum",
        default_date=date(2026, 1, 1),
    )

    assert result == date(2026, 2, 1)
    owner.close()
    app.processEvents()

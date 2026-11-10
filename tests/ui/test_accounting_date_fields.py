from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

from PySide6.QtWidgets import QApplication, QDialog, QMainWindow, QMessageBox

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
    _app()
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


def test_new_company_dialog_defaults_to_standard_and_accepts_custom_csv(
    monkeypatch,
    tmp_path,
):
    app = _app()
    dialog = NewCompanyDialog(None, repository=object())

    assert dialog._chart_box.currentText() == "SimpleOB-Standard"
    assert dialog._selected_chart_path().name == "openbilanz_standard.csv"

    custom_csv = tmp_path / "eigener_kontenrahmen.csv"
    custom_csv.write_text(
        "account_number;name;account_type\n7000;Bank;ASSET\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "simpleob.ui_qt.new_company_dialog.QFileDialog.getOpenFileName",
        lambda *_args, **_kwargs: (str(custom_csv), "CSV"),
    )
    dialog._select_custom_chart()

    assert dialog._selected_chart_path() == custom_csv
    assert dialog._custom_chart_label.text() == str(custom_csv)
    dialog.close()
    app.processEvents()


def test_individual_chart_requires_warning_confirmation(
    monkeypatch,
    tmp_path,
):
    _app()
    dialog = NewCompanyDialog(None, repository=object())
    custom_csv = tmp_path / "individuell.csv"
    custom_csv.write_text(
        "account_number;name;account_type\n7000;Kasse;ASSET\n",
        encoding="utf-8",
    )
    dialog._custom_chart_path = custom_csv
    dialog._company_name_entry.setText("Test UG")
    warning_calls = []

    def decline_warning(*args):
        warning_calls.append(args)
        return QMessageBox.StandardButton.No

    monkeypatch.setattr(
        "simpleob.ui_qt.new_company_dialog.QMessageBox.warning",
        decline_warning,
    )
    dialog._create_company()

    assert len(warning_calls) == 1
    assert "Systemkonten" in warning_calls[0][2]
    assert "Taxonomiezuweisungen" in warning_calls[0][2]
    assert dialog.result is None
    assert dialog.chart_bundle is None
    dialog.close()


def test_individual_chart_with_sidecar_still_opens_configuration_dialog(
    monkeypatch,
    tmp_path,
):
    _app()
    dialog = NewCompanyDialog(None, repository=object())
    custom_csv = tmp_path / "prepared.csv"
    custom_csv.write_text(
        "account_number;name;account_type\n7000;Konto;ASSET\n",
        encoding="utf-8",
    )
    dialog._custom_chart_path = custom_csv
    dialog._company_name_entry.setText("Test UG")
    prepared_bundle = dialog._chart_importer.load(
        dialog._chart_directory / "openbilanz_standard.csv"
    )
    monkeypatch.setattr(
        dialog._chart_importer,
        "load",
        lambda _path: prepared_bundle,
    )
    monkeypatch.setattr(
        "simpleob.ui_qt.new_company_dialog.QMessageBox.warning",
        lambda *_args: QMessageBox.StandardButton.Yes,
    )
    dialog_calls = []

    class AcceptedConfigurationDialog:
        def __init__(self, _parent, **kwargs):
            dialog_calls.append(kwargs)
            self.result = (
                kwargs["control_accounts"],
                kwargs["vat_accounts"],
                kwargs["account_roles"],
            )

        def exec(self):
            return QDialog.DialogCode.Accepted

    monkeypatch.setattr(
        "simpleob.ui_qt.new_company_dialog.AccountConfigurationDialog",
        AcceptedConfigurationDialog,
    )
    dialog._create_company()

    assert len(dialog_calls) == 1
    assert dialog_calls[0]["for_new_company"] is True
    assert dialog.chart_bundle is not None
    assert dialog.result is not None
    dialog.close()


def test_only_exact_standard_chart_path_is_treated_as_standard(tmp_path):
    _app()
    dialog = NewCompanyDialog(None, repository=object())
    assert dialog._is_standard_chart(
        dialog._chart_directory / "openbilanz_standard.csv"
    )

    custom_named_standard = tmp_path / "openbilanz_standard.csv"
    custom_named_standard.write_text("", encoding="utf-8")
    assert not dialog._is_standard_chart(custom_named_standard)
    dialog.close()


def test_standard_chart_creation_does_not_show_individual_warning(monkeypatch):
    _app()
    dialog = NewCompanyDialog(None, repository=object())
    dialog._company_name_entry.setText("Standard UG")

    def unexpected_warning(*_args):
        raise AssertionError("Der Standardkontenrahmen darf nicht warnen.")

    monkeypatch.setattr(
        "simpleob.ui_qt.new_company_dialog.QMessageBox.warning",
        unexpected_warning,
    )
    dialog._create_company()

    assert dialog.result is not None
    assert dialog.uses_standard_chart
    dialog.close()


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

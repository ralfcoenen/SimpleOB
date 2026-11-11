from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from PySide6.QtWidgets import QApplication, QMessageBox

from simpleob import qt_main
from simpleob.core.config import ApplicationConfig
from simpleob.domain.booking_type import BookingType
from simpleob.domain.company import Company
from simpleob.domain.fiscal_year import FiscalYear
from simpleob.domain.fiscal_year_status import FiscalYearStatus
from simpleob.domain.managed_fiscal_year import ManagedFiscalYear
from simpleob.ui_qt.start_dialog import StartDialog


@pytest.fixture
def app():
    application = QApplication.instance()
    if application is None:
        application = QApplication([])
    return application


@pytest.fixture
def config(tmp_path):
    return ApplicationConfig(
        data_dir=tmp_path,
        database_file=tmp_path / "simpleob.db",
        taxonomy_dir=tmp_path / "taxonomy",
        config_file=tmp_path / "config.toml",
    )


def _make_dialog(app, config, *, target_opening_source=None,
                 source_status=FiscalYearStatus.CLOSED,
                 target_bookings=()):
    company = Company(company_id=uuid4(), name="Test UG")
    source_year = FiscalYear(date(2026, 1, 1), date(2026, 12, 31))
    target_year = FiscalYear(date(2027, 1, 1), date(2027, 12, 31))
    repository = MagicMock()
    repository.list_companies.return_value = (company,)
    repository.get_fiscal_years.return_value = (source_year, target_year)
    repository.get_managed_fiscal_years.return_value = (
        ManagedFiscalYear(source_year, source_status),
        ManagedFiscalYear(
            target_year,
            FiscalYearStatus.OPEN,
            opening_source=target_opening_source,
        ),
    )
    booking_repository = MagicMock()
    booking_repository.list_for_fiscal_year.return_value = target_bookings
    dialog = StartDialog(
        repository=repository,
        booking_repository=booking_repository,
        config=config,
    )
    dialog._fiscal_year_box.setCurrentText(target_year.display_name)
    return (
        dialog,
        company,
        source_year,
        target_year,
        repository,
        booking_repository,
    )


def test_existing_open_unopened_fiscal_year_enables_transfer_action(
    app,
    config,
):
    dialog, *_ = _make_dialog(app, config)
    try:
        assert dialog._opening_transfer_button.text() == (
            "Vorjahressalden übernehmen"
        )
        assert dialog._opening_transfer_button.isEnabled()
    finally:
        dialog.close()


@pytest.mark.parametrize(
    ("opening_source", "bookings"),
    (
        (FiscalYear(date(2026, 1, 1), date(2026, 12, 31)), ()),
        (None, (SimpleNamespace(booking_type=BookingType.OPENING),)),
    ),
)
def test_already_opened_fiscal_year_does_not_offer_transfer(
    app,
    config,
    opening_source,
    bookings,
):
    dialog, *_ = _make_dialog(
        app,
        config,
        target_opening_source=opening_source,
        target_bookings=bookings,
    )
    try:
        assert not dialog._opening_transfer_button.isEnabled()
    finally:
        dialog.close()


def test_open_predecessor_does_not_offer_transfer(app, config):
    dialog, *_ = _make_dialog(
        app,
        config,
        source_status=FiscalYearStatus.OPEN,
    )
    try:
        assert not dialog._opening_transfer_button.isEnabled()
    finally:
        dialog.close()


def test_cancelling_transfer_confirmation_creates_no_request_or_booking(
    app,
    config,
    monkeypatch,
):
    dialog, _company, _source, _target, _repository, booking_repository = (
        _make_dialog(app, config)
    )
    accepted = MagicMock()
    monkeypatch.setattr(dialog, "accept", accepted)
    monkeypatch.setattr(
        "simpleob.ui_qt.start_dialog.QMessageBox.question",
        lambda *args: QMessageBox.StandardButton.Cancel,
    )
    try:
        dialog._opening_transfer_button.click()

        assert dialog.opening_transfer_request is None
        accepted.assert_not_called()
        booking_repository.add.assert_not_called()
    finally:
        dialog.close()


def test_confirmed_transfer_sets_existing_workflow_request(
    app,
    config,
    monkeypatch,
):
    dialog, company, source_year, target_year, repository, booking_repository = (
        _make_dialog(app, config)
    )
    accepted = MagicMock()
    opening_workflow = MagicMock()
    monkeypatch.setattr(dialog, "accept", accepted)
    monkeypatch.setattr(
        qt_main,
        "FiscalYearOpeningWorkflow",
        lambda **_kwargs: opening_workflow,
    )
    monkeypatch.setattr(
        "simpleob.ui_qt.start_dialog.QMessageBox.question",
        lambda *args: QMessageBox.StandardButton.Yes,
    )
    try:
        dialog._opening_transfer_button.click()

        assert dialog.opening_transfer_request == (target_year, source_year)
        assert dialog.result.company == company
        assert dialog.result.fiscal_year == target_year
        accepted.assert_called_once()

        qt_main._execute_opening_transfer_request(
            opening_transfer_request=dialog.opening_transfer_request,
            context=dialog.result,
            session=object(),
            booking_repository=booking_repository,
            company_repository=repository,
            posting_service=object(),
            account_types={},
            account_roles=object(),
            chart_of_accounts=object(),
            control_accounts=SimpleNamespace(
                opening_balance_account="9000",
                profit_account="8020",
                loss_account="8021",
                profit_loss_carryforward_account="0860",
            ),
        )

        opening_workflow.open.assert_called_once()
        assert opening_workflow.open.call_args.kwargs[
            "source_fiscal_year"
        ] == source_year
        assert opening_workflow.open.call_args.kwargs[
            "target_fiscal_year"
        ] == target_year
    finally:
        dialog.close()

"""Tests für das Verwaltungsmenü im Hauptfenster."""

from unittest.mock import Mock

from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QMainWindow,
    QTabWidget,
    QWidget,
)

from simpleob.ui_qt.main_window import MainWindow

_APP = QApplication.instance() or QApplication([])


def _window(*, export_available: bool = True) -> tuple[MainWindow, QHBoxLayout]:
    window = MainWindow.__new__(MainWindow)
    QMainWindow.__init__(window)
    window._export_client_transfer = object() if export_available else None
    window._open_company_master_data = Mock()
    window._open_kr_settings = Mock()
    window._open_shareholders = Mock()
    window._open_account_configuration = Mock()
    window._export_company = Mock()
    container = QWidget()
    window._test_container = container
    layout = QHBoxLayout(container)
    window._create_administration_controls(layout)
    return window, layout


def test_administration_actions_include_kr_settings_without_duplicates():
    window, layout = _window()

    assert layout.count() == 1
    assert window._administration_button.text() == "Verwaltung"
    actions = [
        action
        for action in window._administration_menu.actions()
        if not action.isSeparator()
    ]
    labels = [action.text() for action in actions]
    assert labels == [
        "Unternehmensstammdaten…",
        "Kleinunternehmerregelung",
        "Gesellschafter…",
        "Kontenkonfiguration…",
        "Mandant exportieren…",
    ]
    assert len(labels) == len(set(labels))
    assert all(action.isEnabled() for action in actions)

    for action in actions:
        action.trigger()

    window._open_company_master_data.assert_called_once()
    window._open_kr_settings.assert_called_once()
    window._open_shareholders.assert_called_once()
    window._open_account_configuration.assert_called_once()
    window._export_company.assert_called_once()


def test_export_action_remains_disabled_without_transfer_service():
    window, _layout = _window(export_available=False)

    assert not window._export_company_button.isEnabled()
    assert window._company_master_data_button.isEnabled()
    assert window._shareholders_button.isEnabled()
    assert window._account_configuration_button.isEnabled()


def test_administration_actions_are_disabled_in_account_editing_mode(
    monkeypatch,
):
    window, _layout = _window()
    window._account_editing_mode = False
    window._notebook = QTabWidget()
    window._accounts_tab = QWidget()
    other_tab = QWidget()
    window._notebook.addTab(window._accounts_tab, "Konten")
    window._notebook.addTab(other_tab, "Journal")
    window._opening_balance_button = QAction(window)
    window._return_to_start_button = QAction(window)
    window._elster_certificate_action = QAction(window)
    window._elster_data_supplier_action = QAction(window)
    window._e_bilanz_mapping_button = QAction(window)
    monkeypatch.setattr(
        "simpleob.ui_qt.main_window.QMessageBox.information",
        Mock(),
    )

    window._activate_account_editing_mode()

    assert not window._company_master_data_button.isEnabled()
    assert not window._shareholders_button.isEnabled()
    assert not window._account_configuration_button.isEnabled()
    assert not window._export_company_button.isEnabled()
    assert window._return_to_start_button.isEnabled()
    assert window._notebook.isTabEnabled(0)
    assert not window._notebook.isTabEnabled(1)

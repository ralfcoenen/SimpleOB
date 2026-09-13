"""Tests für die Geschäftsjahressteuerung des MainWindow."""
from pathlib import Path
from unittest.mock import Mock, patch
from urllib.error import URLError

from openbilanz.services.taxonomy_management_service import (
    TaxonomyStatus,
)
from openbilanz.taxonomy.taxonomy import TaxonomyVersion
from openbilanz.ui.main_window import MainWindow


def _create_window_double(
    *,
    is_open: bool,
) -> MainWindow:
    """Erzeugt ein MainWindow ohne Tkinter-Fenster."""

    window = object.__new__(MainWindow)

    window._workspace = Mock()
    window._workspace.is_open = is_open
    window._workspace.is_closed = not is_open

    window._opening_balance_button = Mock()
    window._new_account_button = Mock()
    window._edit_account_button = Mock()

    window._add_fixed_asset_button = Mock()
    window._edit_fixed_asset_button = Mock()
    window._delete_fixed_asset_button = Mock()
    window._link_fixed_asset_acquisition_button = Mock()
    window._link_fixed_asset_disposal_button = Mock()
    window._process_depreciations_button = Mock()
    window._tax_depreciation_adjustments_button = Mock()

    window._booking_frame = Mock()
    window._vat_booking_frame = Mock()
    window._booking_mode_box = Mock()

    return window

def _create_taxonomy_window_double(
    *,
    installed: bool,
    complete: bool,
) -> MainWindow:
    """Erzeugt ein MainWindow für Taxonomiestatus-Tests."""

    window = object.__new__(MainWindow)

    window._workspace = Mock()
    window._workspace.taxonomy_status = TaxonomyStatus(
        required_version=TaxonomyVersion.V6_9,
        installed=installed,
        complete=complete,
    )
    window._install_taxonomy_button = Mock()
    window._taxonomy_status = Mock()

    return window

def test_open_fiscal_year_enables_editing() -> None:
    window = _create_window_double(
        is_open=True
    )

    window._update_editing_state()

    window._add_fixed_asset_button.state.assert_called_once_with(
        ["!disabled"]
    )

    window._process_depreciations_button.state.assert_called_once_with(
        ["!disabled"]
    )

    window._booking_frame.set_enabled.assert_called_once_with(
        True
    )
    window._vat_booking_frame.set_enabled.assert_called_once_with(
        True
    )

    window._booking_mode_box.configure.assert_called_once_with(
        state="readonly"
    )


def test_closed_fiscal_year_disables_editing() -> None:
    window = _create_window_double(
        is_open=False
    )

    window._update_editing_state()

    window._add_fixed_asset_button.state.assert_called_once_with(
        ["disabled"]
    )

    window._process_depreciations_button.state.assert_called_once_with(
        ["disabled"]
    )

    window._booking_frame.set_enabled.assert_called_once_with(
        False
    )
    window._vat_booking_frame.set_enabled.assert_called_once_with(
        False
    )

    window._booking_mode_box.configure.assert_called_once_with(
        state="disabled"
    )


def test_taxonomy_status_reports_complete_installation() -> None:
    window = _create_taxonomy_window_double(
        installed=True,
        complete=True,
    )

    window._refresh_taxonomy_status()

    window._taxonomy_status.config.assert_called_once_with(
        text=(
            "Benötigte Taxonomie: 6.9\n"
            "Status: installiert und vollständig"
        ),
    )


def test_taxonomy_status_reports_incomplete_installation() -> None:
    window = _create_taxonomy_window_double(
        installed=True,
        complete=False,
    )

    window._refresh_taxonomy_status()

    window._taxonomy_status.config.assert_called_once_with(
        text=(
            "Benötigte Taxonomie: 6.9\n"
            "Status: installiert, aber unvollständig"
        ),
    )


def test_taxonomy_status_reports_missing_installation() -> None:
    window = _create_taxonomy_window_double(
        installed=False,
        complete=False,
    )

    window._refresh_taxonomy_status()

    window._taxonomy_status.config.assert_called_once_with(
        text=(
            "Benötigte Taxonomie: 6.9\n"
            "Status: nicht installiert"
        ),
    )

def _create_e_bilanz_window_double(
    *,
    taxonomy_usable: bool,
) -> MainWindow:
    """Erzeugt ein MainWindow für E-Bilanz-Zustandstests."""

    window = object.__new__(MainWindow)

    window._workspace = Mock()
    window._workspace.is_closed = True
    window._workspace.taxonomy_status = TaxonomyStatus(
        required_version=TaxonomyVersion.V6_9,
        installed=taxonomy_usable,
        complete=taxonomy_usable,
    )

    window._current_e_bilanz_preparation = Mock()
    window._current_e_bilanz_preparation.balance_sheet_amounts = {}
    window._current_e_bilanz_preparation.income_statement_amounts = {}
    window._current_e_bilanz_document = None
    window._current_e_bilanz_arelle_valid = False

    window._elster_bilanz_transmission_service = None

    window._e_bilanz_status = Mock()
    window._prepare_e_bilanz_button = Mock()
    window._build_e_bilanz_button = Mock()
    window._validate_e_bilanz_button = Mock()
    window._export_e_bilanz_button = Mock()
    window._send_e_bilanz_test_button = Mock()

    return window

def test_e_bilanz_build_is_enabled_for_usable_taxonomy() -> None:
    window = _create_e_bilanz_window_double(
        taxonomy_usable=True,
    )

    window._refresh_e_bilanz()

    window._build_e_bilanz_button.config.assert_any_call(
        state="normal"
    )


def test_e_bilanz_build_is_disabled_for_unusable_taxonomy() -> None:
    window = _create_e_bilanz_window_double(
        taxonomy_usable=False,
    )

    window._refresh_e_bilanz()

    window._build_e_bilanz_button.config.assert_any_call(
        state="disabled"
    )


def test_e_bilanz_status_explains_unusable_taxonomy() -> None:
    window = _create_e_bilanz_window_double(
        taxonomy_usable=False,
    )

    window._refresh_e_bilanz()

    window._e_bilanz_status.config.assert_called_with(
        text=(
            "Die E-Bilanz wurde vorbereitet.\n"
            "Bilanzpositionen: 0\n"
            "GuV-Positionen: 0\n\n"
            "Die benötigte Taxonomie ist nicht "
            "vollständig installiert."
        ),
    )

def test_taxonomy_install_button_is_disabled_when_taxonomy_is_usable() -> None:
    window = _create_taxonomy_window_double(
        installed=True,
        complete=True,
    )

    window._refresh_taxonomy_status()

    window._install_taxonomy_button.config.assert_called_once_with(
        state="disabled"
    )


def test_taxonomy_install_button_is_enabled_when_taxonomy_is_unusable() -> None:
    window = _create_taxonomy_window_double(
        installed=False,
        complete=False,
    )

    window._refresh_taxonomy_status()

    window._install_taxonomy_button.config.assert_called_once_with(
        state="normal"
    )

def test_installs_required_taxonomy_and_refreshes_state() -> None:
    window = object.__new__(MainWindow)

    window._workspace = Mock()
    window._refresh_taxonomy_status = Mock()
    window._refresh_e_bilanz = Mock()

    with patch(
        "openbilanz.ui.main_window.messagebox.showinfo"
    ):
        window._install_required_taxonomy()

    window._workspace.install_required_taxonomy.assert_called_once_with()

    window._refresh_taxonomy_status.assert_called_once_with()
    window._refresh_e_bilanz.assert_called_once_with()


def test_taxonomy_installation_reports_download_error() -> None:
    window = object.__new__(MainWindow)

    window._workspace = Mock()
    window._workspace.install_required_taxonomy.side_effect = (
        URLError("Download fehlgeschlagen")
    )

    window._refresh_taxonomy_status = Mock()
    window._refresh_e_bilanz = Mock()

    with patch(
        "openbilanz.ui.main_window.messagebox.showerror"
    ) as showerror:
        window._install_required_taxonomy()

    showerror.assert_called_once()

    window._refresh_taxonomy_status.assert_not_called()
    window._refresh_e_bilanz.assert_not_called()

def test_taxonomy_installation_reports_success() -> None:
    window = object.__new__(MainWindow)

    window._workspace = Mock()
    window._refresh_taxonomy_status = Mock()
    window._refresh_e_bilanz = Mock()

    with patch(
        "openbilanz.ui.main_window.messagebox.showinfo"
    ) as showinfo:
        window._install_required_taxonomy()

    showinfo.assert_called_once_with(
        "Taxonomie",
        "Die benötigte Taxonomie wurde erfolgreich installiert.",
        parent=window,
    )

def test_taxonomy_installation_reports_invalid_taxonomy() -> None:
    window = object.__new__(MainWindow)

    window._workspace = Mock()
    window._workspace.install_required_taxonomy.side_effect = (
        ValueError("Taxonomiequelle ist unvollständig.")
    )

    window._refresh_taxonomy_status = Mock()
    window._refresh_e_bilanz = Mock()

    with patch(
        "openbilanz.ui.main_window.messagebox.showerror"
    ) as showerror:
        window._install_required_taxonomy()

    showerror.assert_called_once_with(
        "Taxonomie konnte nicht installiert werden",
        "Taxonomiequelle ist unvollständig.",
        parent=window,
    )

    window._refresh_taxonomy_status.assert_not_called()
    window._refresh_e_bilanz.assert_not_called()

def test_e_bilanz_export_is_disabled_by_refresh() -> None:
    window = _create_e_bilanz_window_double(
        taxonomy_usable=True,
    )

    window._refresh_e_bilanz()

    window._export_e_bilanz_button.config.assert_called_with(
        state="disabled"
    )

def test_successful_e_bilanz_validation_enables_export() -> None:
    window = _create_e_bilanz_window_double(
        taxonomy_usable=True,
    )

    window._current_e_bilanz_document = Mock()

    window._workspace.validate_e_bilanz.return_value = Mock(
        is_valid=True,
        errors=(),
    )

    with patch(
        "openbilanz.ui.main_window.messagebox.showinfo"
    ):
        window._validate_e_bilanz()

    assert window._current_e_bilanz_arelle_valid is True

    window._export_e_bilanz_button.config.assert_called_with(
        state="normal"
    )

def test_failed_e_bilanz_validation_disables_export() -> None:
    window = _create_e_bilanz_window_double(
        taxonomy_usable=True,
    )

    window._current_e_bilanz_document = Mock()
    window._current_e_bilanz_arelle_valid = True

    window._workspace.validate_e_bilanz.return_value = Mock(
        is_valid=False,
        errors=("Fehler",),
    )

    with patch(
        "openbilanz.ui.main_window.messagebox.showerror"
    ):
        window._validate_e_bilanz()

    assert window._current_e_bilanz_arelle_valid is False

    window._export_e_bilanz_button.config.assert_called_with(
        state="disabled"
    )

def test_e_bilanz_export_uses_selected_target() -> None:
    window = object.__new__(MainWindow)

    window._workspace = Mock()
    window._current_e_bilanz_document = Mock()

    window._workspace.export_e_bilanz.return_value = (
        Path("/tmp/e-bilanz.xbrl")
    )

    with (
        patch(
            "openbilanz.ui.main_window."
            "filedialog.asksaveasfilename",
            return_value="/tmp/e-bilanz.xbrl",
        ),
        patch(
            "openbilanz.ui.main_window.messagebox.showinfo"
        ),
    ):
        window._export_e_bilanz()

    window._workspace.export_e_bilanz.assert_called_once_with(
        document=window._current_e_bilanz_document,
        target=Path("/tmp/e-bilanz.xbrl"),
    )

def test_e_bilanz_export_cancel_does_not_export() -> None:
    window = object.__new__(MainWindow)

    window._workspace = Mock()
    window._current_e_bilanz_document = Mock()

    with patch(
        "openbilanz.ui.main_window."
        "filedialog.asksaveasfilename",
        return_value="",
    ):
        window._export_e_bilanz()

    window._workspace.export_e_bilanz.assert_not_called()

def test_closing_validation_is_blocked_by_open_depreciations() -> None:
    window = object.__new__(MainWindow)

    window._workspace = Mock()
    window._workspace.build_depreciation_proposals.return_value = (
        Mock(),
    )

    window._current_income_statement = Mock()
    window._current_closing_result = Mock()
    window._current_balance_sheet = Mock()
    window._current_closing_balances = Mock()
    window._account_mapper = Mock()
    window._closing_frame = Mock()

    with patch(
        "openbilanz.ui.main_window.messagebox.showwarning"
    ) as showwarning:
        window._validate_closing()

    window._workspace.validate_closing.assert_not_called()

    showwarning.assert_called_once()

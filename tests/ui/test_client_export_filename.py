"""Der Export schlägt den gemeinsamen Namen vor und respektiert die Auswahl."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from simpleob.ui_qt import main_window as module


@pytest.mark.parametrize(
    "chosen", ["", "Eigene Sicherung", "Eigene Sicherung.simpleob"]
)
def test_export_suggests_shared_name_and_respects_user_choice(
    monkeypatch, tmp_path, chosen
):
    suggested = "SimpleOB-Mandant-Müller-20261018-1407-abcdef123456.simpleob"
    generator = Mock(return_value=suggested)
    monkeypatch.setattr(module, "client_backup_filename", generator)
    selection = str(tmp_path / chosen) if chosen else ""
    dialog = Mock(return_value=(selection, ""))
    monkeypatch.setattr(module.QFileDialog, "getSaveFileName", dialog)
    writer = Mock()
    monkeypatch.setattr(module, "write_client_transfer_archive", writer)
    monkeypatch.setattr(module.QMessageBox, "information", Mock())
    window = SimpleNamespace(
        _context=SimpleNamespace(company=SimpleNamespace(name="Müller")),
        _export_client_transfer=Mock(),
    )
    module.MainWindow._export_company(window)
    generator.assert_called_once_with("Müller")
    assert dialog.call_args.args[2] == suggested
    if chosen:
        expected = tmp_path / (
            chosen if chosen.endswith(".simpleob") else chosen + ".simpleob"
        )
        writer.assert_called_once_with(
            expected, window._export_client_transfer.return_value
        )
    else:
        writer.assert_not_called()
        window._export_client_transfer.assert_not_called()

"""Namensbestätigung, eindeutige Auswahl und Zustandswechsel der Mandantenverwaltung."""

from pathlib import Path
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from PySide6.QtWidgets import QApplication

from openbilanz.core.config import ApplicationConfig
from openbilanz.domain.company import Company
from openbilanz.services.client_deletion_service import ClientDeletionCommitUnknown
from openbilanz.ui_qt import start_dialog as module
from openbilanz.ui_qt.start_dialog import StartDialog


@pytest.fixture
def deletion_dialog(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    config = ApplicationConfig(
        data_dir=tmp_path,
        database_file=tmp_path / "test.db",
        taxonomy_dir=tmp_path / "taxonomy",
        config_file=tmp_path / "config.toml",
    )
    company = Company(company_id=uuid4(), name="Testmandant")
    repository = MagicMock()
    repository.list_companies.return_value = (company,)
    repository.get_fiscal_years.return_value = ()
    callback = MagicMock()
    dialog = StartDialog(repository=repository, config=config, delete_client=callback)
    monkeypatch.setattr(
        module.QFileDialog, "getExistingDirectory", lambda *args: str(tmp_path)
    )
    monkeypatch.setattr(
        module.QInputDialog, "getText", lambda *args: (company.name, True)
    )
    for method in ("warning", "critical", "information"):
        monkeypatch.setattr(module.QMessageBox, method, MagicMock())
    yield dialog, repository, company, callback
    dialog.close()
    assert app is not None


@pytest.mark.parametrize(
    "answer", [("Testmandant", False), ("falsch", True), ("Testmandant ", True)]
)
def test_cancel_or_wrong_name_never_calls_deletion(
    deletion_dialog, monkeypatch, answer
):
    dialog, repository, company, callback = deletion_dialog
    monkeypatch.setattr(module.QInputDialog, "getText", lambda *args: answer)
    dialog._delete_company()
    callback.assert_not_called()


def test_directory_cancel_never_asks_for_confirmation(deletion_dialog, monkeypatch):
    dialog, repository, company, callback = deletion_dialog
    monkeypatch.setattr(module.QFileDialog, "getExistingDirectory", lambda *args: "")
    ask = MagicMock()
    monkeypatch.setattr(module.QInputDialog, "getText", ask)
    dialog._delete_company()
    ask.assert_not_called()
    callback.assert_not_called()


def test_success_shows_same_final_path_and_reloads_empty_list(
    deletion_dialog, monkeypatch
):
    dialog, repository, company, callback = deletion_dialog
    prompts = []

    def confirm(*args):
        prompts.append(args[2])
        return company.name, True

    monkeypatch.setattr(module.QInputDialog, "getText", confirm)
    callback.side_effect = lambda *args: setattr(
        repository.list_companies, "return_value", ()
    )
    dialog._delete_company()
    callback.assert_called_once()
    selected, path = callback.call_args.args
    assert selected.company_id == company.company_id
    assert isinstance(path, Path) and path.suffix == ".simpleob"
    assert str(path) in prompts[0]
    assert str(path) in module.QMessageBox.information.call_args.args[2]
    assert repository.list_companies.call_count == 2
    assert dialog._selected_company() is None
    assert dialog._company_box.count() == 0
    assert not dialog._delete_company_button.isEnabled()
    assert not dialog._open_button.isEnabled()
    assert dialog.result is None


def test_same_names_select_exact_uuid(deletion_dialog):
    dialog, repository, company, callback = deletion_dialog
    second = Company(company_id=uuid4(), name=company.name)
    repository.list_companies.return_value = (company, second)
    dialog._load_companies()
    assert dialog._company_box.count() == 2
    dialog._company_box.setCurrentIndex(1)
    dialog._delete_company()
    assert callback.call_args.args[0].company_id == second.company_id


def test_failure_keeps_selection_and_does_not_claim_success(deletion_dialog):
    dialog, repository, company, callback = deletion_dialog
    callback.side_effect = OSError("Sicherung fehlgeschlagen")
    dialog._delete_company()
    module.QMessageBox.critical.assert_called_once()
    module.QMessageBox.information.assert_not_called()
    assert dialog._selected_company() == company
    assert dialog.isEnabled()


def test_unknown_commit_closes_selection_without_retry_or_success(
    deletion_dialog, monkeypatch, tmp_path
):
    dialog, repository, company, callback = deletion_dialog
    callback.side_effect = ClientDeletionCommitUnknown(tmp_path / "unknown.simpleob")
    reject = MagicMock()
    monkeypatch.setattr(dialog, "reject", reject)
    dialog._delete_company()
    callback.assert_called_once()
    reject.assert_called_once()
    module.QMessageBox.information.assert_not_called()
    assert "unbestimmt" in module.QMessageBox.critical.call_args.args[2]
    assert repository.list_companies.call_count == 1


def test_reload_failure_after_commit_does_not_claim_rollback(
    deletion_dialog, monkeypatch
):
    dialog, repository, company, callback = deletion_dialog
    repository.list_companies.side_effect = OSError("Verbindung verloren")
    reject = MagicMock()
    monkeypatch.setattr(dialog, "reject", reject)
    dialog._delete_company()
    callback.assert_called_once()
    reject.assert_called_once()
    assert "Löschung wurde bestätigt" in module.QMessageBox.critical.call_args.args[2]
    module.QMessageBox.information.assert_not_called()


def test_deletion_uses_shared_filename(deletion_dialog, monkeypatch, tmp_path):
    dialog, repository, company, callback = deletion_dialog
    filename = "SimpleOB-Mandant-Testmandant-20261018-1407-abcdef123456.simpleob"
    generator = MagicMock(return_value=filename)
    monkeypatch.setattr(module, "client_backup_filename", generator)
    dialog._delete_company()
    generator.assert_called_once_with(company.name)
    callback.assert_called_once_with(company, tmp_path / filename)

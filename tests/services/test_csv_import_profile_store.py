"""Globale Profile: Validierung, Identität und atomare Speicherung."""

import json
from dataclasses import replace

import pytest

from simpleob.domain.bank_transaction import BankImportSource
from simpleob.domain.csv_import_profile import (
    CsvColumn,
    CsvStatus,
    qonto_compatibility_profile,
)
from simpleob.services.csv_import_profile_store import (
    CsvImportProfileError,
    CsvImportProfileStore,
)


def test_missing_store_defaults_and_edit_roundtrip(tmp_path):
    store = CsvImportProfileStore(tmp_path / "csv_import_profiles.json")
    (profile,) = store.load()
    assert profile == qonto_compatibility_profile()
    assert not store.path.exists()
    edited = replace(
        profile,
        name="Mein Format",
        columns=replace(profile.columns, reference=CsvColumn("Zweck", False)),
    )
    store.save((edited,))
    (restored,) = store.load()
    assert restored == edited
    assert restored.profile_id == profile.profile_id
    assert restored.import_source == BankImportSource.QONTO_CSV
    assert "bank_account" not in store.path.read_text()


@pytest.mark.parametrize(
    "change",
    [
        {"delimiter": ";;"},
        {"encoding": "not-an-encoding"},
        {"date_format": "%Y"},
        {"thousands_separator": ","},
        {"import_source": "Bad source"},
        {"extra": "unknown"},
        {"profile_id": "not-a-uuid"},
    ],
)
def test_invalid_profile_files_are_not_replaced(tmp_path, change):
    store = CsvImportProfileStore(tmp_path / "profiles.json")
    store.save((qonto_compatibility_profile(),))
    data = json.loads(store.path.read_text())
    data["profiles"][0].update(change)
    store.path.write_text(json.dumps(data))
    before = store.path.read_bytes()
    with pytest.raises(CsvImportProfileError):
        store.load()
    assert store.path.read_bytes() == before


def test_duplicate_ids_json_keys_and_unknown_version_fail(tmp_path):
    store = CsvImportProfileStore(tmp_path / "profiles.json")
    p = qonto_compatibility_profile()
    with pytest.raises(CsvImportProfileError, match="Profil-ID"):
        store.save((p, p))
    for content in (
        '{"schema_version":1,"schema_version":1,"profiles":[]}',
        '{"schema_version":2,"profiles":[]}',
        "{broken",
    ):
        store.path.write_text(content)
        with pytest.raises(CsvImportProfileError):
            store.load()


def test_atomic_save_failure_preserves_previous_profiles(tmp_path, monkeypatch):
    store = CsvImportProfileStore(tmp_path / "profiles.json")
    p = qonto_compatibility_profile()
    store.save((p,))
    before = store.path.read_bytes()

    def fail(*args):
        raise OSError("simulated replace failure")

    monkeypatch.setattr("simpleob.services.csv_import_profile_store.os.replace", fail)
    with pytest.raises(CsvImportProfileError):
        store.save((replace(p, name="Geändert"),))
    assert store.path.read_bytes() == before
    assert list(tmp_path.iterdir()) == [store.path]


def test_model_rejects_ambiguous_columns_and_status():
    p = qonto_compatibility_profile()
    with pytest.raises(ValueError, match="mehrfach"):
        replace(p, columns=replace(p.columns, reference=p.columns.currency))
    with pytest.raises(ValueError, match="Mehrdeutig"):
        CsvStatus(CsvColumn("Status"), (("OK", "ready"), ("ok", "not_settled")))
    with pytest.raises(ValueError):
        BankImportSource(" source ")

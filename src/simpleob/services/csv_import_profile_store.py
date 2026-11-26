"""Validierte, atomare JSON-Speicherung globaler CSV-Importprofile."""

import json
import os
import tempfile
from dataclasses import asdict
from pathlib import Path
from uuid import UUID

from simpleob.core.config import desktop_application_data_dir
from simpleob.domain.bank_transaction import BankImportSource
from simpleob.domain.csv_import_profile import (
    CsvAmount,
    CsvColumn,
    CsvColumns,
    CsvImportProfile,
    CsvStatus,
    qonto_compatibility_profile,
)


class CsvImportProfileError(ValueError):
    """Ungültige oder nicht les-/schreibbare Profilkonfiguration."""


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Doppelter JSON-Schlüssel: {key}")
        result[key] = value
    return result


def _fields(cls, value):
    if not isinstance(value, dict) or set(value) != set(cls.__dataclass_fields__):
        raise ValueError(f"Ungültige Felder für {cls.__name__}.")
    return dict(value)


def _column(value):
    return None if value is None else CsvColumn(**_fields(CsvColumn, value))


def _decode(value):
    data = _fields(CsvImportProfile, value)
    data["profile_id"] = UUID(data["profile_id"])
    data["import_source"] = BankImportSource(data["import_source"])
    data["columns"] = CsvColumns(
        **{
            key: _column(binding)
            for key, binding in _fields(CsvColumns, data["columns"]).items()
        }
    )
    amount = _fields(CsvAmount, data["amount"])
    for key in ("column", "inflow_column", "outflow_column"):
        amount[key] = _column(amount[key])
    data["amount"] = CsvAmount(**amount)
    status = _fields(CsvStatus, data["status"])
    status["column"] = _column(status["column"])
    if not isinstance(status["mapping"], dict):
        raise ValueError("Statusmapping muss ein JSON-Objekt sein.")
    status["mapping"] = tuple(status["mapping"].items())
    data["status"] = CsvStatus(**status)
    return CsvImportProfile(**data)


def _encode(profile):
    data = asdict(profile)
    data["profile_id"] = str(profile.profile_id)
    data["import_source"] = profile.import_source.value
    data["status"]["mapping"] = dict(profile.status.mapping)
    return data


class CsvImportProfileStore:
    """Speichert Profile unabhängig vom Mandanten; Pfad ist für Tests injizierbar."""

    def __init__(self, path: Path | None = None):
        self.path = (
            path
            if path is not None
            else desktop_application_data_dir() / "csv_import_profiles.json"
        )

    def load(self) -> tuple[CsvImportProfile, ...]:
        try:
            try:
                content = self.path.read_text(encoding="utf-8")
            except FileNotFoundError:
                return (qonto_compatibility_profile(),)
            data = json.loads(content, object_pairs_hook=_object)
            if not isinstance(data, dict) or set(data) != {
                "schema_version",
                "profiles",
            }:
                raise ValueError("Ungültige Profildatei.")
            if type(data["schema_version"]) is not int or data["schema_version"] != 1:
                raise ValueError("Unbekannte Profilformatversion.")
            if not isinstance(data["profiles"], list):
                raise ValueError("profiles muss eine Liste sein.")
            profiles = tuple(_decode(p) for p in data["profiles"])
            self._validate(profiles)
            return profiles
        except (OSError, ValueError, TypeError, AttributeError) as exc:
            raise CsvImportProfileError(
                f"Importprofile konnten nicht geladen werden ({self.path}): {exc}"
            ) from exc

    @staticmethod
    def _validate(profiles):
        if not all(isinstance(p, CsvImportProfile) for p in profiles):
            raise ValueError("Ungültiges Profil.")
        ids = [p.profile_id for p in profiles]
        if len(ids) != len(set(ids)):
            raise ValueError("Doppelte Profil-ID.")

    def save(self, profiles: tuple[CsvImportProfile, ...]) -> None:
        temporary = None
        try:
            self._validate(profiles)
            rendered = (
                json.dumps(
                    {"schema_version": 1, "profiles": [_encode(p) for p in profiles]},
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n"
            )
            # Auch die serialisierte Darstellung muss den Ladevertrag erfüllen.
            for profile in json.loads(rendered)["profiles"]:
                _decode(profile)
            self.path.parent.mkdir(parents=True, exist_ok=True)
            descriptor, filename = tempfile.mkstemp(
                prefix=f".{self.path.name}.", suffix=".tmp", dir=self.path.parent
            )
            temporary = Path(filename)
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                stream.write(rendered)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
        except (OSError, ValueError, TypeError, AttributeError) as exc:
            raise CsvImportProfileError(
                f"Importprofile konnten nicht gespeichert werden ({self.path}): {exc}"
            ) from exc
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

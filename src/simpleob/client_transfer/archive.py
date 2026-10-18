"""Dateicontainer für den portablen SimpleOB-Mandantentransfer."""

from __future__ import annotations

import errno
import os
import sys
import tempfile
from pathlib import Path
from zipfile import (
    ZIP_DEFLATED,
    BadZipFile,
    ZipFile,
)

from simpleob.client_transfer.model import (
    ClientTransfer,
)
from simpleob.client_transfer.serialization import (
    client_transfer_from_json,
    client_transfer_to_json,
)

CLIENT_TRANSFER_ARCHIVE_MEMBER = "client.json"


def write_verified_client_backup(path: Path, transfer: ClientTransfer) -> Path:
    """Veröffentlicht ein geprüftes Archiv ohne bestehende Dateien zu ersetzen.

    Der Aufrufer muss einen eindeutigen endgültigen Namen liefern. Bei Fehlern
    bleibt ein bereits veröffentlichter Sicherungsstand bewusst erhalten.
    """
    path = path.absolute()
    fd, temporary_name = tempfile.mkstemp(prefix=".simpleob-", dir=path.parent)
    temporary = Path(temporary_name)
    os.close(fd)
    try:
        write_client_transfer_archive(temporary, transfer)
        with temporary.open("r+b") as file:
            file.flush()
            os.fsync(file.fileno())
            if sys.platform == "darwin":
                import fcntl

                fcntl.fcntl(file.fileno(), fcntl.F_FULLFSYNC)
        if read_client_transfer_archive(temporary) != transfer:
            raise ValueError(
                "Die geschriebene Mandantensicherung weicht vom Export ab."
            )

        # Atomare Veröffentlichung derselben Datei; EEXIST statt Überschreiben.
        # Beide Namen liegen auf demselben Dateisystem. Kein exists/replace-Rennen.
        os.link(temporary, path)
        _sync_backup_directory(path.parent)
        if read_client_transfer_archive(path) != transfer:
            raise ValueError("Die bereitgestellte Mandantensicherung ist fehlerhaft.")
        return path
    finally:
        temporary.unlink(missing_ok=True)


def _sync_backup_directory(directory: Path) -> None:
    """Synchronisiert den Verzeichniseintrag, soweit vom OS unterstützt."""
    if os.name == "nt":
        # Windows stellt über os.open/fsync keine Verzeichnissynchronisation bereit.
        return
    fd = os.open(directory, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        try:
            os.fsync(fd)
        except OSError as exc:
            if exc.errno not in (errno.EINVAL, errno.ENOTSUP):
                raise
    finally:
        os.close(fd)


def write_client_transfer_archive(
    path: str | Path,
    transfer: ClientTransfer,
) -> None:
    """Schreibt einen Mandantentransfer als .simpleob-Datei."""
    archive_path = _normalize_archive_path(path)

    if not isinstance(transfer, ClientTransfer):
        raise TypeError(
            "transfer must be a ClientTransfer"
        )

    json_text = client_transfer_to_json(transfer)

    with ZipFile(
        archive_path,
        mode="w",
        compression=ZIP_DEFLATED,
    ) as archive:
        archive.writestr(
            CLIENT_TRANSFER_ARCHIVE_MEMBER,
            json_text.encode("utf-8"),
        )


def read_client_transfer_archive(
    path: str | Path,
) -> ClientTransfer:
    """Liest und validiert eine .simpleob-Datei."""
    archive_path = _normalize_archive_path(path)

    try:
        with ZipFile(
            archive_path,
            mode="r",
        ) as archive:
            members = archive.infolist()

            if len(members) != 1:
                raise ValueError(
                    "Mandantentransferarchiv muss genau "
                    "eine Datei client.json enthalten."
                )

            member = members[0]

            if (
                member.is_dir()
                or member.filename
                != CLIENT_TRANSFER_ARCHIVE_MEMBER
            ):
                raise ValueError(
                    "Mandantentransferarchiv muss genau "
                    "eine Datei client.json enthalten."
                )

            try:
                json_bytes = archive.read(member)
            except (
                BadZipFile,
                RuntimeError,
            ) as exc:
                raise ValueError(
                    "Mandantentransferarchiv kann nicht "
                    "gelesen werden."
                ) from exc

    except BadZipFile as exc:
        raise ValueError(
            "Datei ist kein gültiges "
            "Mandantentransferarchiv."
        ) from exc

    try:
        json_text = json_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(
            "client.json ist nicht gültig UTF-8-kodiert."
        ) from exc

    return client_transfer_from_json(json_text)


def _normalize_archive_path(
    path: str | Path,
) -> Path:
    if isinstance(path, str):
        if not path.strip():
            raise ValueError(
                "path must not be blank"
            )

        return Path(path)

    if isinstance(path, Path):
        return path

    raise TypeError(
        "path must be a string or Path"
    )

"""Dateicontainer für den portablen SimpleOB-Mandantentransfer."""

from __future__ import annotations

from pathlib import Path
from zipfile import (
    BadZipFile,
    ZIP_DEFLATED,
    ZipFile,
)

from openbilanz.client_transfer.model import (
    ClientTransfer,
)
from openbilanz.client_transfer.serialization import (
    client_transfer_from_json,
    client_transfer_to_json,
)

CLIENT_TRANSFER_ARCHIVE_MEMBER = "client.json"


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

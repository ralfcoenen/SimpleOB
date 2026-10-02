"""Tests für den .simpleob-Mandantentransfercontainer."""

from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID
from zipfile import (
    ZIP_DEFLATED,
    ZipFile,
)

import pytest

from openbilanz.client_transfer.archive import (
    CLIENT_TRANSFER_ARCHIVE_MEMBER,
    read_client_transfer_archive,
    write_client_transfer_archive,
)
from openbilanz.client_transfer.model import (
    ClientTransfer,
    ClientTransferAccountRoles,
    ClientTransferApplication,
    ClientTransferClient,
    ClientTransferFormat,
    ClientTransferMasterData,
)


COMPANY_ID = UUID(
    "12345678-1234-5678-1234-567812345678"
)


def _build_transfer() -> ClientTransfer:
    return ClientTransfer(
        format=ClientTransferFormat(),
        application=ClientTransferApplication(
            name="SimpleOB",
            version="0.46.0",
        ),
        exported_at=datetime(
            2026,
            10,
            2,
            20,
            30,
            tzinfo=timezone.utc,
        ),
        client=ClientTransferClient(
            company_id=COMPANY_ID,
            master_data=ClientTransferMasterData(
                name="Test UG",
                legal_form="UG (haftungsbeschränkt)",
            ),
            accounts=(),
            control_accounts=None,
            vat_accounts=None,
            account_roles=ClientTransferAccountRoles(),
        ),
    )


def test_archive_roundtrip(
    tmp_path: Path,
) -> None:
    transfer = _build_transfer()
    archive_path = tmp_path / "mandant.simpleob"

    write_client_transfer_archive(
        archive_path,
        transfer,
    )

    restored = read_client_transfer_archive(
        archive_path
    )

    assert restored == transfer


def test_archive_contains_only_client_json(
    tmp_path: Path,
) -> None:
    archive_path = tmp_path / "mandant.simpleob"

    write_client_transfer_archive(
        archive_path,
        _build_transfer(),
    )

    with ZipFile(archive_path, mode="r") as archive:
        assert archive.namelist() == [
            CLIENT_TRANSFER_ARCHIVE_MEMBER
        ]


def test_invalid_zip_is_rejected(
    tmp_path: Path,
) -> None:
    archive_path = tmp_path / "mandant.simpleob"
    archive_path.write_text(
        "kein ZIP",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="kein gültiges Mandantentransferarchiv",
    ):
        read_client_transfer_archive(
            archive_path
        )


def test_archive_without_client_json_is_rejected(
    tmp_path: Path,
) -> None:
    archive_path = tmp_path / "mandant.simpleob"

    with ZipFile(
        archive_path,
        mode="w",
        compression=ZIP_DEFLATED,
    ) as archive:
        archive.writestr(
            "other.json",
            b"{}",
        )

    with pytest.raises(
        ValueError,
        match="genau eine Datei client.json",
    ):
        read_client_transfer_archive(
            archive_path
        )


def test_archive_with_additional_member_is_rejected(
    tmp_path: Path,
) -> None:
    archive_path = tmp_path / "mandant.simpleob"

    with ZipFile(
        archive_path,
        mode="w",
        compression=ZIP_DEFLATED,
    ) as archive:
        archive.writestr(
            "client.json",
            b"{}",
        )
        archive.writestr(
            "extra.txt",
            b"extra",
        )

    with pytest.raises(
        ValueError,
        match="genau eine Datei client.json",
    ):
        read_client_transfer_archive(
            archive_path
        )


def test_non_utf8_client_json_is_rejected(
    tmp_path: Path,
) -> None:
    archive_path = tmp_path / "mandant.simpleob"

    with ZipFile(
        archive_path,
        mode="w",
        compression=ZIP_DEFLATED,
    ) as archive:
        archive.writestr(
            "client.json",
            b"\xff\xfe\xfa",
        )

    with pytest.raises(
        ValueError,
        match="nicht gültig UTF-8-kodiert",
    ):
        read_client_transfer_archive(
            archive_path
        )

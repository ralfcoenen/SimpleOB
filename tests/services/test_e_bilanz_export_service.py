"""Tests für EBilanzExportService."""

from pathlib import Path

import pytest

from simpleob.services.e_bilanz_export_service import (
    EBilanzExportService,
)
from simpleob.taxonomy.e_bilanz_builder import (
    EBilanzDocument,
)


def _document() -> EBilanzDocument:
    return EBilanzDocument(
        xml='<?xml version="1.0" encoding="utf-8"?><xbrl/>',
        gaap_ci_statement=None,
    )


def test_export_writes_xbrl_document(
    tmp_path: Path,
) -> None:
    service = EBilanzExportService()
    document = _document()

    target = tmp_path / "e-bilanz.xbrl"

    result = service.export(
        document=document,
        target=target,
    )

    assert result == target
    assert target.read_text(
        encoding="utf-8"
    ) == document.xml


def test_export_creates_parent_directory(
    tmp_path: Path,
) -> None:
    service = EBilanzExportService()

    target = (
        tmp_path
        / "export"
        / "e-bilanz.xbrl"
    )

    service.export(
        document=_document(),
        target=target,
    )

    assert target.is_file()


def test_export_rejects_existing_file(
    tmp_path: Path,
) -> None:
    service = EBilanzExportService()

    target = tmp_path / "e-bilanz.xbrl"
    target.write_text(
        "existing",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="Zieldatei existiert bereits",
    ):
        service.export(
            document=_document(),
            target=target,
        )

    assert target.read_text(
        encoding="utf-8"
    ) == "existing"


def test_export_rejects_non_xbrl_extension(
    tmp_path: Path,
) -> None:
    service = EBilanzExportService()

    with pytest.raises(
        ValueError,
        match=r"Dateiendung \.xbrl",
    ):
        service.export(
            document=_document(),
            target=tmp_path / "e-bilanz.xml",
        )


def test_export_rejects_invalid_document(
    tmp_path: Path,
) -> None:
    service = EBilanzExportService()

    with pytest.raises(
        TypeError,
        match="document muss ein EBilanzDocument sein",
    ):
        service.export(
            document=object(),  # type: ignore[arg-type]
            target=tmp_path / "e-bilanz.xbrl",
        )


def test_export_rejects_invalid_target() -> None:
    service = EBilanzExportService()

    with pytest.raises(
        TypeError,
        match="target muss ein Path sein",
    ):
        service.export(
            document=_document(),
            target="e-bilanz.xbrl",  # type: ignore[arg-type]
        )

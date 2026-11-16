"""Tests für die Installation lokaler Taxonomien."""

from pathlib import Path
from urllib.error import URLError
from zipfile import ZipFile

import pytest

from simpleob.taxonomy.taxonomy import (
    TaxonomyVersion,
)
from simpleob.taxonomy.taxonomy_catalog import (
    TaxonomyCatalog,
)
from simpleob.taxonomy.taxonomy_download_catalog import (
    TaxonomyDownloadCatalog,
)
from simpleob.taxonomy.taxonomy_installation_service import (
    TaxonomyInstallationService,
)


def _create_complete_taxonomy(
    root: Path,
    *,
    version: str,
    date_part: str,
) -> Path:
    version_root = root / version

    gcd_root = (
        version_root
        / f"de-gcd-{date_part}"
    )
    gaap_root = (
        version_root
        / f"de-gaap-ci-{date_part}"
    )

    gcd_root.mkdir(parents=True)
    gaap_root.mkdir(parents=True)

    (
        gcd_root
        / f"de-gcd-{date_part}-shell.xsd"
    ).write_text(
        "",
        encoding="utf-8",
    )

    (
        gaap_root
        / f"de-gaap-ci-{date_part}-shell-fiscal.xsd"
    ).write_text(
        "",
        encoding="utf-8",
    )

    return version_root


def test_installs_complete_taxonomy_from_directory(
    tmp_path: Path,
) -> None:
    source_root = tmp_path / "source"
    target_root = tmp_path / "target"

    source = _create_complete_taxonomy(
        source_root,
        version="6.9",
        date_part="2025-04-01",
    )

    service = TaxonomyInstallationService(
        target_root=target_root,
    )

    installed_path = service.install_from_directory(
        version=TaxonomyVersion.V6_9,
        source=source,
    )

    assert installed_path == (
        target_root / "6.9"
    )

    catalog = TaxonomyCatalog(
        root=target_root,
    )

    assert catalog.is_complete(
        TaxonomyVersion.V6_9
    )


def test_rejects_incomplete_taxonomy_source(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source" / "6.9"
    source.mkdir(parents=True)

    target_root = tmp_path / "target"

    service = TaxonomyInstallationService(
        target_root=target_root,
    )

    with pytest.raises(
        ValueError,
        match="Taxonomiequelle ist unvollständig",
    ):
        service.install_from_directory(
            version=TaxonomyVersion.V6_9,
            source=source,
        )

    assert not (
        target_root / "6.9"
    ).exists()

def _create_complete_taxonomy_zip(
    path: Path,
    *,
    date_part: str,
    version: str = "6.9",
) -> None:
    """Erzeugt ein vollständiges Test-Taxonomie-ZIP."""

    with ZipFile(
        path,
        "w",
    ) as archive:
        package_root = (
            f"german-gaap-taxonomy-v{version}-{date_part}/xbrl/"
        )
        archive.writestr(
            (
                f"{package_root}de-gcd-{date_part}/"
                f"de-gcd-{date_part}-shell.xsd"
            ),
            "x",
        )

        archive.writestr(
            (
                f"{package_root}de-gaap-ci-{date_part}/"
                f"de-gaap-ci-{date_part}-shell-fiscal.xsd"
            ),
            "x",
        )


def test_installs_complete_taxonomy_from_zip(
    tmp_path: Path,
) -> None:
    archive = (
        tmp_path
        / "taxonomy.zip"
    )

    _create_complete_taxonomy_zip(
        archive,
        date_part="2025-04-01",
    )

    target_root = (
        tmp_path
        / "target"
    )

    service = TaxonomyInstallationService(
        target_root=target_root,
    )

    metadata = service.inspect_zip(archive)
    assert metadata.version == "6.9"
    assert metadata.release_date == "2025-04-01"

    installed_path = service.install_from_zip(
        version=TaxonomyVersion.V6_9,
        source=archive,
    )

    assert installed_path == (
        target_root
        / "6.9"
    )

    assert (
        installed_path
        / archive.name
    ).is_file()

    catalog = TaxonomyCatalog(
        root=target_root,
    )

    assert catalog.is_complete(
        TaxonomyVersion.V6_9
    )


def test_rejects_local_taxonomy_zip_with_wrong_sha256(
    tmp_path: Path,
) -> None:
    archive = tmp_path / "taxonomy-6.9.zip"
    _create_complete_taxonomy_zip(
        archive,
        date_part="2025-04-01",
    )
    target_root = tmp_path / "target"
    service = TaxonomyInstallationService(target_root=target_root)

    with pytest.raises(ValueError, match="SHA-256-Prüfsumme"):
        service.install_from_zip(
            version=TaxonomyVersion.V6_9,
            source=archive,
            expected_sha256="0" * 64,
        )

    assert not (target_root / "6.9").exists()


def test_rejects_zip_for_different_taxonomy_version(
    tmp_path: Path,
) -> None:
    archive = tmp_path / "taxonomy-6.8.zip"
    _create_complete_taxonomy_zip(
        archive,
        date_part="2024-04-01",
        version="6.8",
    )
    service = TaxonomyInstallationService(
        target_root=tmp_path / "target",
    )

    with pytest.raises(ValueError, match="Paketversion überein"):
        service.install_from_zip(
            version=TaxonomyVersion.V6_9,
            source=archive,
        )

    assert not (tmp_path / "target" / "6.9").exists()


def test_rejects_corrupted_taxonomy_zip(
    tmp_path: Path,
) -> None:
    archive = tmp_path / "taxonomy-6.9-corrupt.zip"
    _create_complete_taxonomy_zip(
        archive,
        date_part="2025-04-01",
    )
    with ZipFile(archive) as zip_file:
        member = zip_file.infolist()[0]
        data_offset = (
            member.header_offset
            + 30
            + len(member.filename.encode("utf-8"))
            + len(member.extra)
        )
    archive_bytes = bytearray(archive.read_bytes())
    archive_bytes[data_offset] ^= 1
    archive.write_bytes(archive_bytes)
    service = TaxonomyInstallationService(
        target_root=tmp_path / "target",
    )

    with pytest.raises(ValueError, match="beschädigt"):
        service.inspect_zip(archive)

    assert not (tmp_path / "target" / "6.9").exists()


def test_rejects_zip_with_unsafe_archive_path(
    tmp_path: Path,
) -> None:
    archive = tmp_path / "taxonomy-6.9-unsafe.zip"
    _create_complete_taxonomy_zip(
        archive,
        date_part="2025-04-01",
    )
    with ZipFile(archive, "a") as zip_file:
        zip_file.writestr(
            "german-gaap-taxonomy-v6.9-2025-04-01/../../outside.txt",
            "outside",
        )

    service = TaxonomyInstallationService(
        target_root=tmp_path / "target",
    )

    with pytest.raises(ValueError, match="unsicheren Pfad"):
        service.install_from_zip(
            version=TaxonomyVersion.V6_9,
            source=archive,
        )

    assert not (tmp_path / "target" / "6.9").exists()


def test_failed_zip_install_leaves_no_partial_target(
    monkeypatch,
    tmp_path: Path,
) -> None:
    archive = tmp_path / "taxonomy-6.9.zip"
    _create_complete_taxonomy_zip(
        archive,
        date_part="2025-04-01",
    )
    target_root = tmp_path / "target"
    service = TaxonomyInstallationService(target_root=target_root)
    monkeypatch.setattr(
        "simpleob.taxonomy.taxonomy_installation_service.copy2",
        lambda *_args: (_ for _ in ()).throw(OSError("disk full")),
    )

    with pytest.raises(OSError, match="disk full"):
        service.install_from_zip(
            version=TaxonomyVersion.V6_9,
            source=archive,
        )

    assert not (target_root / "6.9").exists()
    assert tuple(target_root.iterdir()) == ()


def test_rejects_incomplete_taxonomy_zip(
    tmp_path: Path,
) -> None:
    archive = (
        tmp_path
        / "taxonomy.zip"
    )

    with ZipFile(
        archive,
        "w",
    ) as zip_file:
        zip_file.writestr(
            "readme.txt",
            "unvollständig",
        )

    target_root = (
        tmp_path
        / "target"
    )

    service = TaxonomyInstallationService(
        target_root=target_root,
    )

    with pytest.raises(
        ValueError,
        match="Paketordner|Taxonomieversion konnte nicht",
    ):
        service.install_from_zip(
            version=TaxonomyVersion.V6_9,
            source=archive,
        )

    assert not (
        target_root
        / "6.9"
    ).exists()


def test_does_not_replace_existing_taxonomy_installation(
    tmp_path: Path,
) -> None:
    target_root = tmp_path / "target"
    installed = _create_complete_taxonomy(
        target_root,
        version="6.9",
        date_part="2025-04-01",
    )
    preserved_file = installed / "keep.txt"
    preserved_file.write_text("original", encoding="utf-8")
    archive = tmp_path / "replacement.zip"
    _create_complete_taxonomy_zip(
        archive,
        date_part="2025-04-01",
    )
    service = TaxonomyInstallationService(target_root=target_root)

    with pytest.raises(ValueError, match="bereits installiert"):
        service.install_from_zip(
            version=TaxonomyVersion.V6_9,
            source=archive,
        )

    assert preserved_file.read_text(encoding="utf-8") == "original"
    
def test_installs_taxonomy_from_nested_zip_structure(
    tmp_path: Path,
) -> None:
    archive = (
        tmp_path
        / "taxonomy-6.8.zip"
    )

    with ZipFile(
        archive,
        "w",
    ) as zip_file:
        root = (
            "german-gaap-taxonomy-v6.8-2024-04-01/"
            "xbrl/"
        )

        zip_file.writestr(
            (
                root
                + "de-gcd-2024-04-01/"
                + "de-gcd-2024-04-01-shell.xsd"
            ),
            "",
        )

        zip_file.writestr(
            (
                root
                + "de-gaap-ci-2024-04-01/"
                + "de-gaap-ci-2024-04-01-shell-fiscal.xsd"
            ),
            "",
        )

    target_root = (
        tmp_path
        / "target"
    )

    service = TaxonomyInstallationService(
        target_root=target_root,
    )

    installed_path = service.install_from_zip(
        version=TaxonomyVersion.V6_8,
        source=archive,
    )

    assert installed_path == (
        target_root
        / "6.8"
    )

    catalog = TaxonomyCatalog(
        root=target_root,
    )

    assert catalog.is_complete(
        TaxonomyVersion.V6_8
    )

    assert (
        installed_path
        / archive.name
    ).is_file()


def test_downloads_and_installs_taxonomy(
    tmp_path: Path,
) -> None:
    target_root = (
        tmp_path
        / "target"
    )

    source = TaxonomyDownloadCatalog().source_for(
        TaxonomyVersion.V6_9
    )

    def download(
        url: str,
        destination: Path,
    ) -> None:
        assert url == source.url

        _create_complete_taxonomy_zip(
            destination,
            date_part="2025-04-01",
        )

    service = TaxonomyInstallationService(
        target_root=target_root,
    )

    installed_path = service.install_from_download(
        version=TaxonomyVersion.V6_9,
        download=download,
    )

    assert installed_path == (
        target_root
        / "6.9"
    )

    assert (
        installed_path
        / source.filename
    ).is_file()

    catalog = TaxonomyCatalog(
        root=target_root,
    )

    assert catalog.is_complete(
        TaxonomyVersion.V6_9
    )


def test_does_not_install_when_download_fails(
    tmp_path: Path,
) -> None:
    target_root = (
        tmp_path
        / "target"
    )

    def download(
        url: str,
        destination: Path,
    ) -> None:
        raise URLError(
            "Download fehlgeschlagen"
        )

    service = TaxonomyInstallationService(
        target_root=target_root,
    )

    with pytest.raises(
        URLError,
    ):
        service.install_from_download(
            version=TaxonomyVersion.V6_9,
            download=download,
        )

    assert not (
        target_root
        / "6.9"
    ).exists()


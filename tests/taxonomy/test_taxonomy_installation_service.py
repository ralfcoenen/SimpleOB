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
) -> None:
    """Erzeugt ein vollständiges Test-Taxonomie-ZIP."""

    with ZipFile(
        path,
        "w",
    ) as archive:
        archive.writestr(
            (
                f"de-gcd-{date_part}/"
                f"de-gcd-{date_part}-shell.xsd"
            ),
            "",
        )

        archive.writestr(
            (
                f"de-gaap-ci-{date_part}/"
                f"de-gaap-ci-{date_part}-shell-fiscal.xsd"
            ),
            "",
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
        match="Taxonomiequelle ist unvollständig",
    ):
        service.install_from_zip(
            version=TaxonomyVersion.V6_9,
            source=archive,
        )

    assert not (
        target_root
        / "6.9"
    ).exists()
    
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


"""Tests für den Katalog installierter Taxonomien."""

from pathlib import Path

from openbilanz.taxonomy.taxonomy import (
    TaxonomyVersion,
)
from openbilanz.taxonomy.taxonomy_catalog import (
    TaxonomyCatalog,
)


def _create_complete_taxonomy(
    root: Path,
    *,
    version: str,
    date_part: str,
) -> None:
    version_root = (
        root
        / version
    )

    gcd_root = (
        version_root
        / f"de-gcd-{date_part}"
    )

    gaap_root = (
        version_root
        / f"de-gaap-ci-{date_part}"
    )

    gcd_root.mkdir(
        parents=True,
    )

    gaap_root.mkdir(
        parents=True,
    )

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


def test_returns_no_versions_for_missing_root(
    tmp_path: Path,
) -> None:
    catalog = TaxonomyCatalog(
        root=tmp_path / "missing",
    )

    assert catalog.installed_versions() == ()


def test_detects_installed_taxonomy_version(
    tmp_path: Path,
) -> None:
    (
        tmp_path
        / "6.9"
    ).mkdir()

    catalog = TaxonomyCatalog(
        root=tmp_path,
    )

    assert catalog.installed_versions() == (
        TaxonomyVersion.V6_9,
    )

    assert catalog.is_installed(
        TaxonomyVersion.V6_9
    )


def test_reports_missing_taxonomy_version(
    tmp_path: Path,
) -> None:
    catalog = TaxonomyCatalog(
        root=tmp_path,
    )

    assert not catalog.is_installed(
        TaxonomyVersion.V6_9
    )


def test_complete_taxonomy_is_complete(
    tmp_path: Path,
) -> None:
    _create_complete_taxonomy(
        tmp_path,
        version="6.9",
        date_part="2025-04-01",
    )

    catalog = TaxonomyCatalog(
        root=tmp_path,
    )

    assert catalog.is_complete(
        TaxonomyVersion.V6_9
    )


def test_missing_gcd_entry_point_is_incomplete(
    tmp_path: Path,
) -> None:
    version_root = (
        tmp_path
        / "6.9"
    )

    gaap_root = (
        version_root
        / "de-gaap-ci-2025-04-01"
    )

    gaap_root.mkdir(
        parents=True,
    )

    (
        gaap_root
        / "de-gaap-ci-2025-04-01-shell-fiscal.xsd"
    ).write_text(
        "",
        encoding="utf-8",
    )

    catalog = TaxonomyCatalog(
        root=tmp_path,
    )

    assert not catalog.is_complete(
        TaxonomyVersion.V6_9
    )


def test_missing_gaap_entry_point_is_incomplete(
    tmp_path: Path,
) -> None:
    version_root = (
        tmp_path
        / "6.9"
    )

    gcd_root = (
        version_root
        / "de-gcd-2025-04-01"
    )

    gcd_root.mkdir(
        parents=True,
    )

    (
        gcd_root
        / "de-gcd-2025-04-01-shell.xsd"
    ).write_text(
        "",
        encoding="utf-8",
    )

    catalog = TaxonomyCatalog(
        root=tmp_path,
    )

    assert not catalog.is_complete(
        TaxonomyVersion.V6_9
    )


def test_missing_version_directory_is_incomplete(
    tmp_path: Path,
) -> None:
    catalog = TaxonomyCatalog(
        root=tmp_path,
    )

    assert not catalog.is_complete(
        TaxonomyVersion.V6_9
    )

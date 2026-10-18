"""Tests für die anwendungsweite Taxonomieverwaltung."""
from datetime import date
from pathlib import Path
from unittest.mock import Mock, patch

from simpleob.domain.fiscal_year import FiscalYear
from simpleob.services.taxonomy_management_service import (
    TaxonomyManagementService,
)
from simpleob.taxonomy.taxonomy import (
    TaxonomyVersion,
)
from simpleob.taxonomy.taxonomy_catalog import (
    TaxonomyCatalog,
)
from simpleob.taxonomy.taxonomy_installation_service import (
    TaxonomyInstallationService,
)


def _fiscal_year(
    year: int,
) -> FiscalYear:
    return FiscalYear(
        start_date=date(
            year,
            1,
            1,
        ),
        end_date=date(
            year,
            12,
            31,
        ),
    )


def _create_complete_taxonomy(
    root: Path,
    *,
    version: str,
    date_part: str,
) -> None:
    version_root = root / version

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


def test_reports_required_taxonomy_version(
    tmp_path: Path,
) -> None:
    service = TaxonomyManagementService(
        catalog=TaxonomyCatalog(
            root=tmp_path,
        ),
        installation_service=TaxonomyInstallationService(
            target_root=tmp_path,
        ),
        download=Mock(),
    )

    status = service.status_for(
        _fiscal_year(2026)
    )

    assert (
        status.required_version
        is TaxonomyVersion.V6_9
    )


def test_reports_missing_taxonomy_as_not_usable(
    tmp_path: Path,
) -> None:
    service = TaxonomyManagementService(
        catalog=TaxonomyCatalog(
            root=tmp_path,
        ),
        installation_service=TaxonomyInstallationService(
            target_root=tmp_path,
        ),
        download=Mock(),
    )

    status = service.status_for(
        _fiscal_year(2026)
    )

    assert not status.installed
    assert not status.complete
    assert not status.usable


def test_reports_complete_taxonomy_as_usable(
    tmp_path: Path,
) -> None:
    _create_complete_taxonomy(
        tmp_path,
        version="6.9",
        date_part="2025-04-01",
    )

    service = TaxonomyManagementService(
        catalog=TaxonomyCatalog(
            root=tmp_path,
        ),
        installation_service=TaxonomyInstallationService(
            target_root=tmp_path,
        ),
        download=Mock(),
    )

    status = service.status_for(
        _fiscal_year(2026)
    )

    assert status.installed
    assert status.complete
    assert status.usable


def test_reports_incomplete_taxonomy_as_not_usable(
    tmp_path: Path,
) -> None:
    version_root = tmp_path / "6.9"
    version_root.mkdir()

    service = TaxonomyManagementService(
        catalog=TaxonomyCatalog(
            root=tmp_path,
        ),
        installation_service=TaxonomyInstallationService(
            target_root=tmp_path,
        ),
        download=Mock(),
    )

    status = service.status_for(
        _fiscal_year(2026)
    )

    assert status.installed
    assert not status.complete
    assert not status.usable

def test_installs_required_taxonomy_for_fiscal_year(
    tmp_path: Path,
) -> None:
    installation_service = TaxonomyInstallationService(
        target_root=tmp_path,
    )
    download = Mock()

    service = TaxonomyManagementService(
        catalog=TaxonomyCatalog(
            root=tmp_path,
        ),
        installation_service=installation_service,
        download=download,
    )

    expected_path = tmp_path / "6.9"

    with patch.object(
        installation_service,
        "install_from_download",
        return_value=expected_path,
    ) as install_from_download:
        installed_path = service.install_required_taxonomy(
            _fiscal_year(2026)
        )

    assert installed_path == expected_path

    install_from_download.assert_called_once_with(
        version=TaxonomyVersion.V6_9,
        download=download,
    )

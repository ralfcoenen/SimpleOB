"""Anwendungsservice für den Status der E-Bilanz-Taxonomie."""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from simpleob.domain.fiscal_year import FiscalYear
from simpleob.taxonomy.taxonomy import (
    TaxonomyVersion,
    taxonomy_version_for,
)
from simpleob.taxonomy.taxonomy_catalog import (
    TaxonomyCatalog,
)
from simpleob.taxonomy.taxonomy_installation_service import (
    TaxonomyArchiveMetadata,
    TaxonomyInstallationService,
)

TAXONOMY_6_9_ARCHIVE_NAME = (
    "german-gaap-taxonomy-v6.9-2025-04-01.zip"
)
TAXONOMY_6_9_ARCHIVE_SHA256 = (
    "4c2572b438e7c1b04119d2c6363bc9b07605ddb1a14731dec10a3a0900d7bfc9"
)


@dataclass(frozen=True, slots=True)
class TaxonomyStatus:
    """Beschreibt den Installationszustand einer benötigten Taxonomie."""

    required_version: TaxonomyVersion
    installed: bool
    complete: bool

    @property
    def usable(self) -> bool:
        """Gibt an, ob die Taxonomie verwendet werden kann."""

        return (
            self.installed
            and self.complete
        )


class TaxonomyManagementService:
    """Verwaltet den Taxonomiestatus für ein Geschäftsjahr."""

    def __init__(
        self,
        *,
        catalog: TaxonomyCatalog,
        installation_service: TaxonomyInstallationService,
        download: Callable[[str, Path], None],
        local_archive: Path | None = None,
        local_archive_sha256: str | None = None,
    ) -> None:
        if not isinstance(
            catalog,
            TaxonomyCatalog,
        ):
            raise TypeError(
                "catalog must be a TaxonomyCatalog"
            )

        if not isinstance(
            installation_service,
            TaxonomyInstallationService,
        ):
            raise TypeError(
                "installation_service must be a "
                "TaxonomyInstallationService"
            )

        if not callable(
            download
        ):
            raise TypeError(
                "download must be callable"
            )

        if local_archive is not None and not isinstance(
            local_archive,
            Path,
        ):
            raise TypeError(
                "local_archive must be a Path or None"
            )

        if local_archive_sha256 is not None and not isinstance(
            local_archive_sha256,
            str,
        ):
            raise TypeError(
                "local_archive_sha256 must be a string or None"
            )

        self._catalog = catalog
        self._installation_service = installation_service
        self._download = download
        self._local_archive = local_archive
        self._local_archive_sha256 = local_archive_sha256

    def status_for(
        self,
        fiscal_year: FiscalYear,
    ) -> TaxonomyStatus:
        """Ermittelt den Status der benötigten Taxonomie."""

        if not isinstance(
            fiscal_year,
            FiscalYear,
        ):
            raise TypeError(
                "fiscal_year must be a FiscalYear"
            )

        required_version = taxonomy_version_for(
            fiscal_year
        )

        installed = self._catalog.is_installed(
            required_version
        )

        complete = self._catalog.is_complete(
            required_version
        )

        return TaxonomyStatus(
            required_version=required_version,
            installed=installed,
            complete=complete,
        )

    def install_required_taxonomy(
        self,
        fiscal_year: FiscalYear,
    ) -> Path:
        """Installiert die für das Geschäftsjahr benötigte Taxonomie."""

        if not isinstance(
            fiscal_year,
            FiscalYear,
        ):
            raise TypeError(
                "fiscal_year must be a FiscalYear"
            )

        required_version = taxonomy_version_for(
            fiscal_year
        )

        status = self.status_for(fiscal_year)
        target = (
            self._catalog.root
            / required_version.value
        )

        if status.usable:
            return target

        if status.installed:
            raise ValueError(
                f"Taxonomie {required_version.value} ist bereits vorhanden, "
                "aber unvollständig. Die vorhandene Installation wurde nicht "
                "überschrieben."
            )

        if (
            required_version is TaxonomyVersion.V6_9
            and self._local_archive is not None
        ):
            return self._installation_service.install_from_zip(
                version=required_version,
                source=self._local_archive,
                expected_sha256=self._local_archive_sha256,
            )

        return self._installation_service.install_from_download(
            version=required_version,
            download=self._download,
        )

    def inspect_taxonomy_archive(
        self,
        source: Path,
    ) -> TaxonomyArchiveMetadata:
        """Prüft ein manuell ausgewähltes Taxonomiearchiv ohne Installation."""

        return self._installation_service.inspect_zip(source)

    def taxonomy_6_9_installed(self) -> bool:
        """Meldet, ob im Ziel bereits ein 6.9-Verzeichnis existiert."""

        return self._catalog.is_installed(TaxonomyVersion.V6_9)

    def install_taxonomy_from_archive(
        self,
        source: Path,
    ) -> Path:
        """Installiert nur ein strukturell erkanntes Taxonomie-6.9-Archiv."""

        return self._installation_service.install_from_zip(
            version=TaxonomyVersion.V6_9,
            source=source,
        )

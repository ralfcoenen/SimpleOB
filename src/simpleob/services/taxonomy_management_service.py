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
    TaxonomyInstallationService,
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

        self._catalog = catalog
        self._installation_service = installation_service
        self._download = download

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

        return self._installation_service.install_from_download(
            version=required_version,
            download=self._download,
        )

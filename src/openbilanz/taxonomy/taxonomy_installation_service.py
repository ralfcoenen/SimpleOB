"""Installation lokal bereitgestellter Taxonomien."""

from collections.abc import Callable
from pathlib import Path
from shutil import copy2, copytree
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from openbilanz.taxonomy.taxonomy import (
    TaxonomyVersion,
)
from openbilanz.taxonomy.taxonomy_catalog import (
    TaxonomyCatalog,
)
from openbilanz.taxonomy.taxonomy_download_catalog import (
    TaxonomyDownloadCatalog,
)


class TaxonomyInstallationService:
    """Installiert Taxonomien in das konfigurierte Zielverzeichnis."""

    def __init__(
        self,
        *,
        target_root: Path,
    ) -> None:
        if not isinstance(
            target_root,
            Path,
        ):
            raise TypeError(
                "target_root must be a Path"
            )

        self._target_root = target_root

    def install_from_directory(
        self,
        *,
        version: TaxonomyVersion,
        source: Path,
    ) -> Path:
        """Installiert eine Taxonomie aus einem vorhandenen Verzeichnis."""

        if not isinstance(
            version,
            TaxonomyVersion,
        ):
            raise TypeError(
                "version must be a TaxonomyVersion"
            )

        if not isinstance(
            source,
            Path,
        ):
            raise TypeError(
                "source must be a Path"
            )

        source_catalog = TaxonomyCatalog(
            root=source.parent,
        )

        if not source_catalog.is_complete(
            version
        ):
            raise ValueError(
                "Taxonomiequelle ist unvollständig."
            )

        self._target_root.mkdir(
            parents=True,
            exist_ok=True,
        )

        target = (
            self._target_root
            / version.value
        )

        if target.exists():
            raise ValueError(
                "Taxonomie ist bereits installiert."
            )

        copytree(
            source,
            target,
        )

        target_catalog = TaxonomyCatalog(
            root=self._target_root,
        )

        if not target_catalog.is_complete(
            version
        ):
            raise RuntimeError(
                "Installierte Taxonomie ist unvollständig."
            )

        return target


    def install_from_zip(
        self,
        *,
        version: TaxonomyVersion,
        source: Path,
    ) -> Path:
        """Installiert eine Taxonomie aus einem ZIP-Archiv."""

        if not isinstance(
            version,
            TaxonomyVersion,
        ):
            raise TypeError(
                "version must be a TaxonomyVersion"
            )

        if not isinstance(
            source,
            Path,
        ):
            raise TypeError(
                "source must be a Path"
            )

        if not source.is_file():
            raise ValueError(
                "Taxonomiequelle wurde nicht gefunden."
            )

        target = (
            self._target_root
            / version.value
        )

        if target.exists():
            raise ValueError(
                "Taxonomie ist bereits installiert."
            )

        with TemporaryDirectory() as temporary_directory:
            temporary_root = Path(
                temporary_directory
            )

            extracted_root = (
                temporary_root
                / version.value
            )

            extracted_root.mkdir(
                parents=True,
            )

            with ZipFile(
                source,
                "r",
            ) as archive:
                archive.extractall(
                    extracted_root
                )

            temporary_catalog = TaxonomyCatalog(
                root=temporary_root,
            )

            if not temporary_catalog.is_complete(
                version
            ):
                raise ValueError(
                    "Taxonomiequelle ist unvollständig."
                )

            self._target_root.mkdir(
                parents=True,
                exist_ok=True,
            )

            copytree(
                extracted_root,
                target,
            )

            copy2(
                source,
                target / source.name,
            )

        target_catalog = TaxonomyCatalog(
            root=self._target_root,
        )

        if not target_catalog.is_complete(
            version
        ):
            raise RuntimeError(
                "Installierte Taxonomie ist unvollständig."
            )

        return target
    
    def install_from_download(
        self,
        *,
        version: TaxonomyVersion,
        download: Callable[
            [str, Path],
            None,
        ],
    ) -> Path:
        """Lädt eine Taxonomie herunter und installiert sie."""

        if not isinstance(
            version,
            TaxonomyVersion,
        ):
            raise TypeError(
                "version must be a TaxonomyVersion"
            )

        if not callable(
            download
        ):
            raise TypeError(
                "download must be callable"
            )

        source = TaxonomyDownloadCatalog().source_for(
            version
        )

        with TemporaryDirectory() as temporary_directory:
            temporary_root = Path(
                temporary_directory
            )

            archive = (
                temporary_root
                / source.filename
            )

            download(
                source.url,
                archive,
            )

            return self.install_from_zip(
                version=version,
                source=archive,
            )
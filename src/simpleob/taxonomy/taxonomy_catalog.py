"""Katalog lokal installierter Taxonomieversionen."""

from pathlib import Path

from simpleob.taxonomy.taxonomy import (
    TaxonomyVersion,
)


class TaxonomyCatalog:
    """Erkennt lokal vorhandene Taxonomieversionen."""

    def __init__(
        self,
        *,
        root: Path,
    ) -> None:
        if not isinstance(
            root,
            Path,
        ):
            raise TypeError(
                "root must be a Path"
            )

        self._root = root

    @property
    def root(self) -> Path:
        """Liefert das Taxonomie-Stammverzeichnis."""

        return self._root

    def installed_versions(
        self,
    ) -> tuple[TaxonomyVersion, ...]:
        """Liefert die lokal vorhandenen unterstützten Versionen."""

        if not self._root.is_dir():
            return ()

        return tuple(
            version
            for version in TaxonomyVersion
            if (
                self._root
                / version.value
            ).is_dir()
        )

    def is_installed(
        self,
        version: TaxonomyVersion,
    ) -> bool:
        """Prüft, ob eine Taxonomieversion lokal vorhanden ist."""

        if not isinstance(
            version,
            TaxonomyVersion,
        ):
            raise TypeError(
                "version must be a TaxonomyVersion"
            )

        return (
            self._root
            / version.value
        ).is_dir()

    def is_complete(
        self,
        version: TaxonomyVersion,
    ) -> bool:
        """Prüft, ob die benötigten Entry-Points vorhanden sind."""

        if not isinstance(
            version,
            TaxonomyVersion,
        ):
            raise TypeError(
                "version must be a TaxonomyVersion"
            )

        version_root = (
            self._root
            / version.value
        )

        if not version_root.is_dir():
            return False

        gcd_matches = tuple(
            version_root.rglob(
                "de-gcd-*-shell.xsd"
            )
        )

        gaap_matches = tuple(
            version_root.rglob(
                "de-gaap-ci-*-shell-fiscal.xsd"
            )
        )

        return (
            len(gcd_matches) == 1
            and len(gaap_matches) == 1
        )
    
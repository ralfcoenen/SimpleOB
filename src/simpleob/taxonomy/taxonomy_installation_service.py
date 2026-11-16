"""Installation lokal bereitgestellter Taxonomien."""

import hashlib
import os
import re
import stat
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from shutil import copy2, copytree
from tempfile import TemporaryDirectory
from zipfile import BadZipFile, ZipFile

from simpleob.taxonomy.taxonomy import (
    TaxonomyVersion,
)
from simpleob.taxonomy.taxonomy_catalog import (
    TaxonomyCatalog,
)
from simpleob.taxonomy.taxonomy_download_catalog import (
    TaxonomyDownloadCatalog,
)


@dataclass(frozen=True, slots=True)
class TaxonomyArchiveMetadata:
    """Aus dem internen Paketaufbau erkannte Taxonomieversion."""

    version: str
    release_date: str


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
        expected_sha256: str | None = None,
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

        if expected_sha256 is not None:
            if (
                len(expected_sha256) != 64
                or any(
                    character not in "0123456789abcdefABCDEF"
                    for character in expected_sha256
                )
            ):
                raise ValueError(
                    "Die erwartete SHA-256-Prüfsumme ist ungültig."
                )
            digest = hashlib.sha256()
            with source.open("rb") as archive_file:
                for chunk in iter(
                    lambda: archive_file.read(1024 * 1024),
                    b"",
                ):
                    digest.update(chunk)
            if digest.hexdigest().casefold() != expected_sha256.casefold():
                raise ValueError(
                    "Die SHA-256-Prüfsumme des Taxonomiearchivs stimmt "
                    "nicht mit der erwarteten Prüfsumme überein."
                )

        target = (
            self._target_root
            / version.value
        )

        try:
            with ZipFile(source, "r") as archive:
                metadata = self._validate_zip_archive(archive)
                if metadata.version != version.value:
                    raise ValueError(
                        "Die angegebene Taxonomieversion stimmt nicht mit "
                        "der Paketversion überein: erwartet "
                        f"{version.value}, gefunden {metadata.version}."
                    )

                if target.exists():
                    raise ValueError(
                        f"Taxonomie {version.value} ist bereits installiert. "
                        "Die vorhandene Installation wurde nicht verändert."
                    )

                self._target_root.mkdir(
                    parents=True,
                    exist_ok=True,
                )

                with TemporaryDirectory(
                    dir=self._target_root,
                    prefix=".taxonomy-install-",
                ) as temporary_directory:
                    temporary_root = Path(temporary_directory)
                    extracted_root = temporary_root / version.value
                    extracted_root.mkdir()
                    archive.extractall(extracted_root)

                    copy2(source, extracted_root / source.name)
                    temporary_catalog = TaxonomyCatalog(root=temporary_root)
                    if not temporary_catalog.is_complete(version):
                        raise ValueError(
                            "Taxonomiequelle ist unvollständig."
                        )

                    if target.exists():
                        raise ValueError(
                            f"Taxonomie {version.value} wurde während der "
                            "Installation bereits angelegt. Sie wurde nicht "
                            "überschrieben."
                        )

                    os.rename(extracted_root, target)
        except BadZipFile as exc:
            raise ValueError(
                "Das Taxonomie-ZIP ist beschädigt oder unvollständig."
            ) from exc

        return target

    def inspect_zip(
        self,
        source: Path,
    ) -> TaxonomyArchiveMetadata:
        """Prüft ein lokales Archiv und liest Version und Datum aus dem Paket."""

        if not isinstance(source, Path):
            raise TypeError("source must be a Path")
        if not source.is_file():
            raise ValueError("Taxonomiequelle wurde nicht gefunden.")

        try:
            with ZipFile(source, "r") as archive:
                return self._validate_zip_archive(archive)
        except BadZipFile as exc:
            raise ValueError(
                "Die ausgewählte Datei ist kein gültiges Taxonomie-ZIP."
            ) from exc

    @staticmethod
    def _validate_zip_archive(
        archive: ZipFile,
    ) -> TaxonomyArchiveMetadata:
        """Prüft Integrität, Pfade, Version und erforderliche Entry-Points."""

        try:
            damaged_member = archive.testzip()
        except (OSError, RuntimeError, ValueError) as exc:
            raise ValueError(
                f"Das Taxonomiearchiv kann nicht geprüft werden: {exc}"
            ) from exc

        if damaged_member is not None:
            raise ValueError(
                "Das Taxonomiearchiv ist beschädigt: "
                f"{damaged_member}"
            )

        seen_paths: set[str] = set()
        package_roots: set[str] = set()
        for member in archive.infolist():
            filename = member.filename
            path = PurePosixPath(filename)
            normalized = path.as_posix().rstrip("/").casefold()

            if (
                not filename
                or not path.parts
                or "\\" in filename
                or path.is_absolute()
                or ".." in path.parts
                or (path.parts and ":" in path.parts[0])
            ):
                raise ValueError(
                    "Das Taxonomiearchiv enthält einen unsicheren Pfad: "
                    f"{filename}"
                )

            if normalized in seen_paths:
                raise ValueError(
                    "Das Taxonomiearchiv enthält einen doppelten Pfad: "
                    f"{filename}"
                )
            seen_paths.add(normalized)
            package_roots.add(path.parts[0])

            unix_mode = (member.external_attr >> 16) & 0xFFFF
            if stat.S_ISLNK(unix_mode):
                raise ValueError(
                    "Das Taxonomiearchiv enthält einen symbolischen Link: "
                    f"{filename}"
                )

        if len(package_roots) != 1:
            raise ValueError(
                "Das Taxonomiearchiv muss genau einen Paketordner enthalten."
            )

        package_root = next(iter(package_roots))
        package_match = re.fullmatch(
            r"(?:german|germany)-gaap-taxonomy-v(?P<version>\d+\.\d+)"
            r"-(?P<date>\d{4}-\d{2}-\d{2})",
            package_root,
        )
        if package_match is None:
            raise ValueError(
                "Die Taxonomieversion konnte nicht aus dem internen "
                "Paketordner erkannt werden."
            )

        version = package_match.group("version")
        release_date = package_match.group("date")
        required_entry_points = {
            (
                f"{package_root}/xbrl/de-gcd-{release_date}/"
                f"de-gcd-{release_date}-shell.xsd"
            ),
            (
                f"{package_root}/xbrl/de-gaap-ci-{release_date}/"
                f"de-gaap-ci-{release_date}-shell-fiscal.xsd"
            ),
        }
        available_entry_points = {
            member.filename
            for member in archive.infolist()
        }
        if not required_entry_points.issubset(available_entry_points):
            raise ValueError(
                "Das Taxonomiepaket enthält nicht die erforderlichen "
                "GCD- und GAAP-CI-Fiscal-Entry-Points für "
                f"Version {version}."
            )

        return TaxonomyArchiveMetadata(
            version=version,
            release_date=release_date,
        )
    
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

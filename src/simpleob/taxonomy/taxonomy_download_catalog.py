"""Offizielle Downloadquellen unterstützter E-Bilanz-Taxonomien."""

from dataclasses import dataclass

from simpleob.taxonomy.taxonomy import (
    TaxonomyVersion,
)


@dataclass(frozen=True, slots=True)
class TaxonomyDownloadSource:
    """Beschreibt die offizielle Quelle einer Taxonomie."""

    version: TaxonomyVersion
    url: str
    filename: str


_SOURCES = {
    TaxonomyVersion.V6_8: TaxonomyDownloadSource(
        version=TaxonomyVersion.V6_8,
        url=(
            "https://www.esteuer.de/download/"
            "taxonomie_20240610/"
            "german-gaap-taxonomy-v6.8-2024-04-01-xbrl.zip"
        ),
        filename=(
            "german-gaap-taxonomy-v6.8-2024-04-01-xbrl.zip"
        ),
    ),
    TaxonomyVersion.V6_9: TaxonomyDownloadSource(
        version=TaxonomyVersion.V6_9,
        url=(
            "https://www.esteuer.de/download/"
            "taxonomie_20250618/"
            "german-gaap-taxonomy-v6.9-2025-04-01-xbrl.zip"
        ),
        filename=(
            "german-gaap-taxonomy-v6.9-2025-04-01-xbrl.zip"
        ),
    ),
    TaxonomyVersion.V6_10: TaxonomyDownloadSource(
        version=TaxonomyVersion.V6_10,
        url=(
            "https://www.esteuer.de/download/"
            "taxonomie_20260615/"
            "germany-gaap-taxonomy-v6.10-2026-04-01-xbrl.zip"
        ),
        filename=(
            "germany-gaap-taxonomy-v6.10-2026-04-01-xbrl.zip"
        ),
    ),
}


class TaxonomyDownloadCatalog:
    """Liefert die offiziellen Quellen unterstützter Taxonomien."""

    def source_for(
        self,
        version: TaxonomyVersion,
    ) -> TaxonomyDownloadSource:
        """Liefert die Downloadquelle einer Taxonomieversion."""

        if not isinstance(
            version,
            TaxonomyVersion,
        ):
            raise TypeError(
                "version must be a TaxonomyVersion"
            )

        return _SOURCES[version]

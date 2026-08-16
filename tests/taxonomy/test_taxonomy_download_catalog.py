"""Tests für die offiziellen Taxonomie-Downloadquellen."""

from openbilanz.taxonomy.taxonomy import (
    TaxonomyVersion,
)
from openbilanz.taxonomy.taxonomy_download_catalog import (
    TaxonomyDownloadCatalog,
)


def test_returns_download_for_taxonomy_6_8() -> None:
    source = TaxonomyDownloadCatalog().source_for(
        TaxonomyVersion.V6_8
    )

    assert (
        source.filename
        == "german-gaap-taxonomy-v6.8-2024-04-01-xbrl.zip"
    )

    assert source.url == (
        "https://www.esteuer.de/download/"
        "taxonomie_20240610/"
        "german-gaap-taxonomy-v6.8-2024-04-01-xbrl.zip"
    )


def test_returns_download_for_taxonomy_6_9() -> None:
    source = TaxonomyDownloadCatalog().source_for(
        TaxonomyVersion.V6_9
    )

    assert (
        source.filename
        == "german-gaap-taxonomy-v6.9-2025-04-01-xbrl.zip"
    )

    assert source.url == (
        "https://www.esteuer.de/download/"
        "taxonomie_20250618/"
        "german-gaap-taxonomy-v6.9-2025-04-01-xbrl.zip"
    )


def test_returns_download_for_taxonomy_6_10() -> None:
    source = TaxonomyDownloadCatalog().source_for(
        TaxonomyVersion.V6_10
    )

    assert (
        source.filename
        == "germany-gaap-taxonomy-v6.10-2026-04-01-xbrl.zip"
    )

    assert source.url == (
        "https://www.esteuer.de/download/"
        "taxonomie_20260615/"
        "germany-gaap-taxonomy-v6.10-2026-04-01-xbrl.zip"
    )

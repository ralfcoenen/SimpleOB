"""Tests für den Taxonomie-Downloader."""

from pathlib import Path
from unittest.mock import patch

from openbilanz.taxonomy.taxonomy_downloader import (
    TaxonomyDownloader,
)


def test_downloads_file(
    tmp_path: Path,
) -> None:
    destination = (
        tmp_path
        / "taxonomy.zip"
    )

    response = b"ZIP-Inhalt"

    with patch(
        "openbilanz.taxonomy.taxonomy_downloader.urlopen"
    ) as urlopen:
        urlopen.return_value.__enter__.return_value.read.return_value = (
            response
        )

        TaxonomyDownloader().download(
            "https://example.test/taxonomy.zip",
            destination,
        )

    assert destination.read_bytes() == response

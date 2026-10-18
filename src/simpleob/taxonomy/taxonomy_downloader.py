"""Download von Taxonomiearchiven."""

from pathlib import Path
from urllib.request import urlopen


class TaxonomyDownloader:
    """Lädt Taxonomiearchive aus dem Internet."""

    def download(
        self,
        url: str,
        destination: Path,
    ) -> None:
        """Lädt eine Datei in den angegebenen Zielpfad."""

        if not isinstance(
            url,
            str,
        ):
            raise TypeError(
                "url must be a string"
            )

        if not url.strip():
            raise ValueError(
                "url must not be blank"
            )

        if not isinstance(
            destination,
            Path,
        ):
            raise TypeError(
                "destination must be a Path"
            )

        destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with urlopen(
            url,
        ) as response:
            content = response.read()

        destination.write_bytes(
            content
        )

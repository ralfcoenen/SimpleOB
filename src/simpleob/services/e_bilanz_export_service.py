"""Export einer erzeugten E-Bilanz als XBRL-Datei."""

from pathlib import Path

from simpleob.taxonomy.e_bilanz_builder import (
    EBilanzDocument,
)


class EBilanzExportService:
    """Speichert eine erzeugte E-Bilanz als XBRL-Datei."""

    def export(
        self,
        *,
        document: EBilanzDocument,
        target: Path,
    ) -> Path:
        """Exportiert die E-Bilanz in die angegebene XBRL-Datei."""

        if not isinstance(
            document,
            EBilanzDocument,
        ):
            raise TypeError(
                "document muss ein EBilanzDocument sein."
            )

        if not isinstance(
            target,
            Path,
        ):
            raise TypeError(
                "target muss ein Path sein."
            )

        if target.exists():
            raise ValueError(
                "Die Zieldatei existiert bereits."
            )

        if target.suffix.lower() != ".xbrl":
            raise ValueError(
                "Die Zieldatei muss die Dateiendung .xbrl haben."
            )

        target.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        target.write_text(
            document.xml,
            encoding="utf-8",
        )

        return target

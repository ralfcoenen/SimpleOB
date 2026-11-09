"""CSV-Importer für Standard-Konten-Taxonomiezuordnungen."""

import csv
from pathlib import Path


class CsvAccountTaxonomyMappingImporter:
    """Importiert Konten-Taxonomiezuordnungen aus einer CSV-Datei."""

    def load(
        self,
        path: Path,
    ) -> dict[str, str]:
        """Lädt Kontonummern und Taxonomie-Concept-Namen."""

        if not isinstance(path, Path):
            raise TypeError(
                "path must be a Path"
            )

        with path.open(
            mode="r",
            encoding="utf-8",
            newline="",
        ) as csv_file:
            reader = csv.DictReader(
                csv_file,
                delimiter=";",
            )

            if reader.fieldnames != [
                "account_number",
                "concept_name",
            ]:
                raise ValueError(
                    "Ungültige Spalten für "
                    "Konten-Taxonomiezuordnungen."
                )

            mappings: dict[str, str] = {}

            try:
                for row_number, row in enumerate(reader, start=2):
                    if None in row or any(
                        value is None for value in row.values()
                    ):
                        raise ValueError(
                            "Ungültige Konten-Taxonomiezuordnung in Zeile "
                            f"{row_number}: Es fehlen Werte oder Spalten."
                        )

                    account_number = row["account_number"].strip()
                    concept_name = row["concept_name"].strip()

                    if not account_number:
                        raise ValueError(
                            "Konten-Taxonomiezuordnung in Zeile "
                            f"{row_number}: Kontonummer darf nicht leer sein."
                        )

                    if not concept_name:
                        raise ValueError(
                            "Konten-Taxonomiezuordnung in Zeile "
                            f"{row_number}: Taxonomieposition darf nicht leer sein."
                        )

                    if account_number in mappings:
                        raise ValueError(
                            "Doppelte Kontonummer in "
                            "Konten-Taxonomiezuordnungen: "
                            f"{account_number}"
                        )

                    mappings[account_number] = concept_name
            except csv.Error as exc:
                raise ValueError(
                    f"Die Konten-Taxonomie-CSV ist fehlerhaft: {exc}"
                ) from exc

        return mappings

    def save(
        self,
        mappings: dict[str, str],
        path: Path,
    ) -> None:
        """Speichert Taxonomiezuordnungen im vorhandenen CSV-Format."""

        if not isinstance(path, Path):
            raise TypeError("path must be a Path")
        if not isinstance(mappings, dict):
            raise TypeError("mappings must be a dict")

        with path.open("x", encoding="utf-8", newline="") as csv_file:
            writer = csv.DictWriter(
                csv_file,
                fieldnames=("account_number", "concept_name"),
                delimiter=";",
                lineterminator="\n",
            )
            writer.writeheader()
            for account_number, concept_name in sorted(mappings.items()):
                writer.writerow(
                    {
                        "account_number": account_number,
                        "concept_name": concept_name,
                    }
                )

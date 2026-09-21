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

            for row in reader:
                account_number = (
                    row["account_number"].strip()
                )
                concept_name = (
                    row["concept_name"].strip()
                )

                if not account_number:
                    raise ValueError(
                        "account_number must not be empty"
                    )

                if not concept_name:
                    raise ValueError(
                        "concept_name must not be empty"
                    )

                if account_number in mappings:
                    raise ValueError(
                        "Doppelte Kontonummer in "
                        "Konten-Taxonomiezuordnungen: "
                        f"{account_number}"
                    )

                mappings[account_number] = concept_name

        return mappings

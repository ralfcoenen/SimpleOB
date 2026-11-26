"""Fehler beim Einlesen synthetischer Bank-CSV-Dateien."""


class BankCsvImportError(ValueError):
    """Ein oder mehrere CSV-Fehler mit den betroffenen Zeilennummern."""

    def __init__(self, errors: tuple[str, ...]) -> None:
        self.errors = errors
        super().__init__("\n".join(errors))

"""Schnittstelle für den Import von Kontenrahmen."""

from abc import ABC, abstractmethod
from pathlib import Path

from simpleob.domain.chart_of_accounts_template import (
    ChartOfAccountsTemplate,
)


class ChartOfAccountsImporter(ABC):
    """Abstrakte Basisklasse für Kontenrahmen-Importer."""

    @abstractmethod
    def load(
        self,
        path: Path,
    ) -> ChartOfAccountsTemplate:
        """Lädt einen Kontenrahmen aus einer Datei."""
        
        
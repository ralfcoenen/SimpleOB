"""Orchestrierung der Taxonomieauflösung und -ladung."""

from simpleob.domain.fiscal_year import FiscalYear
from simpleob.taxonomy.arelle_adapter import ArelleAdapter
from simpleob.taxonomy.model import TaxonomyModel
from simpleob.taxonomy.resolver import TaxonomyResolver


class TaxonomyService:
    """Lädt die passende Taxonomie für ein Geschäftsjahr."""

    def __init__(
        self,
        resolver: TaxonomyResolver,
        adapter: ArelleAdapter,
    ) -> None:
        self._resolver = resolver
        self._adapter = adapter
        
    def __enter__(self) -> "TaxonomyService":
        """Öffnet den Taxonomie-Service als Context Manager."""

        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ) -> None:
        """Schließt den Taxonomie-Service beim Verlassen des Contexts."""

        self.close()

    def model_for(
        self,
        fiscal_year: FiscalYear,
    ) -> TaxonomyModel:
        """Lädt das Taxonomiemodell für ein Geschäftsjahr."""

        entry_point = self._resolver.for_fiscal_year(
            fiscal_year
        )

        return self._adapter.model(
            entry_point
        )

    def close(self) -> None:
        """Schließt die Ressourcen des Taxonomie-Adapters."""

        self._adapter.close()
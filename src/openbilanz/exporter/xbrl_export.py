"""Export von Taxonomiedaten als XBRL-Instanz."""

from openbilanz.taxonomy.context import TaxonomyContext
from openbilanz.taxonomy.entry_point import TaxonomyEntryPoint
from openbilanz.taxonomy.fact import TaxonomyFact
from openbilanz.taxonomy.text_fact import TaxonomyTextFact
from openbilanz.taxonomy.unit import TaxonomyUnit
from openbilanz.taxonomy.xbrl_writer import TaxonomyXbrlWriter


class XbrlExporter:
    """Erzeugt vollständige XBRL-Instanzen."""

    def __init__(self) -> None:
        self._writer = TaxonomyXbrlWriter()

    def export(
        self,
        *,
        contexts: dict[str, TaxonomyContext],
        units: dict[str, TaxonomyUnit],
        facts: tuple[
            TaxonomyFact | TaxonomyTextFact,
            ...,
        ],
        taxonomy_namespace: str,
        entry_points: tuple[TaxonomyEntryPoint, ...],
    ) -> str:
        """Erzeugt eine XBRL-Instanz als XML-String."""

        root = self._writer.instance_element(
            contexts=contexts,
            units=units,
            facts=facts,
            taxonomy_namespace=taxonomy_namespace,
            entry_points=entry_points,
        )

        return self._writer.to_xml_string(
            root=root
        )

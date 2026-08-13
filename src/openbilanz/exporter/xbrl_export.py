"""Export von Taxonomiedaten als XBRL-Instanz."""

from openbilanz.taxonomy.context import TaxonomyContext
from openbilanz.taxonomy.entry_point import TaxonomyEntryPoint
from openbilanz.taxonomy.fact import TaxonomyFact
from openbilanz.taxonomy.text_fact import TaxonomyTextFact
from openbilanz.taxonomy.unit import TaxonomyUnit
from openbilanz.taxonomy.xbrl_writer import TaxonomyXbrlWriter
from openbilanz.taxonomy.gcd_report_element import (
    GcdReportElement,
)


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
        taxonomy_namespaces: dict[str, str] | None = None,
        report_elements: tuple[GcdReportElement, ...] = (),
    ) -> str:
        """Erzeugt eine XBRL-Instanz als XML-String."""

        root = self._writer.instance_element(
            contexts=contexts,
            units=units,
            facts=facts,
            taxonomy_namespace=taxonomy_namespace,
            taxonomy_namespaces=taxonomy_namespaces,
            entry_points=entry_points,
            report_elements=report_elements,
        )

        return self._writer.to_xml_string(
            root=root
        )

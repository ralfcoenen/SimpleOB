"""Serialisierung taxonomischer Daten als XBRL."""

from xml.etree import ElementTree as ET

from openbilanz.taxonomy.concept import TaxonomyPeriodType
from openbilanz.taxonomy.context import TaxonomyContext
from openbilanz.taxonomy.entry_point import TaxonomyEntryPoint
from openbilanz.taxonomy.fact import TaxonomyFact
from openbilanz.taxonomy.text_fact import TaxonomyTextFact
from openbilanz.taxonomy.unit import TaxonomyUnit

XBRLI_NAMESPACE = "http://www.xbrl.org/2003/instance"
ISO4217_NAMESPACE = "http://www.xbrl.org/2003/iso4217"
LINK_NAMESPACE = "http://www.xbrl.org/2003/linkbase"
XLINK_NAMESPACE = "http://www.w3.org/1999/xlink"


class TaxonomyXbrlWriter:
    """Serialisiert Taxonomie-Objekte als XBRL-Elemente."""

    def context_element(
        self,
        context: TaxonomyContext,
        context_id: str,
    ) -> ET.Element:
        """Erzeugt ein XBRL-Context-Element."""

        element = ET.Element(
            f"{{{XBRLI_NAMESPACE}}}context",
            {
                "id": context_id,
            },
        )

        entity = ET.SubElement(
            element,
            f"{{{XBRLI_NAMESPACE}}}entity",
        )

        identifier = ET.SubElement(
            entity,
            f"{{{XBRLI_NAMESPACE}}}identifier",
            {
                "scheme": context.entity_scheme,
            },
        )
        identifier.text = context.entity_identifier

        period = ET.SubElement(
            element,
            f"{{{XBRLI_NAMESPACE}}}period",
        )

        if context.period_type is TaxonomyPeriodType.INSTANT:
            instant = ET.SubElement(
                period,
                f"{{{XBRLI_NAMESPACE}}}instant",
            )
            instant.text = context.end_date.isoformat()

        else:
            start_date = ET.SubElement(
                period,
                f"{{{XBRLI_NAMESPACE}}}startDate",
            )
            start_date.text = context.start_date.isoformat()

            end_date = ET.SubElement(
                period,
                f"{{{XBRLI_NAMESPACE}}}endDate",
            )
            end_date.text = context.end_date.isoformat()

        return element

    def unit_element(
        self,
        unit: TaxonomyUnit,
        unit_id: str,
    ) -> ET.Element:
        """Erzeugt ein XBRL-Unit-Element."""

        element = ET.Element(
            f"{{{XBRLI_NAMESPACE}}}unit",
            {
                "id": unit_id,
            },
        )

        measure = ET.SubElement(
            element,
            f"{{{XBRLI_NAMESPACE}}}measure",
        )
        measure.text = unit.measure

        return element

    def fact_element(
        self,
        fact: TaxonomyFact,
        context_id: str,
        unit_id: str,
        namespace: str,
    ) -> ET.Element:
        """Erzeugt ein numerisches XBRL-Fact-Element."""

        element = ET.Element(
            f"{{{namespace}}}{fact.concept.name}",
            {
                "contextRef": context_id,
                "unitRef": unit_id,
                "decimals": str(fact.decimals),
            },
        )

        element.text = str(
            fact.amount
        )

        return element

    def instance_element(
        self,
        contexts: dict[str, TaxonomyContext],
        units: dict[str, TaxonomyUnit],
        facts: tuple[
            TaxonomyFact | TaxonomyTextFact,
            ...,
        ],
        taxonomy_namespace: str,
        entry_points: tuple[TaxonomyEntryPoint, ...],
    ) -> ET.Element:
        """Erzeugt das Root-Element einer XBRL-Instanz."""

        root = ET.Element(
            f"{{{XBRLI_NAMESPACE}}}xbrl"
        )

        for entry_point in entry_points:
            root.append(
                self.schema_ref_element(
                    entry_point=entry_point,
                )
            )

        for context_id, context in contexts.items():
            root.append(
                self.context_element(
                    context=context,
                    context_id=context_id,
                )
            )
            
        for unit_id, unit in units.items():
            root.append(
                self.unit_element(
                    unit=unit,
                    unit_id=unit_id,
                )
            )

        for fact in facts:
            context_id = self.context_id_for(
                context=fact.context,
                contexts=contexts,
            )

            if isinstance(
                fact,
                TaxonomyTextFact,
            ):
                root.append(
                    self.text_fact_element(
                        fact=fact,
                        context_id=context_id,
                        namespace=taxonomy_namespace,
                    )
                )
                continue

            root.append(
                self.fact_element(
                    fact=fact,
                    context_id=context_id,
                    unit_id=self.unit_id_for(
                        unit=fact.unit,
                        units=units,
                    ),
                    namespace=taxonomy_namespace,
                )
            )
        
        return root

    def schema_ref_element(
        self,
        entry_point: TaxonomyEntryPoint,
    ) -> ET.Element:
        """Erzeugt ein XBRL-schemaRef-Element."""

        return ET.Element(
            "{http://www.xbrl.org/2003/linkbase}schemaRef",
            {
                "{http://www.w3.org/1999/xlink}type": "simple",
                "{http://www.w3.org/1999/xlink}href": (
                    entry_point.schema_ref_uri
                ),
            },
        )

    def to_xml_string(
        self,
        root: ET.Element,
    ) -> str:
        """Serialisiert eine XBRL-Instanz als XML-String."""

        ET.register_namespace(
            "xbrli",
            XBRLI_NAMESPACE,
        )
        ET.register_namespace(
            "link",
            LINK_NAMESPACE,
        )
        ET.register_namespace(
            "xlink",
            XLINK_NAMESPACE,
        )

        root.set(
            "xmlns:iso4217",
            ISO4217_NAMESPACE,
        )

        xml_bytes = ET.tostring(
            root,
            encoding="utf-8",
            xml_declaration=True,
        )

        return xml_bytes.decode("utf-8")
    
    def context_id_for(
        self,
        context: TaxonomyContext,
        contexts: dict[str, TaxonomyContext],
    ) -> str:
        """Ermittelt die XBRL-ID eines Contexts."""

        for context_id, candidate in contexts.items():
            if candidate is context:
                return context_id

        raise ValueError(
            "context is not registered"
        )
        
    def unit_id_for(
        self,
        unit: TaxonomyUnit,
        units: dict[str, TaxonomyUnit],
    ) -> str:
        """Ermittelt die XBRL-ID einer Einheit."""

        for unit_id, candidate in units.items():
            if candidate == unit:
                return unit_id

        raise ValueError(
            "unit is not registered"
        )
        
    def text_fact_element(
        self,
        fact: TaxonomyTextFact,
        context_id: str,
        namespace: str,
    ) -> ET.Element:
        """Erzeugt ein nichtnumerisches XBRL-Text-Fact-Element."""

        element = ET.Element(
            f"{{{namespace}}}{fact.concept.name}",
            {
                "contextRef": context_id,
            },
        )

        element.text = fact.value

        return element
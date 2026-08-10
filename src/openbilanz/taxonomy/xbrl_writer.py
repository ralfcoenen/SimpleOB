"""Serialisierung taxonomischer Daten als XBRL."""

from xml.etree import ElementTree as ET

from openbilanz.taxonomy.concept import TaxonomyPeriodType
from openbilanz.taxonomy.context import TaxonomyContext
from openbilanz.taxonomy.fact import TaxonomyFact
from openbilanz.taxonomy.unit import TaxonomyUnit

XBRLI_NAMESPACE = "http://www.xbrl.org/2003/instance"


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
            },
        )

        element.text = str(
            fact.amount
        )

        return element
    
    def instance_element(
        self,
        context: TaxonomyContext,
        context_id: str,
        unit: TaxonomyUnit,
        unit_id: str,
        facts: tuple[TaxonomyFact, ...],
        taxonomy_namespace: str,
    ) -> ET.Element:
        """Erzeugt das Root-Element einer XBRL-Instanz."""

        root = ET.Element(
            f"{{{XBRLI_NAMESPACE}}}xbrl"
        )

        root.append(
            self.context_element(
                context=context,
                context_id=context_id,
            )
        )

        root.append(
            self.unit_element(
                unit=unit,
                unit_id=unit_id,
            )
        )

        for fact in facts:
            root.append(
                self.fact_element(
                    fact=fact,
                    context_id=context_id,
                    unit_id=unit_id,
                    namespace=taxonomy_namespace,
                )
            )

        return root
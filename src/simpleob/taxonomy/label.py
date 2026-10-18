"""Labels einer XBRL-Taxonomie."""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from xml.etree import ElementTree

LINK_NAMESPACE = "http://www.xbrl.org/2003/linkbase"
XLINK_NAMESPACE = "http://www.w3.org/1999/xlink"
XML_NAMESPACE = "http://www.w3.org/XML/1998/namespace"


class TaxonomyLabelRole(Enum):
    """Fachliche Rolle eines XBRL-Labels."""

    LABEL = "label"
    TERSE_LABEL = "terseLabel"
    DOCUMENTATION = "documentation"
    DEFINITION_GUIDANCE = "definitionGuidance"
    TERSE_60_LABEL = "terse60Label"
    POSITIVE_LABEL = "positiveLabel"
    NEGATIVE_LABEL = "negativeLabel"
    NEGATIVE_TERSE_LABEL = "negativeTerseLabel"
    POSITIVE_TERSE_LABEL = "positiveTerseLabel"
    DISCLOSURE_GUIDANCE = "disclosureGuidance"
    TOTAL_LABEL = "totalLabel"
    OTHER = "other"


@dataclass(frozen=True, slots=True)
class TaxonomyLabel:
    """Repräsentiert ein Label eines XBRL-Konzepts."""

    concept_id: str
    text: str
    role: TaxonomyLabelRole
    role_uri: str
    language: str | None

    @classmethod
    def from_linkbase(
        cls,
        path: Path,
    ) -> tuple["TaxonomyLabel", ...]:
        """Lädt Labels aus einer XBRL-Label-Linkbase."""

        if not isinstance(path, Path):
            raise TypeError(
                "path muss eine Path-Instanz sein."
            )

        tree = ElementTree.parse(path)
        root = tree.getroot()

        locators: dict[str, str] = {}

        for locator in root.findall(
            f".//{{{LINK_NAMESPACE}}}loc"
        ):
            locator_label = locator.attrib.get(
                f"{{{XLINK_NAMESPACE}}}label"
            )
            href = locator.attrib.get(
                f"{{{XLINK_NAMESPACE}}}href"
            )

            if locator_label is None or href is None:
                continue

            if "#" not in href:
                continue

            concept_id = href.split("#", 1)[1]

            locators[locator_label] = concept_id

        resources = {
            label.attrib[f"{{{XLINK_NAMESPACE}}}label"]: label
            for label in root.findall(
                f".//{{{LINK_NAMESPACE}}}label"
            )
            if f"{{{XLINK_NAMESPACE}}}label"
            in label.attrib
        }

        labels: list[TaxonomyLabel] = []

        for arc in root.findall(
            f".//{{{LINK_NAMESPACE}}}labelArc"
        ):
            source = arc.attrib.get(
                f"{{{XLINK_NAMESPACE}}}from"
            )
            target = arc.attrib.get(
                f"{{{XLINK_NAMESPACE}}}to"
            )

            if source is None or target is None:
                continue

            concept_id = locators.get(source)
            resource = resources.get(target)

            if concept_id is None or resource is None:
                continue

            role_uri = resource.attrib.get(
                f"{{{XLINK_NAMESPACE}}}role"
            )

            if role_uri is None:
                continue

            labels.append(
                cls(
                    concept_id=concept_id,
                    text="".join(
                        resource.itertext()
                    ).strip(),
                    role=cls._role_from_uri(
                        role_uri
                    ),
                    role_uri=role_uri,
                    language=resource.attrib.get(
                        f"{{{XML_NAMESPACE}}}lang"
                    ),
                )
            )

        return tuple(labels)

    @staticmethod
    def _role_from_uri(
        role_uri: str,
    ) -> TaxonomyLabelRole:
        """Ordnet eine XBRL-Label-Rolle fachlich ein."""

        mapping = {
            "http://www.xbrl.org/2003/role/label":
                TaxonomyLabelRole.LABEL,
            "http://www.xbrl.org/2003/role/terseLabel":
                TaxonomyLabelRole.TERSE_LABEL,
            "http://www.xbrl.org/2003/role/documentation":
                TaxonomyLabelRole.DOCUMENTATION,
            "http://www.xbrl.org/2003/role/definitionGuidance":
                TaxonomyLabelRole.DEFINITION_GUIDANCE,
            "http://www.xbrl.de/roles/labels/terse60Label":
                TaxonomyLabelRole.TERSE_60_LABEL,
            "http://www.xbrl.org/2003/role/positiveLabel":
                TaxonomyLabelRole.POSITIVE_LABEL,
            "http://www.xbrl.org/2003/role/negativeLabel":
                TaxonomyLabelRole.NEGATIVE_LABEL,
            "http://www.xbrl.org/2003/role/negativeTerseLabel":
                TaxonomyLabelRole.NEGATIVE_TERSE_LABEL,
            "http://www.xbrl.org/2003/role/positiveTerseLabel":
                TaxonomyLabelRole.POSITIVE_TERSE_LABEL,
            "http://www.xbrl.org/2003/role/disclosureGuidance":
                TaxonomyLabelRole.DISCLOSURE_GUIDANCE,
            "http://www.xbrl.org/2003/role/totalLabel":
                TaxonomyLabelRole.TOTAL_LABEL,
        }

        return mapping.get(
            role_uri,
            TaxonomyLabelRole.OTHER,
        )

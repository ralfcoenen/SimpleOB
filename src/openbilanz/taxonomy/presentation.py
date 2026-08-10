"""Presentation-Beziehungen einer XBRL-Taxonomie."""

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from xml.etree import ElementTree

LINK_NAMESPACE = "http://www.xbrl.org/2003/linkbase"
XLINK_NAMESPACE = "http://www.w3.org/1999/xlink"


@dataclass(frozen=True, slots=True)
class TaxonomyPresentationRelation:
    """Parent-Child-Beziehung einer Presentation-Linkbase."""

    parent_concept_id: str
    child_concept_id: str
    order: Decimal
    role_uri: str
    preferred_label_role_uri: str | None

    @classmethod
    def from_linkbase(
        cls,
        path: Path,
    ) -> tuple["TaxonomyPresentationRelation", ...]:
        """Lädt Presentation-Beziehungen aus einer Linkbase."""

        if not isinstance(path, Path):
            raise TypeError(
                "path muss eine Path-Instanz sein."
            )

        tree = ElementTree.parse(path)
        root = tree.getroot()

        relations: list[TaxonomyPresentationRelation] = []

        for presentation_link in root.findall(
            f".//{{{LINK_NAMESPACE}}}presentationLink"
        ):
            role_uri = presentation_link.attrib.get(
                f"{{{XLINK_NAMESPACE}}}role"
            )

            if role_uri is None:
                continue

            locators: dict[str, str] = {}

            for locator in presentation_link.findall(
                f"{{{LINK_NAMESPACE}}}loc"
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

            for arc in presentation_link.findall(
                f"{{{LINK_NAMESPACE}}}presentationArc"
            ):
                source = arc.attrib.get(
                    f"{{{XLINK_NAMESPACE}}}from"
                )
                target = arc.attrib.get(
                    f"{{{XLINK_NAMESPACE}}}to"
                )
                order_value = arc.attrib.get("order")

                if (
                    source is None
                    or target is None
                    or order_value is None
                ):
                    continue

                parent_concept_id = locators.get(source)
                child_concept_id = locators.get(target)

                if (
                    parent_concept_id is None
                    or child_concept_id is None
                ):
                    continue

                relations.append(
                    cls(
                        parent_concept_id=parent_concept_id,
                        child_concept_id=child_concept_id,
                        order=Decimal(order_value),
                        role_uri=role_uri,
                        preferred_label_role_uri=(
                            arc.attrib.get("preferredLabel")
                        ),
                    )
                )

        return tuple(relations)


"""Konzepte einer XBRL-Taxonomie."""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from xml.etree import ElementTree

XSD_NAMESPACE = "http://www.w3.org/2001/XMLSchema"
XBRLI_NAMESPACE = "http://www.xbrl.org/2003/instance"


class TaxonomyPeriodType(Enum):
    """Periodenbezug eines XBRL-Konzepts."""

    INSTANT = "instant"
    DURATION = "duration"
    UNKNOWN = "unknown"


class TaxonomyBalance(Enum):
    """Soll-/Habencharakter eines XBRL-Konzepts."""

    DEBIT = "debit"
    CREDIT = "credit"
    NONE = "none"


@dataclass(frozen=True, slots=True)
class TaxonomyConcept:
    """Repräsentiert ein Konzept aus einem XBRL-Schema."""

    name: str
    concept_id: str
    type_name: str | None
    substitution_group: str | None
    period_type: TaxonomyPeriodType
    balance: TaxonomyBalance
    abstract: bool
    nillable: bool

    @classmethod
    def from_schema(
        cls,
        path: Path,
    ) -> tuple["TaxonomyConcept", ...]:
        """Lädt Taxonomiekonzepte aus einer XSD-Datei."""

        if not isinstance(path, Path):
            raise TypeError(
                "path muss eine Path-Instanz sein."
            )

        tree = ElementTree.parse(path)
        root = tree.getroot()

        concepts: list[TaxonomyConcept] = []

        for element in root.findall(
            f"{{{XSD_NAMESPACE}}}element"
        ):
            name = element.attrib.get("name")
            concept_id = element.attrib.get("id")

            if name is None or concept_id is None:
                continue

            period_type_value = element.attrib.get(
                f"{{{XBRLI_NAMESPACE}}}periodType"
            )

            balance_value = element.attrib.get(
                f"{{{XBRLI_NAMESPACE}}}balance"
            )

            concepts.append(
                cls(
                    name=name,
                    concept_id=concept_id,
                    type_name=element.attrib.get("type"),
                    substitution_group=element.attrib.get(
                        "substitutionGroup"
                    ),
                    period_type=cls._period_type(
                        period_type_value
                    ),
                    balance=cls._balance(
                        balance_value
                    ),
                    abstract=cls._xml_bool(
                        element.attrib.get("abstract")
                    ),
                    nillable=cls._xml_bool(
                        element.attrib.get("nillable")
                    ),
                )
            )

        return tuple(concepts)

    @staticmethod
    def _xml_bool(
        value: str | None,
    ) -> bool:
        """Wandelt einen XML-Boolean in bool um."""

        return value in ("true", "1")

    @staticmethod
    def _period_type(
        value: str | None,
    ) -> TaxonomyPeriodType:
        """Wandelt den XBRL-Periodentyp um."""

        if value == "instant":
            return TaxonomyPeriodType.INSTANT

        if value == "duration":
            return TaxonomyPeriodType.DURATION

        return TaxonomyPeriodType.UNKNOWN

    @staticmethod
    def _balance(
        value: str | None,
    ) -> TaxonomyBalance:
        """Wandelt den XBRL-Soll-/Habencharakter um."""

        if value == "debit":
            return TaxonomyBalance.DEBIT

        if value == "credit":
            return TaxonomyBalance.CREDIT

        return TaxonomyBalance.NONE
    
    @property
    def is_numeric(self) -> bool:
        """Gibt an, ob das Concept einen numerischen XBRL-Typ besitzt."""

        return self.type_name in {
            "xbrli:monetaryItemType",
            "xbrli:decimalItemType",
            "xbrli:pureItemType",
            "xbrli:longItemType",
            "xbrli:positiveIntegerItemType",
        }

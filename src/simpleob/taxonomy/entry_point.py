"""Entry Points für XBRL-Taxonomien."""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from xml.etree import ElementTree

XSD_NAMESPACE = "http://www.w3.org/2001/XMLSchema" 
LINK_NAMESPACE = "http://www.xbrl.org/2003/linkbase"
XLINK_NAMESPACE = "http://www.w3.org/1999/xlink"

class TaxonomyFamily(Enum):
    """Fachliche Familie einer XBRL-Taxonomie."""

    BRA = "de-bra"
    FI = "de-fi"
    GAAP_CI = "de-gaap-ci"
    GCD = "de-gcd"
    INS = "de-ins"
    PI = "de-pi"
    UNKNOWN = "unknown"

class TaxonomyEntryPointVariant(Enum):
    """Variante eines XBRL-Taxonomie-Entry-Points."""

    STANDARD = "standard"
    FISCAL = "fiscal"
    MICRO_BILG = "microbilg"
    FISCAL_MICRO_BILG = "fiscal-microbilg"
    GROUP = "group"
    STAFFELFORM = "staffelform"
    STAFFELFORM_FISCAL = "staffelform-fiscal"
    UNKNOWN = "unknown"


class TaxonomyLinkbaseType(Enum):
    """Unterstützte Typen von XBRL-Linkbases."""

    PRESENTATION = "presentation"
    CALCULATION = "calculation"
    DEFINITION = "definition"
    LABEL = "label"
    REFERENCE = "reference"
    OTHER = "other"


@dataclass(frozen=True, slots=True)
class TaxonomyLinkbaseReference:
    """Referenz auf eine XBRL-Linkbase."""

    href: str
    role: str

    @property
    def type(self) -> TaxonomyLinkbaseType:
        """Ermittelt den fachlichen Linkbase-Typ."""

        if self.role.endswith(
            "/presentationLinkbaseRef"
        ):
            return TaxonomyLinkbaseType.PRESENTATION

        if self.role.endswith(
            "/calculationLinkbaseRef"
        ):
            return TaxonomyLinkbaseType.CALCULATION

        if self.role.endswith(
            "/definitionLinkbaseRef"
        ):
            return TaxonomyLinkbaseType.DEFINITION

        if self.role.endswith(
            "/labelLinkbaseRef"
        ):
            return TaxonomyLinkbaseType.LABEL

        if self.role.endswith(
            "/referenceLinkbaseRef"
        ):
            return TaxonomyLinkbaseType.REFERENCE

        return TaxonomyLinkbaseType.OTHER


@dataclass(frozen=True, slots=True)
class TaxonomyEntryPoint:
    """Beschreibt einen XBRL-Taxonomie-Entry-Point."""

    path: Path
    namespace: str
    schema_imports: tuple[str, ...]
    linkbase_references: tuple[
        TaxonomyLinkbaseReference,
        ...
    ] = ()
    schema_ref: str | None = None
    
    @property
    def schema_ref_uri(self) -> str:
        """Ermittelt die URI des Entry-Point-Schemas."""

        if self.schema_ref is not None:
            return self.schema_ref

        base_namespace = self.namespace.rsplit("/", 1)[0]

        return f"{base_namespace}/{self.path.name}"
    
    @property
    def variant(self) -> TaxonomyEntryPointVariant:
        """Ermittelt die Variante des Entry Points."""

        namespace = self.namespace.rstrip("/")

        if namespace.endswith("/shell-fiscal-microbilg"):
            return TaxonomyEntryPointVariant.FISCAL_MICRO_BILG

        if namespace.endswith("/shell-staffelform-fiscal"):
            return TaxonomyEntryPointVariant.STAFFELFORM_FISCAL

        if namespace.endswith("/shell-microbilg"):
            return TaxonomyEntryPointVariant.MICRO_BILG

        if namespace.endswith("/shell-staffelform"):
            return TaxonomyEntryPointVariant.STAFFELFORM

        if namespace.endswith("/shell-fiscal"):
            return TaxonomyEntryPointVariant.FISCAL

        if namespace.endswith("/shell-group"):
            return TaxonomyEntryPointVariant.GROUP

        if namespace.endswith("/shell"):
            return TaxonomyEntryPointVariant.STANDARD

        return TaxonomyEntryPointVariant.UNKNOWN

    @property
    def family(self) -> TaxonomyFamily:
            """Ermittelt die Taxonomiefamilie aus dem Namespace."""

            for family in TaxonomyFamily:
                if family is TaxonomyFamily.UNKNOWN:
                    continue

                marker = f"/{family.value}-"

                if marker in self.namespace:
                    return family

            return TaxonomyFamily.UNKNOWN
    
    @classmethod
    def from_file(
        cls,
        path: Path,
    ) -> "TaxonomyEntryPoint":
        """Liest Metadaten und Linkbase-Referenzen einer Shell-XSD."""

        if not isinstance(
            path,
            Path,
        ):
            raise TypeError(
                "path muss eine Path-Instanz sein."
            )

        tree = ElementTree.parse(
            path
        )
        root = tree.getroot()

        namespace = root.attrib.get(
            "targetNamespace"
        )

        if namespace is None:
            raise ValueError(
                "Die Taxonomie-Shell besitzt "
                "keinen targetNamespace."
            )

        schema_imports = tuple(
            element.attrib["schemaLocation"]
            for element in root.findall(
                f"{{{XSD_NAMESPACE}}}import"
            )
            if "schemaLocation"
            in element.attrib
        )

        linkbase_references = tuple(
            TaxonomyLinkbaseReference(
                href=element.attrib[
                    f"{{{XLINK_NAMESPACE}}}href"
                ],
                role=element.attrib[
                    f"{{{XLINK_NAMESPACE}}}role"
                ],
            )
            for element in root.findall(
                ".//"
                f"{{{LINK_NAMESPACE}}}linkbaseRef"
            )
            if (
                f"{{{XLINK_NAMESPACE}}}href"
                in element.attrib
                and
                f"{{{XLINK_NAMESPACE}}}role"
                in element.attrib
            )
        )

        return cls(
            path=path,
            namespace=namespace,
            schema_imports=schema_imports,
            linkbase_references=linkbase_references,
        )

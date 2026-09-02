"""Lesen fiskalischer Anforderungsmerkmale aus GAAP-CI-Referenzen."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from openbilanz.taxonomy.entry_point import TaxonomyEntryPoint

_XS_NAMESPACE = "http://www.w3.org/2001/XMLSchema"
_LINK_NAMESPACE = "http://www.xbrl.org/2003/linkbase"
_XLINK_NAMESPACE = "http://www.w3.org/1999/xlink"
_HGBREF_NAMESPACE = "http://www.xbrl.de/taxonomies/de-ref-2010-02-19"

_CONCEPT_REFERENCE_ARCROLE = (
    "http://www.xbrl.org/2003/arcrole/concept-reference"
)


class FiscalRequirement(Enum):
    """Fiskalische Anforderung eines GAAP-CI-Konzepts."""

    REQUIRED = "Mussfeld"
    SUM_REQUIRED = "Summenmussfeld"
    CALCULATION_IF_PRESENT = (
        "Rechnerisch notwendig, soweit vorhanden"
    )


@dataclass(frozen=True, slots=True)
class FiscalConceptRequirement:
    """Fiskalische Referenzinformationen eines GAAP-CI-Konzepts."""

    concept_name: str
    requirement: FiscalRequirement
    legal_form_kst: bool
    not_permitted_for: str | None = None


class FiscalRequirementReader:
    """Liest fiskalische Anforderungen aus einem GAAP-CI-Entry-Point."""

    def __init__(
        self,
        entry_point: TaxonomyEntryPoint,
    ) -> None:
        if not isinstance(
            entry_point,
            TaxonomyEntryPoint,
        ):
            raise TypeError(
                "entry_point must be a TaxonomyEntryPoint"
            )

        self._entry_point = entry_point

    def requirements(
        self,
    ) -> tuple[FiscalConceptRequirement, ...]:
        """Liest alle bekannten fiskalischen Anforderungen."""

        requirements_by_concept: dict[
            str,
            FiscalConceptRequirement,
        ] = {}

        for reference_path in self._reference_paths():
            for requirement in self._read_reference_file(
                reference_path
            ):
                existing = requirements_by_concept.get(
                    requirement.concept_name
                )

                if (
                    existing is not None
                    and existing != requirement
                ):
                    raise ValueError(
                        "conflicting fiscal requirements for "
                        f"{requirement.concept_name}"
                    )

                requirements_by_concept[
                    requirement.concept_name
                ] = requirement

        return tuple(
            requirements_by_concept[concept_name]
            for concept_name in sorted(
                requirements_by_concept
            )
        )

    def corporation_requirements(
        self,
    ) -> tuple[FiscalConceptRequirement, ...]:
        """Liefert Anforderungen für Körperschaften."""

        return tuple(
            requirement
            for requirement in self.requirements()
            if requirement.legal_form_kst
        )

    def _reference_paths(
        self,
    ) -> tuple[Path, ...]:
        """Findet fiskalische Reference-Linkbases der Importkette."""

        references: set[Path] = set()
        visited: set[Path] = set()

        self._collect_reference_paths(
            self._entry_point.path,
            references,
            visited,
        )

        return tuple(
            sorted(
                references,
                key=str,
            )
        )

    def _collect_reference_paths(
        self,
        schema_path: Path,
        references: set[Path],
        visited: set[Path],
    ) -> None:
        schema_path = schema_path.resolve()

        if schema_path in visited:
            return

        visited.add(schema_path)

        root = ET.parse(
            schema_path
        ).getroot()

        target_namespace = root.get(
            "targetNamespace",
            "",
        )

        if (
            "www.xbrl.de/taxonomies/de-gaap-ci-"
            not in target_namespace
        ):
            return

        for linkbase_ref in root.findall(
            f".//{{{_LINK_NAMESPACE}}}linkbaseRef"
        ):
            href = linkbase_ref.get(
                f"{{{_XLINK_NAMESPACE}}}href"
            )

            if not href:
                continue

            if not href.endswith(
                "-reference-fiscal.xml"
            ):
                continue

            reference_path = (
                schema_path.parent
                / href
            ).resolve()

            if reference_path.is_file():
                references.add(
                    reference_path
                )

        for schema_import in root.findall(
            f"{{{_XS_NAMESPACE}}}import"
        ):
            schema_location = schema_import.get(
                "schemaLocation"
            )

            if not schema_location:
                continue

            imported_path = (
                schema_path.parent
                / schema_location
            ).resolve()

            if not imported_path.is_file():
                continue

            self._collect_reference_paths(
                imported_path,
                references,
                visited,
            )

    def _read_reference_file(
        self,
        path: Path,
    ) -> tuple[FiscalConceptRequirement, ...]:
        root = ET.parse(
            path
        ).getroot()

        result: list[
            FiscalConceptRequirement
        ] = []

        for reference_link in root.findall(
            f".//{{{_LINK_NAMESPACE}}}referenceLink"
        ):
            locators = {
                locator.get(
                    f"{{{_XLINK_NAMESPACE}}}label"
                ): locator.get(
                    f"{{{_XLINK_NAMESPACE}}}href"
                )
                for locator in reference_link.findall(
                    f"{{{_LINK_NAMESPACE}}}loc"
                )
                if locator.get(
                    f"{{{_XLINK_NAMESPACE}}}label"
                )
                and locator.get(
                    f"{{{_XLINK_NAMESPACE}}}href"
                )
            }

            references = {
                reference.get(
                    f"{{{_XLINK_NAMESPACE}}}label"
                ): reference
                for reference in reference_link.findall(
                    f"{{{_LINK_NAMESPACE}}}reference"
                )
                if reference.get(
                    f"{{{_XLINK_NAMESPACE}}}label"
                )
            }

            for reference_arc in reference_link.findall(
                f"{{{_LINK_NAMESPACE}}}referenceArc"
            ):
                if reference_arc.get(
                    f"{{{_XLINK_NAMESPACE}}}arcrole"
                ) != _CONCEPT_REFERENCE_ARCROLE:
                    continue

                from_label = reference_arc.get(
                    f"{{{_XLINK_NAMESPACE}}}from"
                )
                to_label = reference_arc.get(
                    f"{{{_XLINK_NAMESPACE}}}to"
                )

                if (
                    from_label is None
                    or to_label is None
                ):
                    continue

                concept_href = locators.get(
                    from_label
                )
                reference = references.get(
                    to_label
                )

                if (
                    concept_href is None
                    or reference is None
                ):
                    continue

                fiscal_requirement_element = (
                    reference.find(
                        (
                            f"{{{_HGBREF_NAMESPACE}}}"
                            "fiscalRequirement"
                        )
                    )
                )

                if (
                    fiscal_requirement_element is None
                    or fiscal_requirement_element.text is None
                ):
                    continue

                requirement_text = (
                    fiscal_requirement_element.text.strip()
                )

                try:
                    requirement = FiscalRequirement(
                        requirement_text
                    )
                except ValueError as exc:
                    raise ValueError(
                        "unknown fiscal requirement "
                        f"{requirement_text!r}"
                    ) from exc

                legal_form_kst_element = (
                    reference.find(
                        (
                            f"{{{_HGBREF_NAMESPACE}}}"
                            "legalFormKSt"
                        )
                    )
                )

                legal_form_kst = (
                    legal_form_kst_element is not None
                    and (
                        legal_form_kst_element.text
                        or ""
                    ).strip().lower()
                    == "true"
                )

                not_permitted_for_element = (
                    reference.find(
                        (
                            f"{{{_HGBREF_NAMESPACE}}}"
                            "notPermittedFor"
                        )
                    )
                )

                not_permitted_for = None

                if (
                    not_permitted_for_element is not None
                    and not_permitted_for_element.text
                ):
                    not_permitted_for = (
                        not_permitted_for_element.text.strip()
                    )

                result.append(
                    FiscalConceptRequirement(
                        concept_name=self._concept_name(
                            concept_href
                        ),
                        requirement=requirement,
                        legal_form_kst=legal_form_kst,
                        not_permitted_for=not_permitted_for,
                    )
                )

        return tuple(
            result
        )

    @staticmethod
    def _concept_name(
        href: str,
    ) -> str:
        """Ermittelt den Taxonomie-Konzeptnamen aus einem Locator."""

        _, separator, fragment = href.partition(
            "#"
        )

        if not separator or not fragment:
            raise ValueError(
                f"invalid concept locator href: {href!r}"
            )

        prefix = "de-gaap-ci_"

        if fragment.startswith(
            prefix
        ):
            return fragment[
                len(prefix):
            ]

        return fragment

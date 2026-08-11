"""Analysiert nichtnumerische Concept-Typen einer XBRL-Taxonomie."""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
from xml.etree import ElementTree as ET

XSD_NAMESPACE = "http://www.w3.org/2001/XMLSchema"

NUMERIC_TYPES = {
    "xbrli:monetaryItemType",
    "xbrli:decimalItemType",
    "xbrli:pureItemType",
    "xbrli:longItemType",
    "xbrli:positiveIntegerItemType",
}


def analyze_taxonomy(
    root: Path,
) -> None:
    """Analysiert berichtbare Concept-Typen in allen XSD-Dateien."""

    type_counts: Counter[str] = Counter()
    non_numeric_concepts: list[
        tuple[str, str, Path]
    ] = []

    xsd_files = tuple(
        sorted(
            root.rglob("*.xsd")
        )
    )

    for path in xsd_files:
        try:
            tree = ET.parse(path)
        except ET.ParseError as exc:
            print(
                f"WARNUNG: XML-Fehler in {path}: {exc}"
            )
            continue

        root_element = tree.getroot()

        for element in root_element.findall(
            f".//{{{XSD_NAMESPACE}}}element"
        ):
            name = element.attrib.get("name")
            type_name = element.attrib.get("type")
            substitution_group = element.attrib.get(
                "substitutionGroup"
            )

            if not name or not type_name:
                continue

            if substitution_group != "xbrli:item":
                continue

            type_counts[type_name] += 1

            if type_name not in NUMERIC_TYPES:
                non_numeric_concepts.append(
                    (
                        name,
                        type_name,
                        path,
                    )
                )

    print()
    print("XSD-DATEIEN:")
    print(len(xsd_files))

    print()
    print("BERICHTBARE XBRL-CONCEPTS:")
    print(
        sum(type_counts.values())
    )

    print()
    print("ALLE BERICHTBAREN CONCEPT-TYPEN:")

    for type_name, count in type_counts.most_common():
        print(
            f"{count:6}  {type_name}"
        )

    non_numeric_type_counts = Counter(
        type_name
        for _, type_name, _ in non_numeric_concepts
    )

    print()
    print("NICHTNUMERISCHE BERICHTBARE CONCEPT-TYPEN:")

    for (
        type_name,
        count,
    ) in non_numeric_type_counts.most_common():
        print(
            f"{count:6}  {type_name}"
        )

    print()
    print(
        "NICHTNUMERISCHE BERICHTBARE CONCEPTS GESAMT:"
    )
    print(
        len(non_numeric_concepts)
    )

    print()
    print("BEISPIELE JE TYP:")

    examples: dict[
        str,
        list[str],
    ] = {}

    for (
        name,
        type_name,
        _,
    ) in non_numeric_concepts:
        examples.setdefault(
            type_name,
            [],
        )

        if len(examples[type_name]) < 10:
            examples[type_name].append(name)

    for type_name in sorted(examples):
        print()
        print(type_name)

        for name in examples[type_name]:
            print(
                f"  {name}"
            )


def main() -> None:
    """Startet die Analyse."""

    parser = argparse.ArgumentParser(
        description=(
            "Analysiert nichtnumerische "
            "berichtbare Concept-Typen "
            "einer XBRL-Taxonomie."
        )
    )

    parser.add_argument(
        "taxonomy_root",
        type=Path,
        help=(
            "Wurzelverzeichnis der "
            "entpackten Taxonomie"
        ),
    )

    args = parser.parse_args()

    taxonomy_root = args.taxonomy_root

    if not taxonomy_root.is_dir():
        raise SystemExit(
            f"Kein Verzeichnis: {taxonomy_root}"
        )

    analyze_taxonomy(
        taxonomy_root
    )


if __name__ == "__main__":
    main()

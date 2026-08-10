from pathlib import Path

import pytest

from openbilanz.taxonomy.entry_point import (
    TaxonomyEntryPoint,
    TaxonomyEntryPointVariant,
    TaxonomyFamily,
    TaxonomyLinkbaseReference,
    TaxonomyLinkbaseType,
)


@pytest.mark.parametrize(
    ("namespace_suffix", "expected_variant"),
    (
        (
            "shell",
            TaxonomyEntryPointVariant.STANDARD,
        ),
        (
            "shell-fiscal",
            TaxonomyEntryPointVariant.FISCAL,
        ),
        (
            "shell-microbilg",
            TaxonomyEntryPointVariant.MICRO_BILG,
        ),
        (
            "shell-fiscal-microbilg",
            TaxonomyEntryPointVariant.FISCAL_MICRO_BILG,
        ),
        (
            "shell-group",
            TaxonomyEntryPointVariant.GROUP,
        ),
        (
            "shell-staffelform",
            TaxonomyEntryPointVariant.STAFFELFORM,
        ),
        (
            "shell-staffelform-fiscal",
            TaxonomyEntryPointVariant.STAFFELFORM_FISCAL,
        ),
    ),
)
def test_entry_point_resolves_variant(
    namespace_suffix: str,
    expected_variant: TaxonomyEntryPointVariant,
) -> None:
    entry_point = TaxonomyEntryPoint(
        path=Path("test-shell.xsd"),
        namespace=(
            "http://www.xbrl.de/taxonomies/"
            f"de-gaap-ci-2024-04-01/{namespace_suffix}"
        ),
        schema_imports=(),
    )

    assert entry_point.variant is expected_variant

@pytest.mark.parametrize(
    ("role_suffix", "expected_type"),
    (
        (
            "presentationLinkbaseRef",
            TaxonomyLinkbaseType.PRESENTATION,
        ),
        (
            "calculationLinkbaseRef",
            TaxonomyLinkbaseType.CALCULATION,
        ),
        (
            "definitionLinkbaseRef",
            TaxonomyLinkbaseType.DEFINITION,
        ),
        (
            "labelLinkbaseRef",
            TaxonomyLinkbaseType.LABEL,
        ),
        (
            "referenceLinkbaseRef",
            TaxonomyLinkbaseType.REFERENCE,
        ),
        (
            "customLinkbaseRef",
            TaxonomyLinkbaseType.OTHER,
        ),
    ),
)
def test_linkbase_reference_resolves_known_types(
    role_suffix: str,
    expected_type: TaxonomyLinkbaseType,
) -> None:
    """Bekannte Linkbase-Rollen werden fachlich klassifiziert."""

    reference = TaxonomyLinkbaseReference(
        href="test.xml",
        role=(
            "http://www.xbrl.org/2003/role/"
            f"{role_suffix}"
        ),
    )

    assert reference.type is expected_type
    

def test_entry_point_reads_shell_metadata(tmp_path: Path) -> None:
    shell = tmp_path / "de-gaap-ci-2024-04-01-shell.xsd"

    shell.write_text(
        """<?xml version="1.0" encoding="utf-8"?>
<xs:schema
    xmlns:xs="http://www.w3.org/2001/XMLSchema"
    targetNamespace="http://www.xbrl.de/taxonomies/de-gaap-ci-2024-04-01/shell">

    <xs:import
        namespace="http://www.xbrl.de/taxonomies/de-gaap-ci-2024-04-01"
        schemaLocation="de-gaap-ci-2024-04-01.xsd"/>

</xs:schema>
""",
        encoding="utf-8",
    )

    entry_point = TaxonomyEntryPoint.from_file(shell)

    assert entry_point.path == shell
    assert (
        entry_point.namespace
        == "http://www.xbrl.de/taxonomies/de-gaap-ci-2024-04-01/shell"
    )
    assert entry_point.schema_imports == (
        "de-gaap-ci-2024-04-01.xsd",
    )
    

def test_entry_point_reads_linkbase_references(
    tmp_path: Path,
) -> None:
    """Ein Entry Point liest seine Linkbase-Referenzen."""

    shell = tmp_path / "de-gaap-ci-2024-04-01-shell.xsd"

    shell.write_text(
        """<?xml version="1.0" encoding="utf-8"?>
<xs:schema
    xmlns:xs="http://www.w3.org/2001/XMLSchema"
    xmlns:link="http://www.xbrl.org/2003/linkbase"
    xmlns:xlink="http://www.w3.org/1999/xlink"
    targetNamespace="http://www.xbrl.de/taxonomies/de-gaap-ci-2024-04-01/shell">

    <xs:annotation>
        <xs:appinfo>
            <link:linkbaseRef
                xlink:type="simple"
                xlink:href="presentation-balanceSheet.xml"
                xlink:role="http://www.xbrl.org/2003/role/presentationLinkbaseRef"/>

            <link:linkbaseRef
                xlink:type="simple"
                xlink:href="calculation-balanceSheet.xml"
                xlink:role="http://www.xbrl.org/2003/role/calculationLinkbaseRef"/>
        </xs:appinfo>
    </xs:annotation>

    <xs:import
        namespace="http://www.xbrl.de/taxonomies/de-gaap-ci-2024-04-01"
        schemaLocation="de-gaap-ci-2024-04-01.xsd"/>

</xs:schema>
""",
        encoding="utf-8",
    )

    entry_point = TaxonomyEntryPoint.from_file(
        shell
    )

    assert entry_point.linkbase_references == (
        TaxonomyLinkbaseReference(
            href="presentation-balanceSheet.xml",
            role=(
                "http://www.xbrl.org/2003/role/"
                "presentationLinkbaseRef"
            ),
        ),
        TaxonomyLinkbaseReference(
            href="calculation-balanceSheet.xml",
            role=(
                "http://www.xbrl.org/2003/role/"
                "calculationLinkbaseRef"
            ),
        ),
    )


def test_linkbase_reference_resolves_type() -> None:
    """Eine Linkbase-Referenz erkennt ihren fachlichen Typ."""

    reference = TaxonomyLinkbaseReference(
        href="presentation-balanceSheet.xml",
        role=(
            "http://www.xbrl.org/2003/role/"
            "presentationLinkbaseRef"
        ),
    )

    assert reference.type is TaxonomyLinkbaseType.PRESENTATION


def test_entry_point_resolves_taxonomy_family() -> None:
    entry_point = TaxonomyEntryPoint(
        path=Path(
            "xbrl/de-gaap-ci-2024-04-01/"
            "de-gaap-ci-2024-04-01-shell.xsd"
        ),
        namespace=(
            "http://www.xbrl.de/taxonomies/"
            "de-gaap-ci-2024-04-01/shell"
        ),
        schema_imports=(),
    )

    assert entry_point.family is TaxonomyFamily.GAAP_CI
    

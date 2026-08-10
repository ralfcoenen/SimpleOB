from pathlib import Path

import pytest

from openbilanz.taxonomy.entry_point import (
    TaxonomyEntryPoint,
    TaxonomyEntryPointVariant,
    TaxonomyFamily,
)
from openbilanz.taxonomy.package import TaxonomyPackage
from openbilanz.taxonomy.taxonomy import TaxonomyVersion


def test_taxonomy_package_stores_version_and_entry_points() -> None:
    entry_point = TaxonomyEntryPoint(
        path=Path("de-gaap-ci-shell.xsd"),
        namespace="http://example.test/shell",
        schema_imports=("de-gaap-ci.xsd",),
    )

    package = TaxonomyPackage(
        name="German GAAP Taxonomy 6.8",
        version=TaxonomyVersion.V6_8,
        entry_points=(entry_point,),
    )

    assert package.name == "German GAAP Taxonomy 6.8"
    assert package.version is TaxonomyVersion.V6_8
    assert package.entry_points == (entry_point,)
    

def test_taxonomy_package_rejects_blank_name() -> None:
    """Ein leerer Paketname ist unzulässig."""

    with pytest.raises(
        ValueError,
        match="name must not be blank",
    ):
        TaxonomyPackage(
            name="",
            version=TaxonomyVersion.V6_8,
            entry_points=(),
        )


def test_taxonomy_package_rejects_invalid_entry_points() -> None:
    """Entry Points müssen TaxonomyEntryPoint-Objekte sein."""

    with pytest.raises(
        TypeError,
        match=(
            "entry_points must contain only "
            "TaxonomyEntryPoint objects"
        ),
    ):
        TaxonomyPackage(
            name="German GAAP Taxonomy 6.8",
            version=TaxonomyVersion.V6_8,
            entry_points=("invalid",),  # type: ignore[arg-type]
        )

def test_taxonomy_package_loads_entry_points_from_directory(
    tmp_path: Path,
) -> None:
    """Ein Paket lädt Shell-XSDs rekursiv als Entry Points."""

    taxonomy_dir = tmp_path / "xbrl" / "de-gaap-ci-2024-04-01"
    taxonomy_dir.mkdir(parents=True)

    shell = taxonomy_dir / "de-gaap-ci-2024-04-01-shell.xsd"

    shell.write_text(
        """<?xml version="1.0" encoding="utf-8"?>
<xs:schema
    xmlns:xs="http://www.w3.org/2001/XMLSchema"
    targetNamespace="http://example.test/shell">

    <xs:import
        namespace="http://example.test/core"
        schemaLocation="core.xsd"/>

</xs:schema>
""",
        encoding="utf-8",
    )

    package = TaxonomyPackage.from_directory(
        root=tmp_path,
        name="German GAAP Taxonomy 6.8",
        version=TaxonomyVersion.V6_8,
    )

    assert len(package.entry_points) == 1
    assert package.entry_points[0].path == shell
    assert package.entry_points[0].namespace == (
        "http://example.test/shell"
    )

def test_taxonomy_package_loads_multiple_entry_points_in_order(
    tmp_path: Path,
) -> None:
    """Mehrere Shell-XSDs werden rekursiv und sortiert geladen."""

    first_dir = tmp_path / "xbrl" / "a"
    second_dir = tmp_path / "xbrl" / "b"

    first_dir.mkdir(parents=True)
    second_dir.mkdir(parents=True)

    first_shell = first_dir / "a-shell.xsd"
    second_shell = second_dir / "b-shell.xsd"

    first_shell.write_text(
        """<?xml version="1.0" encoding="utf-8"?>
<xs:schema
    xmlns:xs="http://www.w3.org/2001/XMLSchema"
    targetNamespace="http://example.test/a">
</xs:schema>
""",
        encoding="utf-8",
    )

    second_shell.write_text(
        """<?xml version="1.0" encoding="utf-8"?>
<xs:schema
    xmlns:xs="http://www.w3.org/2001/XMLSchema"
    targetNamespace="http://example.test/b">
</xs:schema>
""",
        encoding="utf-8",
    )

    package = TaxonomyPackage.from_directory(
        root=tmp_path,
        name="Test Taxonomy",
        version=TaxonomyVersion.V6_8,
    )

    assert tuple(
        entry_point.path
        for entry_point in package.entry_points
    ) == (
        first_shell,
        second_shell,
    )

def test_taxonomy_package_filters_entry_points_by_family() -> None:
    """Entry Points können nach Taxonomiefamilie gefiltert werden."""

    gaap_ci = TaxonomyEntryPoint(
        path=Path("de-gaap-ci-shell.xsd"),
        namespace=(
            "http://www.xbrl.de/taxonomies/"
            "de-gaap-ci-2024-04-01/shell"
        ),
        schema_imports=(),
    )

    gcd = TaxonomyEntryPoint(
        path=Path("de-gcd-shell.xsd"),
        namespace=(
            "http://www.xbrl.de/taxonomies/"
            "de-gcd-2024-04-01/shell"
        ),
        schema_imports=(),
    )

    package = TaxonomyPackage(
        name="German GAAP Taxonomy 6.8",
        version=TaxonomyVersion.V6_8,
        entry_points=(gaap_ci, gcd),
    )

    assert package.entry_points_for(
        family=TaxonomyFamily.GAAP_CI,
    ) == (gaap_ci,)


def test_taxonomy_package_filters_entry_points_by_variant() -> None:
    """Entry Points können nach ihrer Variante gefiltert werden."""

    standard = TaxonomyEntryPoint(
        path=Path("de-gaap-ci-shell.xsd"),
        namespace=(
            "http://www.xbrl.de/taxonomies/"
            "de-gaap-ci-2024-04-01/shell"
        ),
        schema_imports=(),
    )

    fiscal = TaxonomyEntryPoint(
        path=Path("de-gaap-ci-shell-fiscal.xsd"),
        namespace=(
            "http://www.xbrl.de/taxonomies/"
            "de-gaap-ci-2024-04-01/shell-fiscal"
        ),
        schema_imports=(),
    )

    package = TaxonomyPackage(
        name="German GAAP Taxonomy 6.8",
        version=TaxonomyVersion.V6_8,
        entry_points=(standard, fiscal),
    )

    assert package.entry_points_for(
        variant=TaxonomyEntryPointVariant.FISCAL,
    ) == (fiscal,)

def test_taxonomy_package_filters_by_family_and_variant() -> None:
    """Familie und Variante können gemeinsam gefiltert werden."""

    gaap_standard = TaxonomyEntryPoint(
        path=Path("gaap-standard.xsd"),
        namespace=(
            "http://www.xbrl.de/taxonomies/"
            "de-gaap-ci-2024-04-01/shell"
        ),
        schema_imports=(),
    )

    gaap_fiscal = TaxonomyEntryPoint(
        path=Path("gaap-fiscal.xsd"),
        namespace=(
            "http://www.xbrl.de/taxonomies/"
            "de-gaap-ci-2024-04-01/shell-fiscal"
        ),
        schema_imports=(),
    )

    bra_fiscal = TaxonomyEntryPoint(
        path=Path("bra-fiscal.xsd"),
        namespace=(
            "http://www.xbrl.de/taxonomies/"
            "de-bra-2024-04-01/shell-fiscal"
        ),
        schema_imports=(),
    )

    package = TaxonomyPackage(
        name="German GAAP Taxonomy 6.8",
        version=TaxonomyVersion.V6_8,
        entry_points=(
            gaap_standard,
            gaap_fiscal,
            bra_fiscal,
        ),
    )

    assert package.entry_points_for(
        family=TaxonomyFamily.GAAP_CI,
        variant=TaxonomyEntryPointVariant.FISCAL,
    ) == (gaap_fiscal,)


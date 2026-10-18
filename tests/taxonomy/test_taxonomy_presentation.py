"""Tests für Presentation-Beziehungen einer XBRL-Taxonomie."""

from decimal import Decimal
from pathlib import Path

from simpleob.taxonomy.presentation import (
    TaxonomyPresentationRelation,
)


def test_presentation_relations_are_loaded_from_linkbase(
    tmp_path: Path,
) -> None:
    """Parent-Child-Beziehungen werden aus einer Linkbase geladen."""

    linkbase = tmp_path / "presentation.xml"

    linkbase.write_text(
        """<?xml version="1.0" encoding="utf-8"?>
<link:linkbase
    xmlns:link="http://www.xbrl.org/2003/linkbase"
    xmlns:xlink="http://www.w3.org/1999/xlink">

    <link:presentationLink
        xlink:type="extended"
        xlink:role="http://example.test/role/balanceSheet">

        <link:loc
            xlink:type="locator"
            xlink:href="taxonomy.xsd#concept_assets"
            xlink:label="loc_assets"/>

        <link:loc
            xlink:type="locator"
            xlink:href="taxonomy.xsd#concept_fixed_assets"
            xlink:label="loc_fixed_assets"/>

        <link:presentationArc
            xlink:type="arc"
            xlink:arcrole="http://www.xbrl.org/2003/arcrole/parent-child"
            xlink:from="loc_assets"
            xlink:to="loc_fixed_assets"
            order="2.5"/>

    </link:presentationLink>

</link:linkbase>
""",
        encoding="utf-8",
    )

    relations = TaxonomyPresentationRelation.from_linkbase(
        linkbase
    )

    assert relations == (
        TaxonomyPresentationRelation(
            parent_concept_id="concept_assets",
            child_concept_id="concept_fixed_assets",
            order=Decimal("2.5"),
            role_uri="http://example.test/role/balanceSheet",
            preferred_label_role_uri=None,
        ),
    )

def test_multiple_presentation_links_are_loaded_separately(
    tmp_path: Path,
) -> None:
    """Mehrere Presentation-Netzwerke werden getrennt ausgewertet."""

    linkbase = tmp_path / "presentation.xml"

    linkbase.write_text(
        """<?xml version="1.0" encoding="utf-8"?>
<link:linkbase
    xmlns:link="http://www.xbrl.org/2003/linkbase"
    xmlns:xlink="http://www.w3.org/1999/xlink">

    <link:presentationLink
        xlink:type="extended"
        xlink:role="http://example.test/role/first">

        <link:loc
            xlink:type="locator"
            xlink:href="taxonomy.xsd#concept_a"
            xlink:label="loc_parent"/>

        <link:loc
            xlink:type="locator"
            xlink:href="taxonomy.xsd#concept_b"
            xlink:label="loc_child"/>

        <link:presentationArc
            xlink:type="arc"
            xlink:arcrole="http://www.xbrl.org/2003/arcrole/parent-child"
            xlink:from="loc_parent"
            xlink:to="loc_child"
            order="1"/>

    </link:presentationLink>

    <link:presentationLink
        xlink:type="extended"
        xlink:role="http://example.test/role/second">

        <link:loc
            xlink:type="locator"
            xlink:href="taxonomy.xsd#concept_c"
            xlink:label="loc_parent"/>

        <link:loc
            xlink:type="locator"
            xlink:href="taxonomy.xsd#concept_d"
            xlink:label="loc_child"/>

        <link:presentationArc
            xlink:type="arc"
            xlink:arcrole="http://www.xbrl.org/2003/arcrole/parent-child"
            xlink:from="loc_parent"
            xlink:to="loc_child"
            order="2"/>

    </link:presentationLink>

</link:linkbase>
""",
        encoding="utf-8",
    )

    relations = TaxonomyPresentationRelation.from_linkbase(
        linkbase
    )

    assert relations == (
        TaxonomyPresentationRelation(
            parent_concept_id="concept_a",
            child_concept_id="concept_b",
            order=Decimal("1"),
            role_uri="http://example.test/role/first",
            preferred_label_role_uri=None,
        ),
        TaxonomyPresentationRelation(
            parent_concept_id="concept_c",
            child_concept_id="concept_d",
            order=Decimal("2"),
            role_uri="http://example.test/role/second",
            preferred_label_role_uri=None,
        ),
    )

def test_presentation_relation_preserves_preferred_label(
    tmp_path: Path,
) -> None:
    """Die bevorzugte Label-Rolle eines Presentation-Arcs bleibt erhalten."""

    linkbase = tmp_path / "presentation.xml"

    linkbase.write_text(
        """<?xml version="1.0" encoding="utf-8"?>
<link:linkbase
    xmlns:link="http://www.xbrl.org/2003/linkbase"
    xmlns:xlink="http://www.w3.org/1999/xlink">

    <link:presentationLink
        xlink:type="extended"
        xlink:role="http://example.test/role/balanceSheet">

        <link:loc
            xlink:type="locator"
            xlink:href="taxonomy.xsd#concept_assets"
            xlink:label="loc_assets"/>

        <link:loc
            xlink:type="locator"
            xlink:href="taxonomy.xsd#concept_fixed_assets"
            xlink:label="loc_fixed_assets"/>

        <link:presentationArc
            xlink:type="arc"
            xlink:arcrole="http://www.xbrl.org/2003/arcrole/parent-child"
            xlink:from="loc_assets"
            xlink:to="loc_fixed_assets"
            order="1"
            preferredLabel="http://www.xbrl.org/2003/role/terseLabel"/>

    </link:presentationLink>

</link:linkbase>
""",
        encoding="utf-8",
    )

    relations = TaxonomyPresentationRelation.from_linkbase(
        linkbase
    )

    assert relations[0].preferred_label_role_uri == (
        "http://www.xbrl.org/2003/role/terseLabel"
    )
    

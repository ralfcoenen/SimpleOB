"""Tests für Labels einer XBRL-Taxonomie."""

from pathlib import Path

from simpleob.taxonomy.label import (
    TaxonomyLabel,
    TaxonomyLabelRole,
)


def test_taxonomy_labels_are_loaded_from_linkbase(
    tmp_path: Path,
) -> None:
    """Labels werden über Locator und LabelArc Concepts zugeordnet."""

    linkbase = tmp_path / "label-de.xml"

    linkbase.write_text(
        """<?xml version="1.0" encoding="utf-8"?>
<link:linkbase
    xmlns:link="http://www.xbrl.org/2003/linkbase"
    xmlns:xlink="http://www.w3.org/1999/xlink">

    <link:labelLink
        xlink:type="extended"
        xlink:role="http://www.xbrl.org/2003/role/link">

        <link:loc
            xlink:type="locator"
            xlink:href="taxonomy.xsd#concept_assets"
            xlink:label="loc_assets"/>

        <link:label
            xlink:type="resource"
            xlink:label="label_assets"
            xlink:role="http://www.xbrl.org/2003/role/label"
            xml:lang="de">Aktiva</link:label>

        <link:labelArc
            xlink:type="arc"
            xlink:arcrole="http://www.xbrl.org/2003/arcrole/concept-label"
            xlink:from="loc_assets"
            xlink:to="label_assets"/>

    </link:labelLink>

</link:linkbase>
""",
        encoding="utf-8",
    )

    labels = TaxonomyLabel.from_linkbase(
        linkbase
    )

    assert labels == (
        TaxonomyLabel(
            concept_id="concept_assets",
            text="Aktiva",
            role=TaxonomyLabelRole.LABEL,
            role_uri="http://www.xbrl.org/2003/role/label",
            language="de",
        ),
    )


def test_taxonomy_concept_can_have_multiple_labels(
    tmp_path: Path,
) -> None:
    """Ein Concept kann mehrere Labels mit unterschiedlichen Rollen haben."""

    linkbase = tmp_path / "label-de.xml"

    linkbase.write_text(
        """<?xml version="1.0" encoding="utf-8"?>
<link:linkbase
    xmlns:link="http://www.xbrl.org/2003/linkbase"
    xmlns:xlink="http://www.w3.org/1999/xlink">

    <link:labelLink
        xlink:type="extended"
        xlink:role="http://www.xbrl.org/2003/role/link">

        <link:loc
            xlink:type="locator"
            xlink:href="taxonomy.xsd#concept_assets"
            xlink:label="loc_assets"/>

        <link:label
            xlink:type="resource"
            xlink:label="label_assets_standard"
            xlink:role="http://www.xbrl.org/2003/role/label"
            xml:lang="de">Aktiva</link:label>

        <link:label
            xlink:type="resource"
            xlink:label="label_assets_terse"
            xlink:role="http://www.xbrl.org/2003/role/terseLabel"
            xml:lang="de">Aktiva kurz</link:label>

        <link:labelArc
            xlink:type="arc"
            xlink:arcrole="http://www.xbrl.org/2003/arcrole/concept-label"
            xlink:from="loc_assets"
            xlink:to="label_assets_standard"/>

        <link:labelArc
            xlink:type="arc"
            xlink:arcrole="http://www.xbrl.org/2003/arcrole/concept-label"
            xlink:from="loc_assets"
            xlink:to="label_assets_terse"/>

    </link:labelLink>

</link:linkbase>
""",
        encoding="utf-8",
    )

    labels = TaxonomyLabel.from_linkbase(
        linkbase
    )

    assert labels == (
        TaxonomyLabel(
            concept_id="concept_assets",
            text="Aktiva",
            role=TaxonomyLabelRole.LABEL,
            role_uri="http://www.xbrl.org/2003/role/label",
            language="de",
        ),
        TaxonomyLabel(
            concept_id="concept_assets",
            text="Aktiva kurz",
            role=TaxonomyLabelRole.TERSE_LABEL,
            role_uri="http://www.xbrl.org/2003/role/terseLabel",
            language="de",
        ),
    )


def test_taxonomy_label_maps_standard_role(
    tmp_path: Path,
) -> None:
    """Die Standard-Label-Rolle wird typisiert."""

    linkbase = tmp_path / "label-de.xml"

    linkbase.write_text(
        """<?xml version="1.0" encoding="utf-8"?>
<link:linkbase
    xmlns:link="http://www.xbrl.org/2003/linkbase"
    xmlns:xlink="http://www.w3.org/1999/xlink">

    <link:labelLink
        xlink:type="extended"
        xlink:role="http://www.xbrl.org/2003/role/link">

        <link:loc
            xlink:type="locator"
            xlink:href="taxonomy.xsd#concept_assets"
            xlink:label="loc_assets"/>

        <link:label
            xlink:type="resource"
            xlink:label="label_assets"
            xlink:role="http://www.xbrl.org/2003/role/label"
            xml:lang="de">Aktiva</link:label>

        <link:labelArc
            xlink:type="arc"
            xlink:arcrole="http://www.xbrl.org/2003/arcrole/concept-label"
            xlink:from="loc_assets"
            xlink:to="label_assets"/>

    </link:labelLink>

</link:linkbase>
""",
        encoding="utf-8",
    )

    labels = TaxonomyLabel.from_linkbase(
        linkbase
    )

    assert labels[0].role is TaxonomyLabelRole.LABEL
    assert labels[0].role_uri == (
        "http://www.xbrl.org/2003/role/label"
    )


def test_taxonomy_label_maps_unknown_role_to_other(
    tmp_path: Path,
) -> None:
    """Eine unbekannte Label-Rolle wird als OTHER behandelt."""

    linkbase = tmp_path / "label-de.xml"

    linkbase.write_text(
        """<?xml version="1.0" encoding="utf-8"?>
<link:linkbase
    xmlns:link="http://www.xbrl.org/2003/linkbase"
    xmlns:xlink="http://www.w3.org/1999/xlink">

    <link:labelLink
        xlink:type="extended"
        xlink:role="http://www.xbrl.org/2003/role/link">

        <link:loc
            xlink:type="locator"
            xlink:href="taxonomy.xsd#concept_assets"
            xlink:label="loc_assets"/>

        <link:label
            xlink:type="resource"
            xlink:label="label_assets"
            xlink:role="http://example.test/role/customLabel"
            xml:lang="de">Aktiva</link:label>

        <link:labelArc
            xlink:type="arc"
            xlink:arcrole="http://www.xbrl.org/2003/arcrole/concept-label"
            xlink:from="loc_assets"
            xlink:to="label_assets"/>

    </link:labelLink>

</link:linkbase>
""",
        encoding="utf-8",
    )

    labels = TaxonomyLabel.from_linkbase(
        linkbase
    )

    assert labels[0].role is TaxonomyLabelRole.OTHER
    assert labels[0].role_uri == (
        "http://example.test/role/customLabel"
    )

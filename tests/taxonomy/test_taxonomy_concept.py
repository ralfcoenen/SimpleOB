"""Tests für Konzepte einer XBRL-Taxonomie."""
from pathlib import Path

import pytest

from openbilanz.taxonomy.concept import (
    TaxonomyBalance,
    TaxonomyConcept,
    TaxonomyPeriodType,
)


def test_taxonomy_concepts_are_loaded_from_schema(
    tmp_path: Path,
) -> None:
    """XSD-Elemente werden als Taxonomiekonzepte geladen."""

    schema = tmp_path / "de-gaap-ci-test.xsd"

    schema.write_text(
        """<?xml version="1.0" encoding="utf-8"?>
<xs:schema
    xmlns:xs="http://www.w3.org/2001/XMLSchema"
    xmlns:xbrli="http://www.xbrl.org/2003/instance"
    targetNamespace="http://example.test/de-gaap-ci">

    <xs:element
        name="bs.ass"
        id="de-gaap-ci_bs.ass"
        type="xbrli:monetaryItemType"
        substitutionGroup="xbrli:item"
        xbrli:periodType="instant"
        xbrli:balance="debit"
        abstract="false"
        nillable="true"/>

    <xs:element
        name="is.netIncome"
        id="de-gaap-ci_is.netIncome"
        type="xbrli:monetaryItemType"
        substitutionGroup="xbrli:item"
        xbrli:periodType="duration"
        xbrli:balance="credit"
        abstract="true"
        nillable="false"/>

</xs:schema>
""",
        encoding="utf-8",
    )

    concepts = TaxonomyConcept.from_schema(
        schema
    )

    assert concepts == (
        TaxonomyConcept(
            name="bs.ass",
            concept_id="de-gaap-ci_bs.ass",
            type_name="xbrli:monetaryItemType",
            substitution_group="xbrli:item",
            period_type=TaxonomyPeriodType.INSTANT,
            balance=TaxonomyBalance.DEBIT,
            abstract=False,
            nillable=True,
        ),
        TaxonomyConcept(
            name="is.netIncome",
            concept_id="de-gaap-ci_is.netIncome",
            type_name="xbrli:monetaryItemType",
            substitution_group="xbrli:item",
            period_type=TaxonomyPeriodType.DURATION,
            balance=TaxonomyBalance.CREDIT,
            abstract=True,
            nillable=False,
        ),
    )


def test_taxonomy_concept_supports_numeric_xml_booleans(
    tmp_path: Path,
) -> None:
    """XML-Boolean 1 und 0 werden korrekt ausgewertet."""

    schema = tmp_path / "test.xsd"

    schema.write_text(
        """<?xml version="1.0" encoding="utf-8"?>
<xs:schema
    xmlns:xs="http://www.w3.org/2001/XMLSchema">

    <xs:element
        name="first"
        id="first"
        abstract="1"
        nillable="0"/>

</xs:schema>
""",
        encoding="utf-8",
    )

    concepts = TaxonomyConcept.from_schema(
        schema
    )

    assert concepts == (
        TaxonomyConcept(
            name="first",
            concept_id="first",
            type_name=None,
            substitution_group=None,
            period_type=TaxonomyPeriodType.UNKNOWN,
            balance=TaxonomyBalance.NONE,
            abstract=True,
            nillable=False,
        ),
    )


def test_taxonomy_concept_ignores_elements_without_id(
    tmp_path: Path,
) -> None:
    """XSD-Elemente ohne Concept-ID werden ignoriert."""

    schema = tmp_path / "test.xsd"

    schema.write_text(
        """<?xml version="1.0" encoding="utf-8"?>
<xs:schema
    xmlns:xs="http://www.w3.org/2001/XMLSchema">

    <xs:element
        name="without-id"/>

    <xs:element
        name="with-id"
        id="with-id"/>

</xs:schema>
""",
        encoding="utf-8",
    )

    concepts = TaxonomyConcept.from_schema(
        schema
    )

    assert concepts == (
        TaxonomyConcept(
            name="with-id",
            concept_id="with-id",
            type_name=None,
            substitution_group=None,
            period_type=TaxonomyPeriodType.UNKNOWN,
            balance=TaxonomyBalance.NONE,
            abstract=False,
            nillable=False,
        ),
    )

@pytest.mark.parametrize(
    ("type_name", "expected"),
    (
        ("xbrli:monetaryItemType", True),
        ("xbrli:decimalItemType", True),
        ("xbrli:pureItemType", True),
        ("xbrli:longItemType", True),
        ("xbrli:stringItemType", False),
        ("xbrli:dateItemType", False),
        ("xbrli:booleanItemType", False),
        ("xbrli:QNameItemType", False),
        ("xbrli:anyURIItemType", False),
        (None, False),
    ),
)
def test_taxonomy_concept_identifies_numeric_types(
    type_name: str | None,
    expected: bool,
) -> None:
    """Numerische XBRL-Typen werden korrekt erkannt."""

    concept = TaxonomyConcept(
        name="test",
        concept_id="test",
        type_name=type_name,
        substitution_group="xbrli:item",
        period_type=TaxonomyPeriodType.DURATION,
        balance=TaxonomyBalance.NONE,
        abstract=False,
        nillable=True,
    )

    assert concept.is_numeric is expected


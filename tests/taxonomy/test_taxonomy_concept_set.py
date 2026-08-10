"""Tests für die Abfrage von Taxonomie-Concepts."""
from pathlib import Path

import pytest

from openbilanz.taxonomy.concept import (
    TaxonomyBalance,
    TaxonomyConcept,
    TaxonomyPeriodType,
)
from openbilanz.taxonomy.concept_set import TaxonomyConceptSet


def _concept(
    *,
    name: str,
    concept_id: str,
) -> TaxonomyConcept:
    """Erzeugt ein einfaches Taxonomie-Concept für Tests."""

    return TaxonomyConcept(
        name=name,
        concept_id=concept_id,
        type_name="xbrli:monetaryItemType",
        substitution_group="xbrli:item",
        period_type=TaxonomyPeriodType.INSTANT,
        balance=TaxonomyBalance.DEBIT,
        abstract=False,
        nillable=True,
    )


def test_concept_can_be_found_by_id() -> None:
    """Ein Concept kann über seine XSD-ID gefunden werden."""

    assets = _concept(
        name="bs.ass",
        concept_id="de-gaap-ci_bs.ass",
    )

    liabilities = _concept(
        name="bs.eqLiab",
        concept_id="de-gaap-ci_bs.eqLiab",
    )

    concept_set = TaxonomyConceptSet(
        concepts=(
            assets,
            liabilities,
        )
    )

    assert concept_set.by_id(
        "de-gaap-ci_bs.ass"
    ) is assets


def test_unknown_concept_id_returns_none() -> None:
    """Eine unbekannte Concept-ID liefert None."""

    concept_set = TaxonomyConceptSet(
        concepts=()
    )

    assert concept_set.by_id(
        "unknown"
    ) is None

def test_concept_set_rejects_invalid_concepts() -> None:
    """Ein ConceptSet akzeptiert nur TaxonomyConcept-Objekte."""

    with pytest.raises(
        TypeError,
        match=(
            "concepts must contain only "
            "TaxonomyConcept objects"
        ),
    ):
        TaxonomyConceptSet(
            concepts=("invalid",),  # type: ignore[arg-type]
        )


def test_concept_set_rejects_duplicate_concept_ids() -> None:
    """Concept-IDs müssen innerhalb eines Sets eindeutig sein."""

    first = _concept(
        name="bs.ass",
        concept_id="de-gaap-ci_bs.ass",
    )

    duplicate = _concept(
        name="bs.ass.other",
        concept_id="de-gaap-ci_bs.ass",
    )

    with pytest.raises(
        ValueError,
        match="duplicate concept ids are not allowed",
    ):
        TaxonomyConceptSet(
            concepts=(
                first,
                duplicate,
            )
        )

def test_concept_set_can_be_loaded_from_multiple_schemas(
    tmp_path: Path,
) -> None:
    """Concepts aus mehreren XSD-Schemas werden zusammengeführt."""

    first_schema = tmp_path / "first.xsd"
    second_schema = tmp_path / "second.xsd"

    first_schema.write_text(
        """<?xml version="1.0" encoding="utf-8"?>
<xs:schema
    xmlns:xs="http://www.w3.org/2001/XMLSchema"
    xmlns:xbrli="http://www.xbrl.org/2003/instance">

    <xs:element
        name="concept_a"
        id="concept_a"
        type="xbrli:stringItemType"
        substitutionGroup="xbrli:item"
        xbrli:periodType="duration"
        nillable="true"/>

</xs:schema>
""",
        encoding="utf-8",
    )

    second_schema.write_text(
        """<?xml version="1.0" encoding="utf-8"?>
<xs:schema
    xmlns:xs="http://www.w3.org/2001/XMLSchema"
    xmlns:xbrli="http://www.xbrl.org/2003/instance">

    <xs:element
        name="concept_b"
        id="concept_b"
        type="xbrli:stringItemType"
        substitutionGroup="xbrli:item"
        xbrli:periodType="instant"
        nillable="true"/>

</xs:schema>
""",
        encoding="utf-8",
    )

    concept_set = TaxonomyConceptSet.from_schemas(
        paths=(
            first_schema,
            second_schema,
        )
    )

    assert tuple(
        concept.concept_id
        for concept in concept_set.concepts
    ) == (
        "concept_a",
        "concept_b",
    )




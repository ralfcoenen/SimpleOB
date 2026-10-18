"""Tests für die Abfrage von Taxonomie-Labels."""

from simpleob.taxonomy.label import (
    TaxonomyLabel,
    TaxonomyLabelRole,
)
from simpleob.taxonomy.label_set import TaxonomyLabelSet


def test_labels_for_concept_returns_all_matching_labels() -> None:
    """Alle Labels eines Concepts können abgefragt werden."""

    labels = (
        TaxonomyLabel(
            concept_id="concept_assets",
            text="Bilanzsumme, Summe Aktiva",
            role=TaxonomyLabelRole.LABEL,
            role_uri="http://www.xbrl.org/2003/role/label",
            language="de",
        ),
        TaxonomyLabel(
            concept_id="concept_assets",
            text="Summe Aktiva",
            role=TaxonomyLabelRole.TERSE_LABEL,
            role_uri="http://www.xbrl.org/2003/role/terseLabel",
            language="de",
        ),
        TaxonomyLabel(
            concept_id="concept_liabilities",
            text="Summe Passiva",
            role=TaxonomyLabelRole.TERSE_LABEL,
            role_uri="http://www.xbrl.org/2003/role/terseLabel",
            language="de",
        ),
    )

    label_set = TaxonomyLabelSet(
        labels=labels
    )

    assert label_set.for_concept(
        "concept_assets"
    ) == (
        labels[0],
        labels[1],
    )

def test_labels_for_unknown_concept_returns_empty_tuple() -> None:
    """Für ein unbekanntes Concept wird eine leere Folge geliefert."""

    label_set = TaxonomyLabelSet(
        labels=()
    )

    assert label_set.for_concept(
        "unknown"
    ) == ()


def test_label_set_rejects_invalid_labels() -> None:
    """Ein LabelSet akzeptiert nur TaxonomyLabel-Objekte."""

    import pytest

    with pytest.raises(
        TypeError,
        match=(
            "labels must contain only "
            "TaxonomyLabel objects"
        ),
    ):
        TaxonomyLabelSet(
            labels=("invalid",),  # type: ignore[arg-type]
        )
        
def test_labels_for_concept_can_filter_by_language() -> None:
    """Labels können nach Sprache gefiltert werden."""

    german = TaxonomyLabel(
        concept_id="concept_assets",
        text="Aktiva",
        role=TaxonomyLabelRole.LABEL,
        role_uri="http://www.xbrl.org/2003/role/label",
        language="de",
    )

    english = TaxonomyLabel(
        concept_id="concept_assets",
        text="Assets",
        role=TaxonomyLabelRole.LABEL,
        role_uri="http://www.xbrl.org/2003/role/label",
        language="en",
    )

    label_set = TaxonomyLabelSet(
        labels=(german, english)
    )

    assert label_set.for_concept(
        "concept_assets",
        language="de",
    ) == (german,)


def test_labels_for_concept_can_filter_by_role() -> None:
    """Labels können nach ihrer Rolle gefiltert werden."""

    standard = TaxonomyLabel(
        concept_id="concept_assets",
        text="Bilanzsumme, Summe Aktiva",
        role=TaxonomyLabelRole.LABEL,
        role_uri="http://www.xbrl.org/2003/role/label",
        language="de",
    )

    terse = TaxonomyLabel(
        concept_id="concept_assets",
        text="Summe Aktiva",
        role=TaxonomyLabelRole.TERSE_LABEL,
        role_uri="http://www.xbrl.org/2003/role/terseLabel",
        language="de",
    )

    label_set = TaxonomyLabelSet(
        labels=(standard, terse)
    )

    assert label_set.for_concept(
        "concept_assets",
        role=TaxonomyLabelRole.TERSE_LABEL,
    ) == (terse,)

def test_labels_for_concept_can_filter_by_language_and_role() -> None:
    """Sprache und Rolle können gemeinsam gefiltert werden."""

    german_standard = TaxonomyLabel(
        concept_id="concept_assets",
        text="Bilanzsumme, Summe Aktiva",
        role=TaxonomyLabelRole.LABEL,
        role_uri="http://www.xbrl.org/2003/role/label",
        language="de",
    )

    german_terse = TaxonomyLabel(
        concept_id="concept_assets",
        text="Summe Aktiva",
        role=TaxonomyLabelRole.TERSE_LABEL,
        role_uri="http://www.xbrl.org/2003/role/terseLabel",
        language="de",
    )

    english_terse = TaxonomyLabel(
        concept_id="concept_assets",
        text="Total assets",
        role=TaxonomyLabelRole.TERSE_LABEL,
        role_uri="http://www.xbrl.org/2003/role/terseLabel",
        language="en",
    )

    label_set = TaxonomyLabelSet(
        labels=(
            german_standard,
            german_terse,
            english_terse,
        )
    )

    assert label_set.for_concept(
        "concept_assets",
        language="de",
        role=TaxonomyLabelRole.TERSE_LABEL,
    ) == (german_terse,)

   
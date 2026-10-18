"""Tests für taxonomische XBRL-Einheiten."""

import pytest

from simpleob.taxonomy.unit import TaxonomyUnit


def test_taxonomy_unit_rejects_blank_measure() -> None:
    """Eine XBRL-Einheit benötigt ein Measure."""

    with pytest.raises(
        ValueError,
        match="measure must not be blank",
    ):
        TaxonomyUnit(
            measure="",
        )
        
def test_taxonomy_unit_stores_euro_measure() -> None:
    """Die monetäre EUR-Einheit verwendet das XBRL-Measure."""

    unit = TaxonomyUnit(
        measure="iso4217:EUR",
    )

    assert unit.measure == "iso4217:EUR"

def test_taxonomy_unit_creates_euro_unit() -> None:
    """Die EUR-Factory erzeugt die passende XBRL-Einheit."""

    unit = TaxonomyUnit.eur()

    assert unit.measure == "iso4217:EUR"

def test_taxonomy_unit_creates_pure_unit() -> None:
    """Die Pure-Factory erzeugt die dimensionslose XBRL-Einheit."""

    unit = TaxonomyUnit.pure()

    assert unit.measure == "xbrli:pure"


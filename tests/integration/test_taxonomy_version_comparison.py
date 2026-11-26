"""Integrationstests für den Vergleich von Taxonomieversionen."""


from simpleob.taxonomy.arelle_adapter import ArelleAdapter
from simpleob.taxonomy.version_comparison import (
    TaxonomyVersionComparison,
)
from tests.taxonomy_resources import taxonomy_entry_point


def test_taxonomy_version_comparison_detects_added_and_removed_concepts() -> None:
    """Änderungen zwischen Taxonomie 6.8 und 6.9 werden erkannt."""
    ENTRY_POINT_6_8 = taxonomy_entry_point("6.8", kind="gaap-ci")
    ENTRY_POINT_6_9 = taxonomy_entry_point("6.9", kind="gaap-ci")


    adapter = ArelleAdapter()

    try:
        model_6_8 = adapter.model(
            ENTRY_POINT_6_8
        )

        model_6_9 = adapter.model(
            ENTRY_POINT_6_9
        )

        comparison = TaxonomyVersionComparison.compare(
            old_model=model_6_8,
            new_model=model_6_9,
        )

        assert comparison.removed_count == 16
        assert comparison.added_count == 34

        assert (
            "bs.eqLiab.pretaxRes.equityShare"
            in comparison.removed_concept_names
        )

        assert (
            "bs.ass.currAss.receiv.shareholders.particip"
            in comparison.added_concept_names
        )

        assert (
            "bs.ass.fixAss"
            in comparison.unchanged_concept_names
        )

    finally:
        adapter.close()

def test_taxonomy_version_comparison_detects_changes_from_6_9_to_6_10() -> None:
    """Änderungen zwischen Taxonomie 6.9 und 6.10 werden erkannt."""

    entry_point_6_9 = taxonomy_entry_point("6.9")

    entry_point_6_10 = taxonomy_entry_point("6.10")


    adapter = ArelleAdapter()

    try:
        model_6_9 = adapter.model(
            entry_point_6_9
        )

        model_6_10 = adapter.model(
            entry_point_6_10
        )

        comparison = TaxonomyVersionComparison.compare(
            old_model=model_6_9,
            new_model=model_6_10,
        )

        assert comparison.removed_count == 42
        assert comparison.added_count == 38

        assert (
            "bs.ass.currAss.receiv.shareholders.silent"
            in comparison.removed_concept_names
        )

        assert (
            "bs.ass.currAss.receiv.dueCapOfCoop"
            in comparison.added_concept_names
        )

        assert (
            "bs.ass.fixAss"
            in comparison.unchanged_concept_names
        )

    finally:
        adapter.close()


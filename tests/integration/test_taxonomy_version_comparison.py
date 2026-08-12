"""Integrationstests für den Vergleich von Taxonomieversionen."""

from pathlib import Path

import pytest

from openbilanz.taxonomy.arelle_adapter import ArelleAdapter
from openbilanz.taxonomy.version_comparison import (
    TaxonomyVersionComparison,
)

ENTRY_POINT_6_8 = Path(
    "/tmp/openbilanz-taxonomy/6.8/"
    "german-gaap-taxonomy-v6.8-2024-04-01/"
    "xbrl/"
    "de-gaap-ci-2024-04-01/"
    "de-gaap-ci-2024-04-01-shell-fiscal.xsd"
)

ENTRY_POINT_6_9 = Path(
    "/tmp/openbilanz-taxonomy/6.9/"
    "de-gaap-ci-2025-04-01/"
    "de-gaap-ci-2025-04-01-shell-fiscal.xsd"
)


def test_taxonomy_version_comparison_detects_added_and_removed_concepts() -> None:
    """Änderungen zwischen Taxonomie 6.8 und 6.9 werden erkannt."""

    if not ENTRY_POINT_6_8.is_file():
        pytest.skip(
            "Taxonomy 6.8 is not installed locally"
        )

    if not ENTRY_POINT_6_9.is_file():
        pytest.skip(
            "Taxonomy 6.9 is not installed locally"
        )

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

    entry_point_6_9 = Path(
        "/tmp/openbilanz-taxonomy/6.9/"
        "de-gaap-ci-2025-04-01/"
        "de-gaap-ci-2025-04-01-shell-fiscal.xsd"
    )

    entry_point_6_10 = Path(
        "/tmp/openbilanz-taxonomy/6.10/"
        "de-gaap-ci-2026-04-01/"
        "de-gaap-ci-2026-04-01-shell-fiscal.xsd"
    )

    if not entry_point_6_9.is_file():
        pytest.skip(
            "Taxonomy 6.9 is not installed locally"
        )

    if not entry_point_6_10.is_file():
        pytest.skip(
            "Taxonomy 6.10 is not installed locally"
        )

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


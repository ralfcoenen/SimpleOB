"""Integrationstests für Mapping über mehrere Taxonomieversionen."""

from pathlib import Path

import pytest

from openbilanz.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
from openbilanz.accounting.statement_category import StatementCategory
from openbilanz.taxonomy.arelle_adapter import ArelleAdapter
from openbilanz.taxonomy.mapping import TaxonomyMappingRule
from openbilanz.taxonomy.mapping_set import TaxonomyMappingSet


def test_mapping_is_valid_for_taxonomy_6_8_and_6_9() -> None:
    """Dasselbe Mapping kann gegen 6.8 und 6.9 geprüft werden."""

    entry_point_6_8 = Path(
        "/tmp/openbilanz-taxonomy/6.8/"
        "german-gaap-taxonomy-v6.8-2024-04-01/"
        "xbrl/"
        "de-gaap-ci-2024-04-01/"
        "de-gaap-ci-2024-04-01-shell-fiscal.xsd"
    )

    entry_point_6_9 = Path(
        "/tmp/openbilanz-taxonomy/6.9/"
        "de-gaap-ci-2025-04-01/"
        "de-gaap-ci-2025-04-01-shell-fiscal.xsd"
    )

    if not entry_point_6_8.is_file():
        pytest.skip("Taxonomy 6.8 is not installed locally")

    if not entry_point_6_9.is_file():
        pytest.skip("Taxonomy 6.9 is not installed locally")

    position = FinancialStatementPosition(
        code="HGB.266.AKTIVA.A",
        name="Anlagevermögen",
        category=StatementCategory.ASSET,
    )

    mappings = TaxonomyMappingSet(
        rules=(
            TaxonomyMappingRule(
                position=position,
                concept_name="bs.ass.fixAss",
            ),
        )
    )

    adapter = ArelleAdapter()

    try:
        model_6_8 = adapter.model(
            entry_point_6_8
        )

        model_6_9 = adapter.model(
            entry_point_6_9
        )

        result_6_8 = mappings.validate(
            model_6_8
        )

        result_6_9 = mappings.validate(
            model_6_9
        )

        assert result_6_8.is_valid
        assert result_6_9.is_valid

    finally:
        adapter.close()

def test_mapping_detects_concept_removed_between_6_8_and_6_9() -> None:
    """Ein in 6.9 entfallenes Mapping-Ziel wird erkannt."""

    entry_point_6_8 = Path(
        "/tmp/openbilanz-taxonomy/6.8/"
        "german-gaap-taxonomy-v6.8-2024-04-01/"
        "xbrl/"
        "de-gaap-ci-2024-04-01/"
        "de-gaap-ci-2024-04-01-shell-fiscal.xsd"
    )

    entry_point_6_9 = Path(
        "/tmp/openbilanz-taxonomy/6.9/"
        "de-gaap-ci-2025-04-01/"
        "de-gaap-ci-2025-04-01-shell-fiscal.xsd"
    )

    if not entry_point_6_8.is_file():
        pytest.skip("Taxonomy 6.8 is not installed locally")

    if not entry_point_6_9.is_file():
        pytest.skip("Taxonomy 6.9 is not installed locally")

    position = FinancialStatementPosition(
        code="TEST.REMOVED.CONCEPT",
        name="Entfallene Taxonomieposition",
        category=StatementCategory.ASSET,
    )

    concept_name = "bs.eqLiab.pretaxRes.equityShare"

    mappings = TaxonomyMappingSet(
        rules=(
            TaxonomyMappingRule(
                position=position,
                concept_name=concept_name,
            ),
        )
    )

    adapter = ArelleAdapter()

    try:
        model_6_8 = adapter.model(
            entry_point_6_8
        )

        model_6_9 = adapter.model(
            entry_point_6_9
        )

        result_6_8 = mappings.validate(
            model_6_8
        )

        result_6_9 = mappings.validate(
            model_6_9
        )

        assert result_6_8.is_valid
        assert result_6_8.missing_count == 0
        assert result_6_8.missing_concept_names == ()

        assert result_6_9.is_valid is False
        assert result_6_9.valid_count == 0
        assert result_6_9.missing_count == 1
        assert result_6_9.missing_concept_names == (
            concept_name,
        )

    finally:
        adapter.close()
        

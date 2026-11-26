"""Integrationstests für Mapping über mehrere Taxonomieversionen."""


from simpleob.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
from simpleob.accounting.statement_category import StatementCategory
from simpleob.taxonomy.arelle_adapter import ArelleAdapter
from simpleob.taxonomy.mapping import TaxonomyMappingRule
from simpleob.taxonomy.mapping_set import TaxonomyMappingSet
from tests.taxonomy_resources import taxonomy_entry_point


def test_mapping_is_valid_for_taxonomy_6_8_and_6_9() -> None:
    """Dasselbe Mapping kann gegen 6.8 und 6.9 geprüft werden."""

    entry_point_6_8 = taxonomy_entry_point("6.8")

    entry_point_6_9 = taxonomy_entry_point("6.9")


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

    entry_point_6_8 = taxonomy_entry_point("6.8")

    entry_point_6_9 = taxonomy_entry_point("6.9")


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
        

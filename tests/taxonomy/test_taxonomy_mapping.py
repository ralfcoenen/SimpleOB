"""Tests für die Zuordnung interner Abschlusspositionen zur Taxonomie."""

from openbilanz.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
from openbilanz.accounting.statement_category import StatementCategory
from openbilanz.taxonomy.mapping import TaxonomyMappingRule


def test_taxonomy_mapping_rule_stores_position_and_concept_name() -> None:
    """Eine Abschlussposition kann einem Concept-Namen zugeordnet werden."""

    position = FinancialStatementPosition(
        code="bs.ass.fixAss",
        name="Anlagevermögen",
        category=StatementCategory.ASSET,
    )

    rule = TaxonomyMappingRule(
        position=position,
        concept_name="bs.ass.fixAss",
    )

    assert rule.position is position
    assert rule.concept_name == "bs.ass.fixAss"


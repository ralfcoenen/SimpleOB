"""Tests für die Zuordnung interner Abschlusspositionen zur Taxonomie."""

from openbilanz.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
from openbilanz.accounting.statement_category import StatementCategory
from openbilanz.taxonomy.concept import (
    TaxonomyBalance,
    TaxonomyConcept,
    TaxonomyPeriodType,
)
from openbilanz.taxonomy.mapping import TaxonomyMappingRule


def test_taxonomy_mapping_rule_stores_position_and_concept() -> None:
    """Eine interne Abschlussposition kann einem Taxonomie-Concept zugeordnet werden."""

    position = FinancialStatementPosition(
        code="bs.ass.fixAss",
        name="Anlagevermögen",
        category=StatementCategory.ASSET,
    )

    concept = TaxonomyConcept(
        name="bs.ass.fixAss",
        concept_id="de-gaap-ci_bs.ass.fixAss",
        type_name="xbrli:monetaryItemType",
        substitution_group="xbrli:item",
        period_type=TaxonomyPeriodType.INSTANT,
        balance=TaxonomyBalance.DEBIT,
        abstract=False,
        nillable=True,
    )

    rule = TaxonomyMappingRule(
        position=position,
        concept=concept,
    )

    assert rule.position is position
    assert rule.concept is concept


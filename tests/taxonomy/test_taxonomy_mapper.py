"""Tests für die Zuordnung interner Abschlusspositionen zur Taxonomie."""
import pytest

from openbilanz.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
from openbilanz.accounting.statement_category import StatementCategory
from openbilanz.taxonomy.concept import (
    TaxonomyBalance,
    TaxonomyConcept,
    TaxonomyPeriodType,
)
from openbilanz.taxonomy.mapper import TaxonomyMapper
from openbilanz.taxonomy.mapping import TaxonomyMappingRule
from openbilanz.taxonomy.mapping_set import TaxonomyMappingSet


def test_taxonomy_mapper_returns_concept_for_position() -> None:
    """Eine Abschlussposition wird auf ihr Taxonomie-Concept abgebildet."""

    position = FinancialStatementPosition(
        code="HGB.266.AKTIVA.A",
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

    mapping_set = TaxonomyMappingSet(
        rules=(
            TaxonomyMappingRule(
                position=position,
                concept=concept,
            ),
        )
    )

    mapper = TaxonomyMapper(
        mappings=mapping_set
    )

    assert mapper.concept_for(
        position
    ) is concept

def test_taxonomy_mapper_rejects_unmapped_position() -> None:
    """Eine nicht gemappte Abschlussposition löst einen Fehler aus."""

    position = FinancialStatementPosition(
        code="HGB.266.AKTIVA.B",
        name="Umlaufvermögen",
        category=StatementCategory.ASSET,
    )

    mapper = TaxonomyMapper(
        mappings=TaxonomyMappingSet(
            rules=()
        )
    )

    with pytest.raises(
        ValueError,
        match=(
            "no taxonomy mapping found for position "
            "HGB.266.AKTIVA.B"
        ),
    ):
        mapper.concept_for(
            position
        )



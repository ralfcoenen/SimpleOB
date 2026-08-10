"""Tests für die Sammlung von Taxonomie-Zuordnungen."""
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
from openbilanz.taxonomy.mapping import TaxonomyMappingRule
from openbilanz.taxonomy.mapping_set import TaxonomyMappingSet


def test_mapping_can_be_found_for_financial_statement_position() -> None:
    """Eine Zuordnung kann über die interne Abschlussposition gefunden werden."""

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

    rule = TaxonomyMappingRule(
        position=position,
        concept=concept,
    )

    mapping_set = TaxonomyMappingSet(
        rules=(rule,)
    )

    assert mapping_set.for_position(
        position
    ) is rule

def test_mapping_is_found_by_position_code() -> None:
    """Verschiedene Positionsobjekte mit gleichem Code teilen die Zuordnung."""

    mapped_position = FinancialStatementPosition(
        code="HGB.266.AKTIVA.A",
        name="Anlagevermögen",
        category=StatementCategory.ASSET,
    )

    lookup_position = FinancialStatementPosition(
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

    rule = TaxonomyMappingRule(
        position=mapped_position,
        concept=concept,
    )

    mapping_set = TaxonomyMappingSet(
        rules=(rule,)
    )

    assert mapped_position is not lookup_position

    assert mapping_set.for_position(
        lookup_position
    ) is rule

def test_mapping_set_rejects_duplicate_position_codes() -> None:
    """Ein Positionscode darf nur einmal gemappt werden."""

    first_position = FinancialStatementPosition(
        code="HGB.266.AKTIVA.A",
        name="Anlagevermögen",
        category=StatementCategory.ASSET,
    )

    duplicate_position = FinancialStatementPosition(
        code="HGB.266.AKTIVA.A",
        name="Anlagevermögen",
        category=StatementCategory.ASSET,
    )

    first_concept = TaxonomyConcept(
        name="bs.ass.fixAss",
        concept_id="de-gaap-ci_bs.ass.fixAss",
        type_name="xbrli:monetaryItemType",
        substitution_group="xbrli:item",
        period_type=TaxonomyPeriodType.INSTANT,
        balance=TaxonomyBalance.DEBIT,
        abstract=False,
        nillable=True,
    )

    second_concept = TaxonomyConcept(
        name="bs.ass.currAss",
        concept_id="de-gaap-ci_bs.ass.currAss",
        type_name="xbrli:monetaryItemType",
        substitution_group="xbrli:item",
        period_type=TaxonomyPeriodType.INSTANT,
        balance=TaxonomyBalance.DEBIT,
        abstract=False,
        nillable=True,
    )

    with pytest.raises(
        ValueError,
        match="duplicate position codes are not allowed",
    ):
        TaxonomyMappingSet(
            rules=(
                TaxonomyMappingRule(
                    position=first_position,
                    concept=first_concept,
                ),
                TaxonomyMappingRule(
                    position=duplicate_position,
                    concept=second_concept,
                ),
            )
        )


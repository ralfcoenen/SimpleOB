"""Tests für die Zuordnung interner Abschlusspositionen zur Taxonomie."""
import pytest

from simpleob.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
from simpleob.accounting.statement_category import StatementCategory
from simpleob.taxonomy.concept import (
    TaxonomyBalance,
    TaxonomyConcept,
    TaxonomyPeriodType,
)
from simpleob.taxonomy.concept_set import TaxonomyConceptSet
from simpleob.taxonomy.label_set import TaxonomyLabelSet
from simpleob.taxonomy.mapper import TaxonomyMapper
from simpleob.taxonomy.mapping import TaxonomyMappingRule
from simpleob.taxonomy.mapping_set import TaxonomyMappingSet
from simpleob.taxonomy.model import TaxonomyModel
from simpleob.taxonomy.presentation_set import (
    TaxonomyPresentationSet,
)


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

    taxonomy_model = TaxonomyModel(
        concepts=TaxonomyConceptSet(
            concepts=(concept,),
        ),
        labels=TaxonomyLabelSet(
            labels=(),
        ),
        presentation=TaxonomyPresentationSet(
            relations=(),
        ),
    )

    mapping_set = TaxonomyMappingSet(
        rules=(
            TaxonomyMappingRule(
                position=position,
                concept_name="bs.ass.fixAss",
            ),
        )
    )

    mapper = TaxonomyMapper(
        mappings=mapping_set,
        taxonomy_model=taxonomy_model,
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

    taxonomy_model = TaxonomyModel(
        concepts=TaxonomyConceptSet(
            concepts=(),
        ),
        labels=TaxonomyLabelSet(
            labels=(),
        ),
        presentation=TaxonomyPresentationSet(
            relations=(),
        ),
    )

    mapper = TaxonomyMapper(
        mappings=TaxonomyMappingSet(
            rules=()
        ),
        taxonomy_model=taxonomy_model,
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
    

def test_taxonomy_mapper_resolves_concept_from_taxonomy_model() -> None:
    """Ein Mapping wird gegen die aktuell geladene Taxonomie aufgelöst."""

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

    taxonomy_model = TaxonomyModel(
        concepts=TaxonomyConceptSet(
            concepts=(concept,),
        ),
        labels=TaxonomyLabelSet(
            labels=(),
        ),
        presentation=TaxonomyPresentationSet(
            relations=(),
        ),
    )

    mapping_set = TaxonomyMappingSet(
        rules=(
            TaxonomyMappingRule(
                position=position,
                concept_name="bs.ass.fixAss",
            ),
        )
    )

    mapper = TaxonomyMapper(
        mappings=mapping_set,
        taxonomy_model=taxonomy_model,
    )

    assert mapper.concept_for(
        position
    ) is concept

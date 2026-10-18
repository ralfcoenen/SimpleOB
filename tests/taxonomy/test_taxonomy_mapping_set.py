"""Tests für die Sammlung von Taxonomie-Zuordnungen."""
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
from simpleob.taxonomy.mapping import TaxonomyMappingRule
from simpleob.taxonomy.mapping_set import TaxonomyMappingSet
from simpleob.taxonomy.model import TaxonomyModel
from simpleob.taxonomy.presentation_set import (
    TaxonomyPresentationSet,
)


def test_mapping_can_be_found_for_financial_statement_position() -> None:
    """Eine Zuordnung kann über die interne Abschlussposition gefunden werden."""

    position = FinancialStatementPosition(
        code="HGB.266.AKTIVA.A",
        name="Anlagevermögen",
        category=StatementCategory.ASSET,
    )

   
    rule = TaxonomyMappingRule(
        position=position,
        concept_name="bs.ass.fixAss",
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

   
    rule = TaxonomyMappingRule(
        position=mapped_position,
        concept_name="bs.ass.fixAss",
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


    with pytest.raises(
        ValueError,
        match="duplicate position codes are not allowed",
    ):
        TaxonomyMappingSet(
            rules=(
                TaxonomyMappingRule(
                    position=first_position,
                    concept_name="bs.ass.fixAss",
                ),
                TaxonomyMappingRule(
                    position=duplicate_position,
                    concept_name="bs.ass.fixAss",
                ),
            )
        )

def test_mapping_set_validates_against_taxonomy_model() -> None:
    """Alle Mapping-Ziele existieren in der geladenen Taxonomie."""

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

    assert mapping_set.missing_concept_names(
        taxonomy_model
    ) == ()

def test_mapping_set_reports_missing_concept_names() -> None:
    """Nicht mehr vorhandene Mapping-Ziele werden gemeldet."""

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
                concept_name="bs.ass.oldConcept",
            ),
        )
    )

    assert mapping_set.missing_concept_names(
        taxonomy_model
    ) == (
        "bs.ass.oldConcept",
    )

def test_mapping_set_returns_validation_result() -> None:
    """Die Mapping-Prüfung liefert ein zusammengefasstes Ergebnis."""

    first_position = FinancialStatementPosition(
        code="HGB.266.AKTIVA.A",
        name="Anlagevermögen",
        category=StatementCategory.ASSET,
    )

    second_position = FinancialStatementPosition(
        code="HGB.266.AKTIVA.B",
        name="Umlaufvermögen",
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
                position=first_position,
                concept_name="bs.ass.fixAss",
            ),
            TaxonomyMappingRule(
                position=second_position,
                concept_name="bs.ass.oldConcept",
            ),
        )
    )

    result = mapping_set.validate(
        taxonomy_model
    )

    assert result.is_valid is False
    assert result.valid_count == 1
    assert result.missing_count == 1
    assert result.missing_concept_names == (
        "bs.ass.oldConcept",
    )

def test_mapping_validation_counts_rules_for_same_missing_concept() -> None:
    """Mehrere Regeln auf dasselbe fehlende Concept zählen einzeln."""

    first_position = FinancialStatementPosition(
        code="HGB.TEST.1",
        name="Erste Position",
        category=StatementCategory.NEUTRAL,
    )

    second_position = FinancialStatementPosition(
        code="HGB.TEST.2",
        name="Zweite Position",
        category=StatementCategory.NEUTRAL,
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

    mapping_set = TaxonomyMappingSet(
        rules=(
            TaxonomyMappingRule(
                position=first_position,
                concept_name="bs.ass.oldConcept",
            ),
            TaxonomyMappingRule(
                position=second_position,
                concept_name="bs.ass.oldConcept",
            ),
        )
    )

    result = mapping_set.validate(
        taxonomy_model
    )

    assert result.is_valid is False
    assert result.valid_count == 0
    assert result.missing_count == 2
    assert result.missing_concept_names == (
        "bs.ass.oldConcept",
    )


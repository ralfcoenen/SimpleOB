"""Tests für die Vervollständigung verpflichtender GAAP-CI-Facts."""

from datetime import date
from decimal import Decimal

from simpleob.taxonomy.concept import (
    TaxonomyBalance,
    TaxonomyConcept,
    TaxonomyPeriodType,
)
from simpleob.taxonomy.concept_set import TaxonomyConceptSet
from simpleob.taxonomy.context import TaxonomyContext
from simpleob.taxonomy.fact import TaxonomyFact
from simpleob.taxonomy.fiscal_requirement_reader import (
    FiscalConceptRequirement,
    FiscalRequirement,
)
from simpleob.taxonomy.gaap_ci_mandatory_fact_completer import (
    GaapCiMandatoryFactCompleter,
)
from simpleob.taxonomy.label_set import TaxonomyLabelSet
from simpleob.taxonomy.model import TaxonomyModel
from simpleob.taxonomy.presentation import (
    TaxonomyPresentationRelation,
)
from simpleob.taxonomy.presentation_set import (
    TaxonomyPresentationSet,
)
from simpleob.taxonomy.unit import TaxonomyUnit

BALANCE_SHEET_ROLE = (
    "http://www.xbrl.de/taxonomies/de-gaap-ci/role/balanceSheet"
)
INCOME_STATEMENT_ROLE = (
    "http://www.xbrl.de/taxonomies/de-gaap-ci/role/incomeStatement"
)
APPROPRIATION_PROFITS_ROLE = (
    "http://www.xbrl.de/taxonomies/de-gaap-ci/role/appropriationProfits"
)
NOTES_ROLE = (
    "http://www.xbrl.de/taxonomies/de-gaap-ci/role/notes"
)


def create_model(
    concepts: tuple[TaxonomyConcept, ...],
    *,
    relations: tuple[TaxonomyPresentationRelation, ...] = (),
) -> TaxonomyModel:
    """Erzeugt ein minimales Taxonomiemodell."""

    return TaxonomyModel(
        concepts=TaxonomyConceptSet(
            concepts=concepts,
        ),
        labels=TaxonomyLabelSet(
            labels=(),
        ),
        presentation=TaxonomyPresentationSet(
            relations=relations,
        ),
    )


def create_monetary_concept(
    *,
    name: str,
    period_type: TaxonomyPeriodType,
) -> TaxonomyConcept:
    """Erzeugt ein nillable monetäres Test-Concept."""

    return TaxonomyConcept(
        name=name,
        concept_id=f"de-gaap-ci_{name}",
        type_name="xbrli:monetaryItemType",
        substitution_group="xbrli:item",
        period_type=period_type,
        balance=TaxonomyBalance.DEBIT,
        abstract=False,
        nillable=True,
    )


def create_contexts() -> tuple[
    TaxonomyContext,
    TaxonomyContext,
]:
    """Erzeugt Instant- und Duration-Kontext für die Tests."""

    instant_context = TaxonomyContext(
        entity_identifier="DE123456789",
        entity_scheme="http://www.rzf-nrw.de/Steuernummer",
        period_type=TaxonomyPeriodType.INSTANT,
        start_date=None,
        end_date=date(2025, 12, 31),
    )
    duration_context = TaxonomyContext(
        entity_identifier="DE123456789",
        entity_scheme="http://www.rzf-nrw.de/Steuernummer",
        period_type=TaxonomyPeriodType.DURATION,
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
    )

    return instant_context, duration_context


def test_completer_creates_only_missing_mandatory_nil_facts() -> None:
    """Nur fehlende Mussfelder werden als NIL ergänzt."""

    existing_concept = create_monetary_concept(
        name="bs.ass",
        period_type=TaxonomyPeriodType.INSTANT,
    )
    missing_instant_concept = create_monetary_concept(
        name="bs.ass.currAss",
        period_type=TaxonomyPeriodType.INSTANT,
    )
    missing_duration_concept = create_monetary_concept(
        name="is.netIncome",
        period_type=TaxonomyPeriodType.DURATION,
    )

    model = create_model(
        (
            existing_concept,
            missing_instant_concept,
            missing_duration_concept,
        )
    )
    instant_context, duration_context = create_contexts()
    unit = TaxonomyUnit.eur()

    existing_fact = TaxonomyFact(
        concept=existing_concept,
        amount=Decimal("1000.00"),
        context=instant_context,
        unit=unit,
    )
    requirements = (
        FiscalConceptRequirement(
            concept_name="bs.ass",
            requirement=FiscalRequirement.SUM_REQUIRED,
            legal_form_kst=True,
        ),
        FiscalConceptRequirement(
            concept_name="bs.ass.currAss",
            requirement=FiscalRequirement.SUM_REQUIRED,
            legal_form_kst=True,
        ),
        FiscalConceptRequirement(
            concept_name="is.netIncome",
            requirement=FiscalRequirement.REQUIRED,
            legal_form_kst=True,
        ),
    )

    completer = GaapCiMandatoryFactCompleter(
        taxonomy_model=model,
    )

    nil_facts = completer.build_missing_nil_facts(
        requirements=requirements,
        existing_facts=(
            existing_fact,
        ),
        instant_context=instant_context,
        duration_context=duration_context,
        unit=unit,
    )

    assert len(nil_facts) == 2

    facts_by_name = {
        fact.concept.name: fact
        for fact in nil_facts
    }

    assert set(facts_by_name) == {
        "bs.ass.currAss",
        "is.netIncome",
    }
    assert (
        facts_by_name["bs.ass.currAss"].context
        is instant_context
    )
    assert (
        facts_by_name["is.netIncome"].context
        is duration_context
    )
    assert (
        facts_by_name["bs.ass.currAss"].unit
        == unit
    )
    assert (
        facts_by_name["is.netIncome"].unit
        == unit
    )


def test_completer_ignores_calculation_if_present_requirement() -> None:
    """Rechnerisch notwendige Positionen werden nicht automatisch als NIL ergänzt."""

    concept = create_monetary_concept(
        name="bs.ass.accountingConvenience",
        period_type=TaxonomyPeriodType.INSTANT,
    )
    model = create_model(
        (
            concept,
        )
    )
    instant_context, duration_context = create_contexts()
    requirements = (
        FiscalConceptRequirement(
            concept_name="bs.ass.accountingConvenience",
            requirement=(
                FiscalRequirement.CALCULATION_IF_PRESENT
            ),
            legal_form_kst=True,
        ),
    )

    completer = GaapCiMandatoryFactCompleter(
        taxonomy_model=model,
    )
    nil_facts = completer.build_missing_nil_facts(
        requirements=requirements,
        existing_facts=(),
        instant_context=instant_context,
        duration_context=duration_context,
        unit=TaxonomyUnit.eur(),
    )

    assert nil_facts == ()


def test_completer_filters_inactive_report_element() -> None:
    """Pflichtfelder eines nicht aktiven Berichtsteils werden nicht ergänzt."""

    balance_concept = create_monetary_concept(
        name="bs.ass.currAss",
        period_type=TaxonomyPeriodType.INSTANT,
    )
    ev_concept = create_monetary_concept(
        name="incomeUse.gainLoss.netIncome",
        period_type=TaxonomyPeriodType.DURATION,
    )
    root = create_monetary_concept(
        name="root",
        period_type=TaxonomyPeriodType.DURATION,
    )

    model = create_model(
        (
            balance_concept,
            ev_concept,
            root,
        ),
        relations=(
            TaxonomyPresentationRelation(
                parent_concept_id=root.concept_id,
                child_concept_id=balance_concept.concept_id,
                order=Decimal("1"),
                role_uri=BALANCE_SHEET_ROLE,
                preferred_label_role_uri=None,
            ),
            TaxonomyPresentationRelation(
                parent_concept_id=root.concept_id,
                child_concept_id=ev_concept.concept_id,
                order=Decimal("2"),
                role_uri=APPROPRIATION_PROFITS_ROLE,
                preferred_label_role_uri=None,
            ),
        ),
    )
    instant_context, duration_context = create_contexts()

    requirements = (
        FiscalConceptRequirement(
            concept_name=balance_concept.name,
            requirement=FiscalRequirement.SUM_REQUIRED,
            legal_form_kst=True,
        ),
        FiscalConceptRequirement(
            concept_name=ev_concept.name,
            requirement=FiscalRequirement.REQUIRED,
            legal_form_kst=True,
        ),
    )

    nil_facts = GaapCiMandatoryFactCompleter(
        taxonomy_model=model,
    ).build_missing_nil_facts(
        requirements=requirements,
        existing_facts=(),
        instant_context=instant_context,
        duration_context=duration_context,
        unit=TaxonomyUnit.eur(),
        active_report_element_roles=(
            BALANCE_SHEET_ROLE,
            INCOME_STATEMENT_ROLE,
        ),
    )

    assert tuple(
        fact.concept.name
        for fact in nil_facts
    ) == (
        balance_concept.name,
    )


def test_completer_accepts_concept_with_multiple_roles() -> None:
    """Eine aktive Presentation-Rolle genügt bei mehrfach verwendeten Concepts."""

    concept = create_monetary_concept(
        name="bs.eqLiab.liab.regulatory",
        period_type=TaxonomyPeriodType.INSTANT,
    )
    root = create_monetary_concept(
        name="root",
        period_type=TaxonomyPeriodType.INSTANT,
    )

    model = create_model(
        (
            concept,
            root,
        ),
        relations=(
            TaxonomyPresentationRelation(
                parent_concept_id=root.concept_id,
                child_concept_id=concept.concept_id,
                order=Decimal("1"),
                role_uri=NOTES_ROLE,
                preferred_label_role_uri=None,
            ),
            TaxonomyPresentationRelation(
                parent_concept_id=root.concept_id,
                child_concept_id=concept.concept_id,
                order=Decimal("2"),
                role_uri=BALANCE_SHEET_ROLE,
                preferred_label_role_uri=None,
            ),
        ),
    )
    instant_context, duration_context = create_contexts()

    requirements = (
        FiscalConceptRequirement(
            concept_name=concept.name,
            requirement=FiscalRequirement.REQUIRED,
            legal_form_kst=True,
        ),
    )

    nil_facts = GaapCiMandatoryFactCompleter(
        taxonomy_model=model,
    ).build_missing_nil_facts(
        requirements=requirements,
        existing_facts=(),
        instant_context=instant_context,
        duration_context=duration_context,
        unit=TaxonomyUnit.eur(),
        active_report_element_roles=(
            BALANCE_SHEET_ROLE,
            INCOME_STATEMENT_ROLE,
        ),
    )

    assert tuple(
        fact.concept.name
        for fact in nil_facts
    ) == (
        concept.name,
    )

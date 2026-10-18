"""Integrationstest der GAAP-CI-Mussfeldvervollständigung für Taxonomie 6.9."""

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from simpleob.taxonomy.arelle_adapter import ArelleAdapter
from simpleob.taxonomy.concept import TaxonomyPeriodType
from simpleob.taxonomy.context import TaxonomyContext
from simpleob.taxonomy.entry_point import TaxonomyEntryPoint
from simpleob.taxonomy.fact import TaxonomyFact
from simpleob.taxonomy.fiscal_requirement_reader import (
    FiscalRequirement,
    FiscalRequirementReader,
)
from simpleob.taxonomy.gaap_ci_mandatory_fact_completer import (
    GaapCiMandatoryFactCompleter,
)
from simpleob.taxonomy.resolver import TaxonomyResolver
from simpleob.taxonomy.taxonomy import TaxonomyVersion
from simpleob.taxonomy.unit import TaxonomyUnit

TAXONOMY_ROOT = Path(
    "data/taxonomy"
).resolve()

TEST_ENTITY_SCHEME = (
    "http://www.bundesfinanzministerium.de"
)


@pytest.mark.integration
def test_gaap_ci_69_completes_real_corporation_mandatory_facts() -> None:
    """Echte 6.9-KSt-Mussfelder werden vollständig als NIL ergänzt."""

    version_root = TAXONOMY_ROOT / "6.9"

    if not version_root.is_dir():
        pytest.skip(
            "Taxonomy 6.9 is not installed locally"
        )

    resolver = TaxonomyResolver(
        root=TAXONOMY_ROOT
    )

    entry_point_path = (
        resolver.gaap_ci_fiscal_entry_point(
            TaxonomyVersion.V6_9
        )
    )

    entry_point = TaxonomyEntryPoint.from_file(
        entry_point_path
    )

    reader = FiscalRequirementReader(
        entry_point
    )

    requirements = (
        reader.corporation_requirements()
    )

    mandatory_requirements = tuple(
        requirement
        for requirement in requirements
        if requirement.requirement
        in {
            FiscalRequirement.REQUIRED,
            FiscalRequirement.SUM_REQUIRED,
        }
    )

    calculation_if_present_requirements = tuple(
        requirement
        for requirement in requirements
        if requirement.requirement
        is FiscalRequirement.CALCULATION_IF_PRESENT
    )

    assert len(requirements) == 977
    assert len(mandatory_requirements) == 562
    assert (
        len(calculation_if_present_requirements)
        == 415
    )

    adapter = ArelleAdapter()

    try:
        taxonomy_model = adapter.model(
            entry_point_path
        )

        concepts_by_name = {
            concept.name: concept
            for concept
            in taxonomy_model.concepts.concepts
        }

        mandatory_concepts = tuple(
            concepts_by_name[
                requirement.concept_name
            ]
            for requirement
            in mandatory_requirements
        )

        assert len(mandatory_concepts) == 562

        instant_mandatory_concepts = tuple(
            concept
            for concept in mandatory_concepts
            if concept.period_type
            is TaxonomyPeriodType.INSTANT
        )

        duration_mandatory_concepts = tuple(
            concept
            for concept in mandatory_concepts
            if concept.period_type
            is TaxonomyPeriodType.DURATION
        )

        assert (
            len(instant_mandatory_concepts)
            == 131
        )
        assert (
            len(duration_mandatory_concepts)
            == 431
        )

        instant_context = TaxonomyContext(
            entity_identifier="DE123456789",
            entity_scheme=TEST_ENTITY_SCHEME,
            period_type=TaxonomyPeriodType.INSTANT,
            start_date=None,
            end_date=date(2026, 12, 31),
        )

        duration_context = TaxonomyContext(
            entity_identifier="DE123456789",
            entity_scheme=TEST_ENTITY_SCHEME,
            period_type=TaxonomyPeriodType.DURATION,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )

        unit = TaxonomyUnit.eur()

        existing_concept = (
            mandatory_concepts[0]
        )

        if (
            existing_concept.period_type
            is TaxonomyPeriodType.INSTANT
        ):
            existing_context = (
                instant_context
            )
        elif (
            existing_concept.period_type
            is TaxonomyPeriodType.DURATION
        ):
            existing_context = (
                duration_context
            )
        else:
            pytest.fail(
                "Mandatory 6.9 concept has "
                "unexpected period type: "
                f"{existing_concept.name}"
            )

        existing_fact = TaxonomyFact(
            concept=existing_concept,
            amount=Decimal("1.00"),
            context=existing_context,
            unit=unit,
        )

        completer = (
            GaapCiMandatoryFactCompleter(
                taxonomy_model=taxonomy_model
            )
        )

        nil_facts = (
            completer.build_missing_nil_facts(
                requirements=requirements,
                existing_facts=(
                    existing_fact,
                ),
                instant_context=instant_context,
                duration_context=duration_context,
                unit=unit,
            )
        )

    finally:
        adapter.close()

    assert len(nil_facts) == 561

    nil_concept_names = {
        fact.concept.name
        for fact in nil_facts
    }

    mandatory_concept_names = {
        requirement.concept_name
        for requirement
        in mandatory_requirements
    }

    calculation_if_present_names = {
        requirement.concept_name
        for requirement
        in calculation_if_present_requirements
    }

    assert (
        existing_concept.name
        not in nil_concept_names
    )

    assert nil_concept_names == (
        mandatory_concept_names
        - {
            existing_concept.name,
        }
    )

    assert (
        nil_concept_names
        .isdisjoint(
            calculation_if_present_names
        )
    )

    instant_nil_facts = tuple(
        fact
        for fact in nil_facts
        if fact.context
        is instant_context
    )

    duration_nil_facts = tuple(
        fact
        for fact in nil_facts
        if fact.context
        is duration_context
    )

    expected_instant_nil_count = (
        131
        - int(
            existing_concept.period_type
            is TaxonomyPeriodType.INSTANT
        )
    )

    expected_duration_nil_count = (
        431
        - int(
            existing_concept.period_type
            is TaxonomyPeriodType.DURATION
        )
    )

    assert (
        len(instant_nil_facts)
        == expected_instant_nil_count
    )

    assert (
        len(duration_nil_facts)
        == expected_duration_nil_count
    )

    assert (
        len(instant_nil_facts)
        + len(duration_nil_facts)
        == len(nil_facts)
    )

    assert all(
        fact.unit is unit
        for fact in nil_facts
    )

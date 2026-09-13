"""Tests für den Arelle-Adapter."""

from pathlib import Path
from decimal import Decimal

import pytest

from openbilanz.taxonomy.arelle_adapter import ArelleAdapter
from openbilanz.taxonomy.calculation_set import (
    TaxonomyCalculationSet,
)
from openbilanz.taxonomy.calculation import (
    TaxonomyCalculationRelation,
)
from openbilanz.taxonomy.concept import (
    TaxonomyBalance,
    TaxonomyPeriodType,
)
from openbilanz.taxonomy.concept_set import TaxonomyConceptSet
from openbilanz.taxonomy.label import (
    TaxonomyLabelRole,
)
from openbilanz.taxonomy.label_set import TaxonomyLabelSet
from openbilanz.taxonomy.model import TaxonomyModel
from openbilanz.taxonomy.presentation_set import (
    TaxonomyPresentationSet,
)

ENTRY_POINT = Path(
    "/tmp/openbilanz-taxonomy/6.8/"
    "german-gaap-taxonomy-v6.8-2024-04-01/"
    "xbrl/"
    "de-gaap-ci-2024-04-01/"
    "de-gaap-ci-2024-04-01-shell-fiscal.xsd"
)

INVALID_INSTANCE = Path(
    "tests/fixtures/invalid_xbrl_instance.xbrl"
)


def require_taxonomy() -> None:
    """Überspringt den Test, wenn die lokale Taxonomie fehlt."""

    if not ENTRY_POINT.is_file():
        pytest.skip(
            "German GAAP taxonomy 6.8 is not installed locally"
        )


def test_arelle_adapter_loads_taxonomy() -> None:
    """Der Adapter lädt eine Taxonomie über Arelle."""

    require_taxonomy()

    adapter = ArelleAdapter()

    try:
        taxonomy = adapter.load_taxonomy(
            ENTRY_POINT
        )

        assert taxonomy.concept_count == 3531

        assert (
            "http://www.xbrl.de/taxonomies/"
            "de-gaap-ci-2024-04-01"
            in taxonomy.namespaces
        )

    finally:
        adapter.close()


def test_arelle_adapter_validates_taxonomy() -> None:
    """Der Adapter validiert eine Taxonomie über Arelle."""

    require_taxonomy()

    adapter = ArelleAdapter()

    try:
        result = adapter.validate(
            ENTRY_POINT
        )

        assert result.is_valid
        assert result.errors == ()

    finally:
        adapter.close()


def test_arelle_adapter_reports_validation_errors() -> None:
    """Der Adapter gibt Arelle-Validierungsfehler zurück."""

    adapter = ArelleAdapter()

    try:
        result = adapter.validate(
            INVALID_INSTANCE
        )

        assert not result.is_valid
        assert result.errors

    finally:
        adapter.close()

def test_arelle_adapter_returns_taxonomy_concept() -> None:
    """Der Adapter überführt ein Arelle-Concept ins Openbilanz-Modell."""

    require_taxonomy()

    adapter = ArelleAdapter()

    try:
        concept = adapter.concept(
            ENTRY_POINT,
            "bs.ass.fixAss",
        )

        assert concept is not None

        assert concept.name == "bs.ass.fixAss"
        assert concept.concept_id == "de-gaap-ci_bs.ass.fixAss"

        assert (
            concept.type_name
            == "xbrli:monetaryItemType"
        )

        assert (
            concept.period_type
            is TaxonomyPeriodType.INSTANT
        )

        assert (
            concept.balance
            is TaxonomyBalance.DEBIT
        )

        assert not concept.abstract
        assert concept.nillable
        assert concept.is_numeric

    finally:
        adapter.close()


def test_arelle_adapter_returns_none_for_unknown_concept() -> None:
    """Ein unbekanntes Concept wird nicht gefunden."""

    require_taxonomy()

    adapter = ArelleAdapter()

    try:
        concept = adapter.concept(
            ENTRY_POINT,
            "does.not.exist",
        )

        assert concept is None

    finally:
        adapter.close()

def test_arelle_adapter_returns_concept_set() -> None:
    """Der Adapter überführt Arelle-Concepts in ein ConceptSet."""

    require_taxonomy()

    adapter = ArelleAdapter()

    try:
        concepts = adapter.concepts(
            ENTRY_POINT
        )

        assert isinstance(
            concepts,
            TaxonomyConceptSet,
        )

        concept = concepts.by_id(
            "de-gaap-ci_bs.ass.fixAss"
        )

        assert concept is not None
        assert concept.name == "bs.ass.fixAss"

        assert (
            concept.type_name
            == "xbrli:monetaryItemType"
        )

        assert (
            concept.period_type
            is TaxonomyPeriodType.INSTANT
        )

        assert (
            concept.balance
            is TaxonomyBalance.DEBIT
        )

        assert concept.is_numeric

    finally:
        adapter.close()

def test_arelle_adapter_concept_set_contains_valid_concepts() -> None:
    """Das ConceptSet enthält nur berichtbare XBRL-Items mit ID."""

    require_taxonomy()

    adapter = ArelleAdapter()

    try:
        concepts = adapter.concepts(
            ENTRY_POINT
        )

        assert concepts.concepts

        assert all(
            concept.concept_id is not None
            for concept in concepts.concepts
        )

        assert len(concepts.concepts) == len(
            {
                concept.concept_id
                for concept in concepts.concepts
            }
        )

        print()
        print(
            "BERICHTBARE CONCEPTS:",
            len(concepts.concepts),
        )

    finally:
        adapter.close()

def test_arelle_adapter_returns_standard_label() -> None:
    """Der Adapter liefert das deutsche Standardlabel eines Concepts."""

    require_taxonomy()

    adapter = ArelleAdapter()

    try:
        label = adapter.label(
            ENTRY_POINT,
            "bs.ass.fixAss",
            language="de",
        )

        assert label is not None

        assert label.concept_id == (
            "de-gaap-ci_bs.ass.fixAss"
        )

        assert label.text

        assert (
            label.role
            is TaxonomyLabelRole.LABEL
        )

        assert (
            label.role_uri
            == "http://www.xbrl.org/2003/role/label"
        )

        assert label.language == "de"

        print()
        print("LABEL:")
        print(label.text)

    finally:
        adapter.close()


def test_arelle_adapter_returns_label_set() -> None:
    """Der Adapter überführt deutsche Standardlabels in ein LabelSet."""

    require_taxonomy()

    adapter = ArelleAdapter()

    try:
        labels = adapter.labels(
            ENTRY_POINT
        )

        assert isinstance(
            labels,
            TaxonomyLabelSet,
        )

        concept_labels = labels.for_concept(
            "de-gaap-ci_bs.ass.fixAss",
            language="de",
            role=TaxonomyLabelRole.LABEL,
        )

        assert concept_labels

        assert any(
            label.text == "Anlagevermögen"
            for label in concept_labels
        )

    finally:
        adapter.close()


def test_arelle_adapter_returns_presentation_set() -> None:
    """Der Adapter überführt Presentation-Beziehungen in ein PresentationSet."""

    require_taxonomy()

    adapter = ArelleAdapter()

    try:
        presentation = adapter.presentation(
            ENTRY_POINT
        )

        assert isinstance(
            presentation,
            TaxonomyPresentationSet,
        )

        assert presentation.relations

        assert all(
            relation.parent_concept_id
            for relation in presentation.relations
        )

        assert all(
            relation.child_concept_id
            for relation in presentation.relations
        )

        assert all(
            relation.role_uri
            for relation in presentation.relations
        )

        print()
        print(
            "PRESENTATION-BEZIEHUNGEN:",
            len(presentation.relations),
        )

    finally:
        adapter.close()

def test_arelle_adapter_returns_calculation_set() -> None:
    """Der Adapter überführt Calculation-Beziehungen in ein CalculationSet."""

    require_taxonomy()

    adapter = ArelleAdapter()

    try:
        calculation = adapter.calculation(
            ENTRY_POINT
        )

        assert isinstance(
            calculation,
            TaxonomyCalculationSet,
        )

        assert calculation.relations

        assert all(
            relation.parent_concept_id
            for relation in calculation.relations
        )

        assert all(
            relation.child_concept_id
            for relation in calculation.relations
        )

        assert all(
            relation.role_uri
            for relation in calculation.relations
        )

        print()
        print(
            "CALCULATION-BEZIEHUNGEN:",
            len(calculation.relations),
        )

    finally:
        adapter.close()


def test_arelle_adapter_returns_taxonomy_model() -> None:
    """Der Adapter baut ein vollständiges TaxonomyModel aus Arelle-Daten."""

    require_taxonomy()

    adapter = ArelleAdapter()

    try:
        model = adapter.model(
            ENTRY_POINT
        )

        assert isinstance(
            model,
            TaxonomyModel,
        )

        concept = model.concepts.by_id(
            "de-gaap-ci_bs.ass.fixAss"
        )

        assert concept is not None
        assert concept.name == "bs.ass.fixAss"

        assert (
            model.label_for(
                "de-gaap-ci_bs.ass.fixAss"
            )
            == "Anlagevermögen"
        )

        assert model.presentation.relations
        assert model.calculation.relations

    finally:
        adapter.close()

def test_calculation_set_returns_parents_for_role() -> None:
    calculation = TaxonomyCalculationSet(
        relations=(
            TaxonomyCalculationRelation(
                parent_concept_id="parent-a",
                child_concept_id="child",
                order=Decimal("2"),
                weight=Decimal("1"),
                role_uri="role-a",
            ),
            TaxonomyCalculationRelation(
                parent_concept_id="parent-b",
                child_concept_id="child",
                order=Decimal("1"),
                weight=Decimal("-1"),
                role_uri="role-a",
            ),
            TaxonomyCalculationRelation(
                parent_concept_id="parent-other-role",
                child_concept_id="child",
                order=Decimal("1"),
                weight=Decimal("1"),
                role_uri="role-b",
            ),
        )
    )

    parents = calculation.parents_of(
        "child",
        role_uri="role-a",
    )

    assert tuple(
        relation.parent_concept_id
        for relation in parents
    ) == (
        "parent-a",
        "parent-b",
    )

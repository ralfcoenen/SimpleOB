"""Tests für den TaxonomyService."""

from datetime import date
from pathlib import Path

from openbilanz.domain.fiscal_year import FiscalYear
from openbilanz.taxonomy.concept_set import TaxonomyConceptSet
from openbilanz.taxonomy.label_set import TaxonomyLabelSet
from openbilanz.taxonomy.model import TaxonomyModel
from openbilanz.taxonomy.presentation_set import (
    TaxonomyPresentationSet,
)
from openbilanz.taxonomy.service import TaxonomyService


class FakeResolver:
    """Minimaler Resolver für den Service-Test."""

    def __init__(
        self,
        entry_point: Path,
    ) -> None:
        self.entry_point = entry_point
        self.received_fiscal_year = None

    def for_fiscal_year(
        self,
        fiscal_year: FiscalYear,
    ) -> Path:
        self.received_fiscal_year = fiscal_year
        return self.entry_point


class FakeAdapter:
    """Minimaler Arelle-Adapter für den Service-Test."""

    def __init__(
        self,
        model: TaxonomyModel,
    ) -> None:
        self.model_result = model
        self.received_entry_point = None
        self.closed = False

    def model(
        self,
        entry_point: Path,
    ) -> TaxonomyModel:
        self.received_entry_point = entry_point
        return self.model_result

    def close(self) -> None:
        self.closed = True

def test_taxonomy_service_loads_model_for_fiscal_year() -> None:
    """Der Service verbindet Geschäftsjahr, Resolver und Adapter."""

    fiscal_year = FiscalYear(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )

    entry_point = Path(
        "/tmp/openbilanz-taxonomy/6.9/"
        "de-gaap-ci-2025-04-01/"
        "de-gaap-ci-2025-04-01-shell-fiscal.xsd"
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

    resolver = FakeResolver(
        entry_point
    )

    adapter = FakeAdapter(
        taxonomy_model
    )

    service = TaxonomyService(
        resolver=resolver,
        adapter=adapter,
    )

    result = service.model_for(
        fiscal_year
    )

    assert result is taxonomy_model
    assert resolver.received_fiscal_year is fiscal_year
    assert adapter.received_entry_point == entry_point

def test_taxonomy_service_closes_adapter() -> None:
    """Der Service schließt die Arelle-Ressourcen."""

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

    resolver = FakeResolver(
        Path("/tmp/test-taxonomy.xsd")
    )

    adapter = FakeAdapter(
        taxonomy_model
    )

    service = TaxonomyService(
        resolver=resolver,
        adapter=adapter,
    )

    service.close()

    assert adapter.closed


def test_taxonomy_service_can_be_used_as_context_manager() -> None:
    """Der Service schließt seine Ressourcen beim Verlassen des Contexts."""

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

    resolver = FakeResolver(
        Path("/tmp/test-taxonomy.xsd")
    )

    adapter = FakeAdapter(
        taxonomy_model
    )

    with TaxonomyService(
        resolver=resolver,
        adapter=adapter,
    ) as service:
        assert service is not None
        assert adapter.closed is False

    assert adapter.closed


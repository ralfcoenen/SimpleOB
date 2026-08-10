"""Tests für taxonomische XBRL-Kontexte."""

from datetime import date

import pytest

from openbilanz.taxonomy.concept import TaxonomyPeriodType
from openbilanz.taxonomy.context import TaxonomyContext

TEST_ENTITY_SCHEME = "http://www.bundesfinanzministerium.de"


def test_taxonomy_context_duration_requires_start_date() -> None:
    """Eine Duration-Periode benötigt ein Startdatum."""

    with pytest.raises(
        ValueError,
        match="duration context requires start_date",
    ):
        TaxonomyContext(
            entity_identifier="DE123456789",
            entity_scheme=TEST_ENTITY_SCHEME,
            period_type=TaxonomyPeriodType.DURATION,
            start_date=None,
            end_date=date(2025, 12, 31),
        )


def test_taxonomy_context_instant_rejects_start_date() -> None:
    """Ein Instant-Kontext darf kein Startdatum besitzen."""

    with pytest.raises(
        ValueError,
        match="instant context must not have start_date",
    ):
        TaxonomyContext(
            entity_identifier="DE123456789",
            entity_scheme=TEST_ENTITY_SCHEME,
            period_type=TaxonomyPeriodType.INSTANT,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
        )


def test_taxonomy_context_duration_rejects_start_after_end() -> None:
    """Bei Duration darf das Startdatum nicht nach dem Enddatum liegen."""

    with pytest.raises(
        ValueError,
        match="start_date must not be after end_date",
    ):
        TaxonomyContext(
            entity_identifier="DE123456789",
            entity_scheme=TEST_ENTITY_SCHEME,
            period_type=TaxonomyPeriodType.DURATION,
            start_date=date(2026, 1, 1),
            end_date=date(2025, 12, 31),
        )


@pytest.mark.parametrize(
    "entity_identifier",
    (
        "",
        "   ",
    ),
)
def test_taxonomy_context_rejects_blank_entity_identifier(
    entity_identifier: str,
) -> None:
    """Der Entity-Identifier darf nicht leer sein."""

    with pytest.raises(
        ValueError,
        match="entity_identifier must not be blank",
    ):
        TaxonomyContext(
            entity_identifier=entity_identifier,
            entity_scheme=TEST_ENTITY_SCHEME,
            period_type=TaxonomyPeriodType.INSTANT,
            start_date=None,
            end_date=date(2025, 12, 31),
        )


def test_taxonomy_context_stores_entity_scheme() -> None:
    """Ein XBRL-Kontext speichert das Scheme des Entity-Identifier."""

    context = TaxonomyContext(
        entity_identifier="DE123456789",
        entity_scheme=TEST_ENTITY_SCHEME,
        period_type=TaxonomyPeriodType.INSTANT,
        start_date=None,
        end_date=date(2025, 12, 31),
    )

    assert context.entity_scheme == TEST_ENTITY_SCHEME


@pytest.mark.parametrize(
    "entity_scheme",
    (
        "",
        "   ",
    ),
)
def test_taxonomy_context_rejects_blank_entity_scheme(
    entity_scheme: str,
) -> None:
    """Das Scheme des Entity-Identifier darf nicht leer sein."""

    with pytest.raises(
        ValueError,
        match="entity_scheme must not be blank",
    ):
        TaxonomyContext(
            entity_identifier="DE123456789",
            entity_scheme=entity_scheme,
            period_type=TaxonomyPeriodType.INSTANT,
            start_date=None,
            end_date=date(2025, 12, 31),
        )

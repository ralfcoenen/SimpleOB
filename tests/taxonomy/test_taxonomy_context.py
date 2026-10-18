"""Tests für taxonomische XBRL-Kontexte."""

from datetime import date

import pytest

from simpleob.taxonomy.concept import TaxonomyPeriodType
from simpleob.taxonomy.context import (
    TaxonomyContext,
    TaxonomyDimension,
)

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


def test_taxonomy_context_has_no_dimensions_by_default() -> None:
    """Ein normaler XBRL-Kontext besitzt standardmäßig keine Dimensionen."""

    context = TaxonomyContext(
        entity_identifier="DE123456789",
        entity_scheme=TEST_ENTITY_SCHEME,
        period_type=TaxonomyPeriodType.DURATION,
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
    )

    assert context.dimensions == ()


def test_taxonomy_context_stores_dimensions() -> None:
    """Ein XBRL-Kontext kann explizite Dimensionen speichern."""

    context = TaxonomyContext(
        entity_identifier="DE123456789",
        entity_scheme=TEST_ENTITY_SCHEME,
        period_type=TaxonomyPeriodType.DURATION,
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
        dimensions=(
            TaxonomyDimension(
                dimension_name="de-gaap-ci:dim_taxTrans",
                member_name="de-gaap-ci:dim_comBal",
            ),
            TaxonomyDimension(
                dimension_name=(
                    "de-gaap-ci:dim_changes.nt.ass.gross"
                ),
                member_name=(
                    "de-gaap-ci:bs.ass.fixAss.tan.machinery"
                ),
            ),
        ),
    )

    assert context.dimensions == (
        TaxonomyDimension(
            dimension_name="de-gaap-ci:dim_taxTrans",
            member_name="de-gaap-ci:dim_comBal",
        ),
        TaxonomyDimension(
            dimension_name=(
                "de-gaap-ci:dim_changes.nt.ass.gross"
            ),
            member_name=(
                "de-gaap-ci:bs.ass.fixAss.tan.machinery"
            ),
        ),
    )


@pytest.mark.parametrize(
    ("dimension_name", "member_name", "message"),
    (
        (
            "",
            "de-gaap-ci:dim_comBal",
            "dimension_name must not be blank",
        ),
        (
            "   ",
            "de-gaap-ci:dim_comBal",
            "dimension_name must not be blank",
        ),
        (
            "de-gaap-ci:dim_taxTrans",
            "",
            "member_name must not be blank",
        ),
        (
            "de-gaap-ci:dim_taxTrans",
            "   ",
            "member_name must not be blank",
        ),
    ),
)
def test_taxonomy_dimension_rejects_blank_names(
    dimension_name: str,
    member_name: str,
    message: str,
) -> None:
    """Dimension und Mitglied müssen benannt sein."""

    with pytest.raises(
        ValueError,
        match=message,
    ):
        TaxonomyDimension(
            dimension_name=dimension_name,
            member_name=member_name,
        )


def test_taxonomy_context_rejects_non_tuple_dimensions() -> None:
    """Dimensionen müssen unveränderlich als Tuple gespeichert werden."""

    with pytest.raises(
        TypeError,
        match="dimensions must be a tuple",
    ):
        TaxonomyContext(
            entity_identifier="DE123456789",
            entity_scheme=TEST_ENTITY_SCHEME,
            period_type=TaxonomyPeriodType.DURATION,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            dimensions=[],  # type: ignore[arg-type]
        )


def test_taxonomy_context_rejects_invalid_dimension_entries() -> None:
    """Das Dimensions-Tuple darf nur TaxonomyDimension enthalten."""

    with pytest.raises(
        TypeError,
        match=(
            "dimensions must contain only "
            "TaxonomyDimension"
        ),
    ):
        TaxonomyContext(
            entity_identifier="DE123456789",
            entity_scheme=TEST_ENTITY_SCHEME,
            period_type=TaxonomyPeriodType.DURATION,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            dimensions=(
                "de-gaap-ci:dim_taxTrans",
            ),  # type: ignore[arg-type]
        )


def test_taxonomy_context_rejects_duplicate_dimensions() -> None:
    """Eine Dimension darf in einem Kontext nur einmal vorkommen."""

    with pytest.raises(
        ValueError,
        match="dimension names must be unique",
    ):
        TaxonomyContext(
            entity_identifier="DE123456789",
            entity_scheme=TEST_ENTITY_SCHEME,
            period_type=TaxonomyPeriodType.DURATION,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            dimensions=(
                TaxonomyDimension(
                    dimension_name="de-gaap-ci:dim_taxTrans",
                    member_name="de-gaap-ci:dim_comBal",
                ),
                TaxonomyDimension(
                    dimension_name="de-gaap-ci:dim_taxTrans",
                    member_name="de-gaap-ci:dim_taxBal",
                ),
            ),
        )

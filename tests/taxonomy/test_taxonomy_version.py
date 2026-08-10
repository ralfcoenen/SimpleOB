"""Tests für die Auswahl der E-Bilanz-Taxonomie."""
from datetime import date

import pytest

from openbilanz.domain.fiscal_year import FiscalYear
from openbilanz.taxonomy.taxonomy import (
    TaxonomyVersion,
    taxonomy_version_for,
)


def test_selects_taxonomy_6_9_for_fiscal_year_2026() -> None:
    """Für ein 2026 beginnendes Wirtschaftsjahr gilt Taxonomie 6.9."""

    fiscal_year = FiscalYear(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )

    assert (
        taxonomy_version_for(fiscal_year)
        is TaxonomyVersion.V6_9
    )


def test_selects_taxonomy_6_10_for_fiscal_year_2027() -> None:
    """Für ein 2027 beginnendes Wirtschaftsjahr gilt Taxonomie 6.10."""

    fiscal_year = FiscalYear(
        start_date=date(2027, 1, 1),
        end_date=date(2027, 12, 31),
    )

    assert (
        taxonomy_version_for(fiscal_year)
        is TaxonomyVersion.V6_10
    )


def test_taxonomy_selection_uses_fiscal_year_start() -> None:
    """Bei abweichendem Wirtschaftsjahr entscheidet dessen Beginn."""

    fiscal_year = FiscalYear(
        start_date=date(2026, 7, 1),
        end_date=date(2027, 6, 30),
    )

    assert (
        taxonomy_version_for(fiscal_year)
        is TaxonomyVersion.V6_9
    )

def test_rejects_fiscal_year_before_supported_taxonomies() -> None:
    """Vor 2025 beginnende Geschäftsjahre werden nicht unterstützt."""

    fiscal_year = FiscalYear(
        start_date=date(2024, 12, 31),
        end_date=date(2025, 12, 30),
    )

    with pytest.raises(
        ValueError,
        match=(
            "Für dieses Geschäftsjahr ist keine "
            "unterstützte Taxonomie definiert."
        ),
    ):
        taxonomy_version_for(
            fiscal_year
        )

def test_selects_taxonomy_6_10_exactly_from_2027() -> None:
    """Ab dem 1. Januar 2027 gilt exakt Taxonomie 6.10."""

    fiscal_year = FiscalYear(
        start_date=date(2027, 1, 1),
        end_date=date(2027, 12, 31),
    )

    assert (
        taxonomy_version_for(fiscal_year)
        is TaxonomyVersion.V6_10
    )
    
def test_selects_taxonomy_6_8_for_fiscal_year_2025() -> None:
    """Für ein 2025 beginnendes Wirtschaftsjahr gilt Taxonomie 6.8."""

    fiscal_year = FiscalYear(
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
    )

    assert (
        taxonomy_version_for(fiscal_year)
        is TaxonomyVersion.V6_8
    )


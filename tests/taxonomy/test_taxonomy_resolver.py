"""Tests für die Auflösung lokal installierter Taxonomien."""

from datetime import date
from pathlib import Path

import pytest

from simpleob.domain.fiscal_year import FiscalYear
from simpleob.taxonomy.resolver import TaxonomyResolver
from simpleob.taxonomy.taxonomy import TaxonomyVersion
from tests.taxonomy_resources import taxonomy_entry_point, taxonomy_test_root

TAXONOMY_ROOT = taxonomy_test_root()


def test_resolver_finds_gaap_ci_fiscal_entry_point() -> None:
    """Der GAAP-CI-Fiscal-Entry-Point wird gefunden."""

    taxonomy_entry_point('6.9')


    resolver = TaxonomyResolver(
        root=TAXONOMY_ROOT
    )

    entry_point = resolver.gaap_ci_fiscal_entry_point(
        TaxonomyVersion.V6_9
    )

    assert entry_point.is_file()
    assert entry_point.is_relative_to(TAXONOMY_ROOT / "6.9")
    assert entry_point.name == "de-gaap-ci-2025-04-01-shell-fiscal.xsd"


def test_resolver_finds_gaap_ci_fiscal_entry_point_for_6_8() -> None:
    """Der Resolver findet auch die tiefer verschachtelte Taxonomie 6.8."""

    taxonomy_entry_point('6.8')


    resolver = TaxonomyResolver(
        root=TAXONOMY_ROOT
    )

    entry_point = resolver.gaap_ci_fiscal_entry_point(
        TaxonomyVersion.V6_8
    )

    assert entry_point.is_file()
    assert entry_point.is_relative_to(TAXONOMY_ROOT / "6.8")
    assert entry_point.name == "de-gaap-ci-2024-04-01-shell-fiscal.xsd"


def test_resolver_finds_gaap_ci_fiscal_entry_point_for_6_10() -> None:
    """Der Resolver findet die Taxonomie 6.10."""

    taxonomy_entry_point('6.10')


    resolver = TaxonomyResolver(
        root=TAXONOMY_ROOT
    )

    entry_point = resolver.gaap_ci_fiscal_entry_point(
        TaxonomyVersion.V6_10
    )

    assert entry_point.is_file()
    assert entry_point.is_relative_to(TAXONOMY_ROOT / "6.10")
    assert entry_point.name == "de-gaap-ci-2026-04-01-shell-fiscal.xsd"

def test_resolver_finds_entry_point_for_fiscal_year() -> None:
    """Ein Geschäftsjahr wird auf den passenden Entry-Point aufgelöst."""

    taxonomy_entry_point('6.9')


    fiscal_year = FiscalYear(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )

    resolver = TaxonomyResolver(
        root=TAXONOMY_ROOT
    )

    entry_point = resolver.for_fiscal_year(
        fiscal_year
    )

    assert entry_point.is_file()
    assert entry_point.is_relative_to(TAXONOMY_ROOT / "6.9")
    assert entry_point.name == "de-gaap-ci-2025-04-01-shell-fiscal.xsd"
    
@pytest.mark.parametrize(
    ("start_date", "end_date", "version"),
    (
        (
            date(2025, 1, 1),
            date(2025, 12, 31),
            TaxonomyVersion.V6_8,
        ),
        (
            date(2026, 1, 1),
            date(2026, 12, 31),
            TaxonomyVersion.V6_9,
        ),
        (
            date(2027, 1, 1),
            date(2027, 12, 31),
            TaxonomyVersion.V6_10,
        ),
    ),
)
def test_resolver_uses_correct_taxonomy_for_fiscal_year(
    start_date: date,
    end_date: date,
    version: TaxonomyVersion,
) -> None:
    """Geschäftsjahre werden der richtigen Taxonomieversion zugeordnet."""

    taxonomy_entry_point(version.value)


    fiscal_year = FiscalYear(
        start_date=start_date,
        end_date=end_date,
    )

    resolver = TaxonomyResolver(
        root=TAXONOMY_ROOT
    )

    entry_point = resolver.for_fiscal_year(
        fiscal_year
    )

    assert entry_point == resolver.gaap_ci_fiscal_entry_point(
        version
    )

def test_taxonomy_resolver_finds_gcd_entry_point(
    tmp_path: Path,
) -> None:
    """Der Resolver findet den GCD-Entry-Point einer Taxonomieversion."""

    entry_point = (
        tmp_path
        / "6.8"
        / "de-gcd-2024-04-01"
        / "de-gcd-2024-04-01-shell.xsd"
    )

    entry_point.parent.mkdir(
        parents=True
    )

    entry_point.touch()

    resolver = TaxonomyResolver(
        root=tmp_path
    )

    result = resolver.gcd_entry_point(
        TaxonomyVersion.V6_8
    )

    assert result == entry_point
    

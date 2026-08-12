"""Tests für die Auflösung lokal installierter Taxonomien."""

from datetime import date
from pathlib import Path

import pytest

from openbilanz.domain.fiscal_year import FiscalYear
from openbilanz.taxonomy.resolver import TaxonomyResolver
from openbilanz.taxonomy.taxonomy import TaxonomyVersion

TAXONOMY_ROOT = Path(
    "/tmp/openbilanz-taxonomy"
)


def test_resolver_finds_gaap_ci_fiscal_entry_point() -> None:
    """Der GAAP-CI-Fiscal-Entry-Point wird gefunden."""

    version_root = TAXONOMY_ROOT / "6.9"

    if not version_root.is_dir():
        pytest.skip(
            "Taxonomy 6.9 is not installed locally"
        )

    resolver = TaxonomyResolver(
        root=TAXONOMY_ROOT
    )

    entry_point = resolver.gaap_ci_fiscal_entry_point(
        TaxonomyVersion.V6_9
    )

    assert entry_point == Path(
        "/tmp/openbilanz-taxonomy/6.9/"
        "de-gaap-ci-2025-04-01/"
        "de-gaap-ci-2025-04-01-shell-fiscal.xsd"
    )


def test_resolver_finds_gaap_ci_fiscal_entry_point_for_6_8() -> None:
    """Der Resolver findet auch die tiefer verschachtelte Taxonomie 6.8."""

    version_root = TAXONOMY_ROOT / "6.8"

    if not version_root.is_dir():
        pytest.skip(
            "Taxonomy 6.8 is not installed locally"
        )

    resolver = TaxonomyResolver(
        root=TAXONOMY_ROOT
    )

    entry_point = resolver.gaap_ci_fiscal_entry_point(
        TaxonomyVersion.V6_8
    )

    assert entry_point == Path(
        "/tmp/openbilanz-taxonomy/6.8/"
        "german-gaap-taxonomy-v6.8-2024-04-01/"
        "xbrl/"
        "de-gaap-ci-2024-04-01/"
        "de-gaap-ci-2024-04-01-shell-fiscal.xsd"
    )


def test_resolver_finds_gaap_ci_fiscal_entry_point_for_6_10() -> None:
    """Der Resolver findet die Taxonomie 6.10."""

    version_root = TAXONOMY_ROOT / "6.10"

    if not version_root.is_dir():
        pytest.skip(
            "Taxonomy 6.10 is not installed locally"
        )

    resolver = TaxonomyResolver(
        root=TAXONOMY_ROOT
    )

    entry_point = resolver.gaap_ci_fiscal_entry_point(
        TaxonomyVersion.V6_10
    )

    assert entry_point == Path(
        "/tmp/openbilanz-taxonomy/6.10/"
        "de-gaap-ci-2026-04-01/"
        "de-gaap-ci-2026-04-01-shell-fiscal.xsd"
    )

def test_resolver_finds_entry_point_for_fiscal_year() -> None:
    """Ein Geschäftsjahr wird auf den passenden Entry-Point aufgelöst."""

    version_root = TAXONOMY_ROOT / "6.9"

    if not version_root.is_dir():
        pytest.skip(
            "Taxonomy 6.9 is not installed locally"
        )

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

    assert entry_point == Path(
        "/tmp/openbilanz-taxonomy/6.9/"
        "de-gaap-ci-2025-04-01/"
        "de-gaap-ci-2025-04-01-shell-fiscal.xsd"
    )
    
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

    version_root = TAXONOMY_ROOT / version.value

    if not version_root.is_dir():
        pytest.skip(
            f"Taxonomy {version.value} is not installed locally"
        )

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
    

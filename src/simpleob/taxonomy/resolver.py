"""Auflösung lokal installierter Taxonomie-Entry-Points."""

from pathlib import Path

from simpleob.domain.fiscal_year import FiscalYear
from simpleob.taxonomy.taxonomy import (
    TaxonomyVersion,
    taxonomy_version_for,
)


class TaxonomyResolver:
    """Findet lokale Entry-Points unterstützter Taxonomieversionen."""

    def __init__(
        self,
        root: Path,
    ) -> None:
        if not isinstance(
            root,
            Path,
        ):
            raise TypeError(
                "root must be a Path"
            )

        self._root = root

    def gaap_ci_fiscal_entry_point(
        self,
        version: TaxonomyVersion,
    ) -> Path:
        """Findet den GAAP-CI-Fiscal-Entry-Point einer Version."""

        if not isinstance(
            version,
            TaxonomyVersion,
        ):
            raise TypeError(
                "version must be a TaxonomyVersion"
            )

        version_root = (
            self._root
            / version.value
        )

        matches = tuple(
            sorted(
                version_root.rglob(
                    "de-gaap-ci-*-shell-fiscal.xsd"
                )
            )
        )

        if not matches:
            raise FileNotFoundError(
                "GAAP-CI fiscal entry point not found "
                f"for taxonomy {version.value}"
            )

        if len(matches) > 1:
            raise ValueError(
                "multiple GAAP-CI fiscal entry points found "
                f"for taxonomy {version.value}"
            )

        return matches[0]
    
    def gcd_entry_point(
        self,
        version: TaxonomyVersion,
    ) -> Path:
        """Findet den GCD-Entry-Point einer Version."""

        if not isinstance(
            version,
            TaxonomyVersion,
        ):
            raise TypeError(
                "version must be a TaxonomyVersion"
            )

        version_root = (
            self._root
            / version.value
        )

        matches = tuple(
            sorted(
                version_root.rglob(
                    "de-gcd-*-shell.xsd"
                )
            )
        )

        if not matches:
            raise FileNotFoundError(
                "GCD entry point not found "
                f"for taxonomy {version.value}"
            )

        if len(matches) > 1:
            raise ValueError(
                "multiple GCD entry points found "
                f"for taxonomy {version.value}"
            )

        return matches[0]
    
    def for_fiscal_year(
        self,
        fiscal_year: FiscalYear,
    ) -> Path:
        """Findet den passenden GAAP-CI-Fiscal-Entry-Point eines Geschäftsjahres."""

        if not isinstance(
            fiscal_year,
            FiscalYear,
        ):
            raise TypeError(
                "fiscal_year must be a FiscalYear"
            )

        version = taxonomy_version_for(
            fiscal_year
        )

        return self.gaap_ci_fiscal_entry_point(
            version
        )
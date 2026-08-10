"""Pakete von XBRL-Taxonomien."""

from dataclasses import dataclass
from pathlib import Path

from openbilanz.taxonomy.entry_point import (
    TaxonomyEntryPoint,
    TaxonomyEntryPointVariant,
    TaxonomyFamily,
)
from openbilanz.taxonomy.taxonomy import TaxonomyVersion


@dataclass(frozen=True, slots=True)
class TaxonomyPackage:
    """Beschreibt ein importiertes XBRL-Taxonomiepaket."""

    name: str
    version: TaxonomyVersion
    entry_points: tuple[TaxonomyEntryPoint, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.name, str):
            raise TypeError(
                "name must be a string"
            )

        if not self.name.strip():
            raise ValueError(
                "name must not be blank"
            )

        if self.name != self.name.strip():
            raise ValueError(
                "name must not contain surrounding whitespace"
            )

        if not isinstance(
            self.version,
            TaxonomyVersion,
        ):
            raise TypeError(
                "version must be a TaxonomyVersion"
            )

        if not isinstance(
            self.entry_points,
            tuple,
        ):
            raise TypeError(
                "entry_points must be a tuple"
            )

        if not all(
            isinstance(
                entry_point,
                TaxonomyEntryPoint,
            )
            for entry_point in self.entry_points
        ):
            raise TypeError(
                "entry_points must contain only "
                "TaxonomyEntryPoint objects"
            )


    @classmethod
    def from_directory(
        cls,
        *,
        root: Path,
        name: str,
        version: TaxonomyVersion,
    ) -> "TaxonomyPackage":
        """Lädt Taxonomie-Entry-Points aus einem Verzeichnis."""

        if not isinstance(root, Path):
            raise TypeError(
                "root muss eine Path-Instanz sein."
            )

        entry_point_paths = tuple(
            sorted(
                root.rglob("*-shell*.xsd")
            )
        )

        entry_points = tuple(
            TaxonomyEntryPoint.from_file(path)
            for path in entry_point_paths
        )

        return cls(
            name=name,
            version=version,
            entry_points=entry_points,
        )

    def entry_points_for(
        self,
        *,
        family: TaxonomyFamily | None = None,
        variant: TaxonomyEntryPointVariant | None = None,
    ) -> tuple[TaxonomyEntryPoint, ...]:
        """Filtert Entry Points nach Familie und Variante."""

        return tuple(
            entry_point
            for entry_point in self.entry_points
            if (
                family is None
                or entry_point.family is family
            )
            and (
                variant is None
                or entry_point.variant is variant
            )
        )

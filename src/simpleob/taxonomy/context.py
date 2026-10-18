"""XBRL-Kontext einer Taxonomie."""

from dataclasses import dataclass
from datetime import date

from simpleob.taxonomy.concept import TaxonomyPeriodType


@dataclass(frozen=True, slots=True)
class TaxonomyDimension:
    """Beschreibt eine explizite XBRL-Dimension und ihr Mitglied."""

    dimension_name: str
    member_name: str

    def __post_init__(self) -> None:
        if not self.dimension_name.strip():
            raise ValueError(
                "dimension_name must not be blank"
            )

        if not self.member_name.strip():
            raise ValueError(
                "member_name must not be blank"
            )


@dataclass(frozen=True, slots=True)
class TaxonomyContext:
    """Beschreibt Entität und Berichtsperiode eines XBRL-Facts."""

    entity_identifier: str
    entity_scheme: str
    period_type: TaxonomyPeriodType
    start_date: date | None
    end_date: date
    dimensions: tuple[TaxonomyDimension, ...] = ()

    def __post_init__(self) -> None:
        if not self.entity_identifier.strip():
            raise ValueError(
                "entity_identifier must not be blank"
            )

        if not self.entity_scheme.strip():
            raise ValueError(
                "entity_scheme must not be blank"
            )

        if (
            self.period_type is TaxonomyPeriodType.DURATION
            and self.start_date is None
        ):
            raise ValueError(
                "duration context requires start_date"
            )

        if (
            self.period_type is TaxonomyPeriodType.INSTANT
            and self.start_date is not None
        ):
            raise ValueError(
                "instant context must not have start_date"
            )

        if (
            self.period_type is TaxonomyPeriodType.DURATION
            and self.start_date is not None
            and self.start_date > self.end_date
        ):
            raise ValueError(
                "start_date must not be after end_date"
            )

        if not isinstance(self.dimensions, tuple):
            raise TypeError(
                "dimensions must be a tuple"
            )

        if not all(
            isinstance(dimension, TaxonomyDimension)
            for dimension in self.dimensions
        ):
            raise TypeError(
                "dimensions must contain only TaxonomyDimension"
            )

        dimension_names = tuple(
            dimension.dimension_name
            for dimension in self.dimensions
        )

        if len(dimension_names) != len(set(dimension_names)):
            raise ValueError(
                "dimension names must be unique"
            )

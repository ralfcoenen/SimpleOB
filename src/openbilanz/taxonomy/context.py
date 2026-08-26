"""XBRL-Kontext einer Taxonomie."""

from dataclasses import dataclass
from datetime import date

from openbilanz.taxonomy.concept import TaxonomyPeriodType
from openbilanz.taxonomy.context_dimension import (
    TaxonomyContextDimension,
)


@dataclass(frozen=True, slots=True)
class TaxonomyContext:
    """Beschreibt Entität und Berichtsperiode eines XBRL-Facts."""

    entity_identifier: str
    entity_scheme: str
    period_type: TaxonomyPeriodType
    start_date: date | None
    end_date: date
    dimensions: tuple[TaxonomyContextDimension, ...] = ()

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

        for dimension in self.dimensions:
            if not isinstance(
                dimension,
                TaxonomyContextDimension,
            ):
                raise TypeError(
                    "dimensions must contain "
                    "TaxonomyContextDimension objects"
                )

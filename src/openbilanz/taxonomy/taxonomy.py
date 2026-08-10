"""E-Bilanz-Taxonomien."""

from dataclasses import dataclass, field
from datetime import date
from enum import Enum

from openbilanz.domain.fiscal_year import FiscalYear


class TaxonomyVersion(Enum):
    """Unterstützte E-Bilanz-Taxonomieversionen."""

    V6_8 = "6.8"
    V6_9 = "6.9"
    V6_10 = "6.10"
    

def taxonomy_version_for(
    fiscal_year: FiscalYear,
) -> TaxonomyVersion:
    """Ermittelt die anzuwendende Taxonomie für ein Geschäftsjahr."""

    if not isinstance(
        fiscal_year,
        FiscalYear,
    ):
        raise TypeError(
            "fiscal_year muss ein FiscalYear sein."
        )

    if fiscal_year.start_date >= date(
        2027,
        1,
        1,
    ):
        return TaxonomyVersion.V6_10

    if fiscal_year.start_date >= date(
        2026,
        1,
        1,
    ):
        return TaxonomyVersion.V6_9

    if fiscal_year.start_date >= date(
        2025,
        1,
        1,
    ):
        return TaxonomyVersion.V6_8

    raise ValueError(
        "Für dieses Geschäftsjahr ist keine "
        "unterstützte Taxonomie definiert."
    )

@dataclass(frozen=True, slots=True)
class TaxonomyPosition:
    """Repräsentiert eine Position der E-Bilanz-Taxonomie."""

    name: str
    label: str
    children: tuple["TaxonomyPosition", ...] = field(
        default_factory=tuple
    )

    def __post_init__(self) -> None:
        if not isinstance(
            self.name,
            str,
        ):
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
            self.label,
            str,
        ):
            raise TypeError(
                "label must be a string"
            )

        if not self.label.strip():
            raise ValueError(
                "label must not be blank"
            )

        if self.label != self.label.strip():
            raise ValueError(
                "label must not contain surrounding whitespace"
            )

        if not isinstance(
            self.children,
            tuple,
        ):
            raise TypeError(
                "children must be a tuple"
            )

        if not all(
            isinstance(
                child,
                TaxonomyPosition,
            )
            for child in self.children
        ):
            raise TypeError(
                "children must contain only TaxonomyPosition objects"
            )


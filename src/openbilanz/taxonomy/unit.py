"""XBRL-Einheit einer Taxonomie."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TaxonomyUnit:
    """Beschreibt die Maßeinheit eines XBRL-Facts."""

    measure: str

    def __post_init__(self) -> None:
        if not self.measure.strip():
            raise ValueError(
                "measure must not be blank"
            )

    @classmethod
    def eur(cls) -> "TaxonomyUnit":
        """Erzeugt die XBRL-Einheit für Euro."""

        return cls(
            measure="iso4217:EUR",
        )
        
    @classmethod
    def pure(cls) -> "TaxonomyUnit":
        """Erzeugt die dimensionslose XBRL-Einheit."""

        return cls(
            measure="xbrli:pure",
        )
"""GCD-Klassifikation einer inländischen Zweigniederlassung."""

from dataclasses import dataclass
from enum import Enum

from simpleob.taxonomy.text_fact import TaxonomyTextFact


class GcdDomesticBranchOfForeignCompanyType(Enum):
    """Ausprägung von domesticBranchOfForeignCompany."""

    HGB = "HGB"
    OTHER = "other"


@dataclass(frozen=True, slots=True)
class GcdDomesticBranchOfForeignCompany:
    """Enthält die ausgewählte Ausprägung als GCD-Tuple."""

    fact: TaxonomyTextFact

    def __post_init__(self) -> None:
        if not isinstance(
            self.fact,
            TaxonomyTextFact,
        ):
            raise TypeError(
                "fact must be a TaxonomyTextFact"
            )

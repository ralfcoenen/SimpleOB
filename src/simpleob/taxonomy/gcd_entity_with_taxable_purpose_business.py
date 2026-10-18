"""GCD-Klassifikation des steuerpflichtigen wirtschaftlichen Geschäftsbetriebs."""

from dataclasses import dataclass
from enum import Enum

from simpleob.taxonomy.text_fact import TaxonomyTextFact


class GcdEntityWithTaxablePurposeBusinessType(Enum):
    """Ausprägung von entityWithTaxablePurposeBusiness."""

    NORMAL = "normal"
    PUBLIC_LAW = "publicLaw"
    TAX_PRIVILEGED = "taxPrivileged"
    MERCHANT_VESSELS_IN_INTERNATIONAL_TRAFFIC = (
        "merchantVesselsInInternationalTraffic"
    )


@dataclass(frozen=True, slots=True)
class GcdEntityWithTaxablePurposeBusiness:
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

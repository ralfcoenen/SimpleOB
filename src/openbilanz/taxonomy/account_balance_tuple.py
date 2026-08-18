"""Taxonomie-Tuple für einen E-Bilanz-Kontennachweis."""

from dataclasses import dataclass

from openbilanz.taxonomy.fact import TaxonomyFact
from openbilanz.taxonomy.text_fact import TaxonomyTextFact


@dataclass(frozen=True, slots=True)
class TaxonomyAccountBalance:
    """Ein detailedInformation.accountBalances-Tuple."""

    position_name: TaxonomyTextFact
    account_number: TaxonomyTextFact
    account_description: TaxonomyTextFact
    amount: TaxonomyFact
    not_possible: TaxonomyTextFact | None = None

    def __post_init__(self) -> None:
        if not isinstance(
            self.position_name,
            TaxonomyTextFact,
        ):
            raise TypeError(
                "position_name must be a TaxonomyTextFact"
            )

        if not isinstance(
            self.account_number,
            TaxonomyTextFact,
        ):
            raise TypeError(
                "account_number must be a TaxonomyTextFact"
            )

        if not isinstance(
            self.account_description,
            TaxonomyTextFact,
        ):
            raise TypeError(
                "account_description must be a TaxonomyTextFact"
            )

        if not isinstance(
            self.amount,
            TaxonomyFact,
        ):
            raise TypeError(
                "amount must be a TaxonomyFact"
            )

        if (
            self.not_possible is not None
            and not isinstance(
                self.not_possible,
                TaxonomyTextFact,
            )
        ):
            raise TypeError(
                "not_possible must be a TaxonomyTextFact or None"
            )

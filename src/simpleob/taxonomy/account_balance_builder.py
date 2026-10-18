"""Erzeugung von GAAP-CI-Kontennachweis-Tuples."""

from simpleob.domain.e_bilanz_account_detail import (
    EBilanzAccountDetail,
)
from simpleob.taxonomy.account_balance_tuple import (
    TaxonomyAccountBalance,
)
from simpleob.taxonomy.context import TaxonomyContext
from simpleob.taxonomy.fact import TaxonomyFact
from simpleob.taxonomy.mapper import TaxonomyMapper
from simpleob.taxonomy.model import TaxonomyModel
from simpleob.taxonomy.text_fact import TaxonomyTextFact
from simpleob.taxonomy.unit import TaxonomyUnit


class AccountBalanceBuilder:
    """Überführt Kontennachweise in GAAP-CI-Tuples."""

    _POSITION_NAME = (
        "detailedInformation.accountbalances.positionName"
    )
    _ACCOUNT_NUMBER = (
        "detailedInformation.accountbalances.accountNumber"
    )
    _ACCOUNT_DESCRIPTION = (
        "detailedInformation.accountbalances.accountDescription"
    )
    _AMOUNT = (
        "detailedInformation.accountbalances.amount"
    )
    _NOT_POSSIBLE = (
        "detailedInformation.accountbalances.notPossible"
    )

    def __init__(
        self,
        *,
        taxonomy_model: TaxonomyModel,
        taxonomy_mapper: TaxonomyMapper,
    ) -> None:
        self._taxonomy_model = taxonomy_model
        self._taxonomy_mapper = taxonomy_mapper

    def build(
        self,
        *,
        detail: EBilanzAccountDetail,
        context: TaxonomyContext,
    ) -> TaxonomyAccountBalance:
        """Erzeugt ein Kontennachweis-Tuple."""

        concepts = {
            concept.name: concept
            for concept
            in self._taxonomy_model.concepts.concepts
        }

        required_names = (
            self._POSITION_NAME,
            self._ACCOUNT_NUMBER,
            self._ACCOUNT_DESCRIPTION,
            self._AMOUNT,
        )

        for name in required_names:
            if name not in concepts:
                raise ValueError(
                    "GAAP-CI taxonomy concept not found: "
                    f"{name}"
                )

        target_concept = (
            self._taxonomy_mapper.concept_for(
                detail.position
            )
        )

        return TaxonomyAccountBalance(
            position_name=TaxonomyTextFact(
                concept=concepts[self._POSITION_NAME],
                value=(
                    "de-gaap-ci:"
                    f"{target_concept.name}"
                ),
                context=context,
            ),
            account_number=TaxonomyTextFact(
                concept=concepts[self._ACCOUNT_NUMBER],
                value=detail.account_number,
                context=context,
            ),
            account_description=TaxonomyTextFact(
                concept=concepts[
                    self._ACCOUNT_DESCRIPTION
                ],
                value=detail.account_description,
                context=context,
            ),
            amount=TaxonomyFact(
                concept=concepts[self._AMOUNT],
                amount=detail.balance,
                context=context,
                unit=TaxonomyUnit.eur(),
            ),
            not_possible=(
                TaxonomyTextFact(
                    concept=concepts[self._NOT_POSSIBLE],
                    value="false",
                    context=context,
                )
                if self._NOT_POSSIBLE in concepts
                else None
            ),
        )

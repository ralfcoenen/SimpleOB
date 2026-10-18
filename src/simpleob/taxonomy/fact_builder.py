"""Aufbau taxonomischer Facts aus Abschlussbeträgen."""

from collections.abc import Mapping
from decimal import Decimal

from simpleob.accounting.financial_statement_position import (
    FinancialStatementPosition,
)
from simpleob.taxonomy.context import TaxonomyContext
from simpleob.taxonomy.fact import TaxonomyFact
from simpleob.taxonomy.mapper import TaxonomyMapper
from simpleob.taxonomy.unit import TaxonomyUnit


class TaxonomyFactBuilder:
    """Erzeugt taxonomische Facts aus internen Abschlusspositionen."""

    def __init__(
        self,
        mapper: TaxonomyMapper,
    ) -> None:
        if not isinstance(
            mapper,
            TaxonomyMapper,
        ):
            raise TypeError(
                "mapper must be a TaxonomyMapper"
            )

        self._mapper = mapper

    def build(
        self,
        amounts: Mapping[
            FinancialStatementPosition,
            Decimal,
        ],
        context: TaxonomyContext,
        unit: TaxonomyUnit,
    ) -> tuple[TaxonomyFact, ...]:
        """Erzeugt aggregierte Facts für die Abschlussbeträge."""

        aggregated: dict[str, TaxonomyFact] = {}

        for position, amount in amounts.items():
            if amount == Decimal("0"):
                continue

            concept = self._mapper.concept_for(
                position
            )

            existing = aggregated.get(
                concept.concept_id
            )

            if existing is None:
                aggregated[concept.concept_id] = TaxonomyFact(
                    concept=concept,
                    amount=amount,
                    context=context,
                    unit=unit,
                )
                continue

            aggregated[concept.concept_id] = TaxonomyFact(
                concept=existing.concept,
                amount=existing.amount + amount,
                context=context,
                unit=unit,
            )

        return tuple(
            fact
            for fact in aggregated.values()
            if fact.amount != Decimal("0")
        )
